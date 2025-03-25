import sys
import dash
from dash.dependencies import Input, Output, State
from dash import dcc, html
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import io
from dateutil import parser

FILE_PATH = 'match_history.csv'


def load_csv_data(file_path):
    """
    Loads CSV data by separating metadata (lines starting with '#')
    from the actual CSV content, and returns (metadata_dict, DataFrame).
    Uses 'utf-8-sig' to automatically strip the BOM.
    """
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        raise

    # Remove empty lines and separate metadata from CSV lines.
    meta_lines = [line.strip() for line in lines if line.strip().startswith('#')]
    csv_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]

    # Extract metadata into a dictionary.
    meta = {}
    for line in meta_lines:
        if ':' in line:
            key, value = line[2:].split(':', 1)  # Remove '# ' prefix.
            meta[key.strip()] = value.strip()

    # Join CSV lines and load into DataFrame.
    try:
        csv_content = ''.join(csv_lines)
        df = pd.read_csv(io.StringIO(csv_content), skip_blank_lines=True)
    except Exception as e:
        print(f"Error parsing CSV data: {e}")
        raise

    # Strip any extra whitespace from column names.
    df.columns = df.columns.str.strip()
    return meta, df


def preprocess_data(df):
    """
    Preprocess the DataFrame:
      - Ensure the expected columns are present.
      - Flag bye matches (rows where Opponent indicates a bye).
      - Parse event dates using an explicit format if possible.
      - Extract opponent ID and name.
      - Compute a win flag based on the "Result" column.
    """
    # Check for the expected column 'Opponent'
    if 'Opponent' not in df.columns:
        print("Columns found in CSV:", df.columns.tolist())
        raise KeyError("Expected column 'Opponent' not found in CSV data.")

    # Mark bye matches.
    df['Is_Bye'] = df['Opponent'].str.contains('Bye', case=False, na=False)
    # Filter out bye matches (if you prefer to exclude them from stats).
    df = df[~df['Is_Bye']].copy()

    # Parse dates using the format '%b. %d, %Y' (e.g., "Mar. 10, 2025")
    try:
        df['Event_Date'] = pd.to_datetime(df['Event Date'], format='%b. %d, %Y')
    except Exception as e:
        print("pd.to_datetime parsing failed, falling back to dateutil.parser:", e)
        df['Event_Date'] = df['Event Date'].apply(lambda d: parser.parse(d.replace('noon', '12:00 PM')))

    # Helper functions to extract opponent details.
    def extract_opponent_id(player_str):
        if pd.isna(player_str) or '(' not in player_str or ')' not in player_str:
            return None
        return player_str.split('(')[-1].split(')')[0]

    def extract_opponent_name(player_str):
        if pd.isna(player_str) or '(' not in player_str:
            return player_str
        return player_str.split(' (')[0]

    df['Opponent_ID'] = df['Opponent'].apply(extract_opponent_id)
    df['Opponent_Name'] = df['Opponent'].apply(extract_opponent_name)
    df['User_Win'] = df['Result'].str.strip().str.lower() == 'win'
    return df


# Load and preprocess the CSV data.
meta, data = load_csv_data(FILE_PATH)
data = preprocess_data(data)

# Retrieve metadata values for display.
player_name = meta.get('Player Name', 'Unknown')
player_id = meta.get('GEM ID', 'Unknown')

rated_data = data[data['Rated'] == 'Yes'].copy()
rated_data['Rating_Change'] = pd.to_numeric(rated_data['Rating Change'], errors='coerce').fillna(0)

# Sort chronologically and compute a running total (starting at 1500).
rated_data = rated_data.sort_values('Event_Date')
rated_data['Cumulative_Rating'] = 1500 + rated_data['Rating_Change'].cumsum()

rated_data['Date'] = rated_data['Event_Date'].dt.date
daily_data = rated_data.groupby('Date', as_index=False).last()  # pick the last row in each day

y_min = daily_data['Cumulative_Rating'].min()
y_max = daily_data['Cumulative_Rating'].max()

daily_elo_fig = px.area(
    daily_data,
    x='Date',
    y='Cumulative_Rating',
    title='Elo Rating Over Time'
)
daily_elo_fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Elo Rating",
    yaxis=dict(range=[y_min - 10, y_max + 10])
)

# Elo Change over time
elo_by_opponent = rated_data.groupby("Opponent_ID")["Rating_Change"].sum().reset_index()

id_to_name_map = data[['Opponent_ID', 'Opponent_Name']].drop_duplicates() \
    .set_index('Opponent_ID')['Opponent_Name'].to_dict()
elo_by_opponent["Opponent_Name"] = elo_by_opponent["Opponent_ID"].map(id_to_name_map)

# Top 5 where you lost the most Elo
top_negative = elo_by_opponent.nsmallest(5, "Rating_Change")
top_negative_fig = px.bar(
    top_negative,
    x="Opponent_Name",
    y="Rating_Change",
    title="Top 5 Opponents you donated Elo to",
    labels={"Opponent_Name": "Opponent", "Rating_Change": "Elo Change"},
    color_discrete_sequence=['#FF7F24']
)
top_negative_fig.update_layout(
    xaxis_title="Opponent",
    yaxis_title="Total Elo Change"
)

# Top 5 where you gained the most Elo
top_positive = elo_by_opponent.nlargest(5, "Rating_Change")
top_positive_fig = px.bar(
    top_positive,
    x="Opponent_Name",
    y="Rating_Change",
    title="Top 5 Opponents donating Elo to you",
    labels={"Opponent_Name": "Opponent", "Rating_Change": "Elo Change"},
    color_discrete_sequence=['#006994']
)
top_positive_fig.update_layout(
    xaxis_title="Opponent",
    yaxis_title="Total Elo Change"
)

# Opponent statistics (wins, losses, win rate)
opponent_stats = data.groupby('Opponent_ID').agg(
    Match_Count=('Opponent_ID', 'size'),
    Win_Count=('User_Win', 'sum'),
    Loss_Count=('User_Win', lambda x: (~x).sum()),
    Win_Rate=('User_Win', 'mean')
).reset_index()
opponent_stats['Opponent_Name'] = opponent_stats['Opponent_ID'].map(id_to_name_map)

# Visualization: Top 5 opponents by match count (stacked wins and losses).
top_5_opponents = opponent_stats.nlargest(5, 'Match_Count')
top_opponents_fig = go.Figure()
top_opponents_fig.add_trace(go.Bar(
    x=top_5_opponents['Opponent_Name'],
    y=top_5_opponents['Loss_Count'],
    name='Losses',
    marker={'color': '#FF7F24'}
))
top_opponents_fig.add_trace(go.Bar(
    x=top_5_opponents['Opponent_Name'],
    y=top_5_opponents['Win_Count'],
    name='Wins',
    marker={'color': '#006994'}
))
top_opponents_fig.update_layout(
    barmode='stack',
    title='Top 5 Opponents by Match Count',
    xaxis_title='Opponent',
    yaxis_title='Count'
)


# Visualization: Win rate per round.
# Create a custom sorting function for rounds
def round_sorter(df):
    # Create a copy of the dataframe to avoid modifying the original
    df_sorted = df.copy()

    # Create a new column for sorting
    df_sorted['Round_Sort'] = df_sorted['Round'].apply(
        lambda x: int(x) if x.isdigit() else float('inf') if x.startswith('P') else float('inf')
    )

    # Create a second level sort key for playoff rounds
    df_sorted['Playoff_Sort'] = df_sorted['Round'].apply(
        lambda x: int(x[1:]) if x.startswith('P') and x[1:].isdigit() else float('inf')
    )

    # Sort by numeric rounds first, then by playoff rounds
    return df_sorted.sort_values(['Round_Sort', 'Playoff_Sort'])


# Group by Round and calculate win rate
round_win_rate = data.groupby('Round')['User_Win'].mean().reset_index()
round_win_rate['Win Rate'] = round_win_rate['User_Win'] * 100

# Apply custom sorting
round_win_rate = round_sorter(round_win_rate)

round_win_rate_fig = px.bar(
    round_win_rate,
    x='Round',
    y='Win Rate',
    title='Win Rate per Round',
    color_discrete_sequence=['#006994']
)
round_win_rate_fig.update_traces(hovertemplate='Round %{x}<br>Win Rate=%{y:.2f}%')
round_win_rate_fig.update_layout(yaxis_title="Win Rate (%)")

# Visualization: Win Rate Against Each Opponent (Static version)
fig_win_rate = px.bar(
    opponent_stats.sort_values('Win_Rate'),
    x='Win_Rate',
    y='Opponent_Name',
    orientation='h',
    title='Win Rate Against Each Opponent',
    color_discrete_sequence=['#006994']
)
fig_win_rate.update_layout(
    height=1000,  # Taller figure
    margin=dict(l=200),  # More space for y-axis labels
    xaxis_title="Win Rate (%)",
    yaxis=dict(
        categoryorder='total ascending',
        tickfont=dict(size=10)  # Smaller text for many opponents
    )
)
fig_win_rate.update_traces(marker=dict(color='#006994'))

# ----------------------
# Dash App Layout
# ----------------------

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1(f'FaB History Analysis for {player_name}'),
    html.Div(f'GEM ID: {player_id}'),

    # Filter Controls (Rating)
    html.Div([
        dcc.RadioItems(
            id='rating_filter',
            options=[
                {'label': 'All', 'value': 'all'},
                {'label': 'Rated', 'value': 'Yes'},
                {'label': 'Unrated', 'value': 'No'}
            ],
            value='all',
            labelStyle={'display': 'inline-block'}
        ),
        html.Div(id='stats_output')
    ], style={'margin': '20px 0'}),

    # Opponent Search
    html.Div([
        dcc.Input(id='opponent_name_input', type='text', placeholder='Enter opponent name'),
        html.Button('Submit', id='opponent_name_submit'),
        html.Div(id='opponent_name_output')
    ], style={'margin': '20px 0'}),

    # Elo Over Time, Top Gains/Losses
    dcc.Graph(id='elo_over_time_graph', figure=daily_elo_fig),
    dcc.Graph(id='top-negative-graph', figure=top_negative_fig),
    dcc.Graph(id='top-positive-graph', figure=top_positive_fig),

    # --------------------------------------
    # Put the checklist & Win Rate graph together
    # --------------------------------------
    html.Div([
        # The new checklist directly above the Win Rate chart
        dcc.Checklist(
            id='extreme_filter',
            options=[{'label': 'Hide 0% / 100% Opponents', 'value': 'exclude'}],
            value=[],  # empty by default
            labelStyle={'display': 'inline-block'}
        ),
        dcc.Graph(id='filtered_graph')  # This is the "Win Rate Against Each Opponent" chart
    ], style={'margin': '20px 0'}),

    # The top-opponents-graph
    dcc.Graph(id='top-opponents-graph', figure=top_opponents_fig),
    dcc.Graph(figure=round_win_rate_fig)
])


@app.callback(
    Output('filtered_graph', 'figure'),
    [
        Input('rating_filter', 'value'),
        Input('extreme_filter', 'value')  # NEW INPUT
    ]
)
def update_filtered_graph(rating_value, extreme_filter):
    """
    Updates the "Win Rate Against Each Opponent" bar chart
    based on the selected rating filter AND whether we exclude
    0% / 100% opponents.
    """
    if rating_value != 'all':
        filtered = data[data['Rated'] == rating_value]
    else:
        filtered = data.copy()

    stats = filtered.groupby('Opponent_ID').agg(
        Match_Count=('Opponent_ID', 'size'),
        Win_Rate=('User_Win', 'mean')
    ).reset_index()
    stats['Opponent_Name'] = stats['Opponent_ID'].map(id_to_name_map)
    # Convert to percentage for final display
    stats['Win_Rate'] *= 100

    # If user wants to exclude extremes, remove those at exactly 0% or 100%
    if 'exclude' in extreme_filter:
        stats = stats[(stats['Win_Rate'] > 0) & (stats['Win_Rate'] < 100)]

    figure = px.bar(
        stats.sort_values('Win_Rate'),
        x='Win_Rate',
        y='Opponent_Name',
        orientation='h',
        title='Win Rate Against Each Opponent',
        color_discrete_sequence=['#006994']
    )
    figure.update_layout(
        yaxis_title="Opponent",
        xaxis_title="Win Rate (%)",
        height=1000,
        margin=dict(l=200),
        yaxis=dict(
            categoryorder='total ascending',
            tickfont=dict(size=10)
        )
    )
    return figure


@app.callback(
    Output('opponent_name_output', 'children'),
    [Input('opponent_name_submit', 'n_clicks')],
    [State('opponent_name_input', 'value')]
)
def update_opponent_output(n_clicks, value):
    """
    Searches for opponents by name and displays match stats.
    """
    if not n_clicks or not value:
        return 'Enter an opponent name and click submit.'

    filtered = data[data['Opponent_Name'].fillna('').str.contains(value, case=False)]
    if filtered.empty:
        return 'No matches found for this opponent.'

    stats = filtered.groupby('Opponent_ID').agg(
        Match_Count=('Opponent_ID', 'size'),
        Win_Rate=('User_Win', 'mean')
    ).reset_index()
    stats['Opponent_Name'] = stats['Opponent_ID'].map(id_to_name_map)

    results = [
        f"{row['Opponent_Name']}: {row['Match_Count']} matches, {row['Win_Rate']:.2%} win rate"
        for _, row in stats.iterrows()
    ]
    return html.Ul([html.Li(result) for result in results])


@app.callback(
    Output('stats_output', 'children'),
    [Input('rating_filter', 'value')]
)
def update_stats_output(rating_filter):
    """
    Updates overall statistics based on the selected rating filter.
    """
    if rating_filter == 'all':
        filtered = data
    else:
        filtered = data[data['Rated'] == rating_filter]

    total_matches = len(filtered)
    overall_winrate = filtered["User_Win"].mean()
    unique_opponents = filtered["Opponent_ID"].nunique()

    return html.Div([
        html.H3(f'Total Matches: {total_matches}'),
        html.H3(f'Total Winrate: {overall_winrate:.2%}'),
        html.H3(f'Number of Different Opponents: {unique_opponents}')
    ])


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        app.run(debug=False, host='0.0.0.0')
    else:
        app.run(debug=True, host='0.0.0.0')

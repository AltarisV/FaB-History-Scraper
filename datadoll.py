import dash
from dash.dependencies import Input, Output, State
from dash import dcc
from dash import html
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from dateutil import parser

# Load your CSV data
file_path = 'match_history.csv'  # Replace with your CSV file path
data = pd.read_csv(file_path)


def parse_date(date_str):
    date_str = date_str.replace('noon', '12:00 PM')
    return parser.parse(date_str)


def extract_player_id(player_str):
    # Extract the player ID from the string
    if pd.isna(player_str) or '(' not in player_str or ')' not in player_str:
        return None
    return player_str.split('(')[-1].split(')')[0]


def extract_player_name(player_str):
    if pd.isna(player_str) or '(' not in player_str:
        return player_str
    # Split the string at the first occurrence of ' ('
    name_part = player_str.split(' (')[0]
    return name_part

def extract_player_info(player_str):
    if pd.isna(player_str) or '(' not in player_str or ')' not in player_str:
        return None, player_str
    player_id = player_str.split('(')[-1].split(')')[0]
    player_name = player_str.split(' (')[0]
    return player_id, player_name

# Apply the custom parse_date function to the 'Event Date' column
data['Event_Date'] = data['Event Date'].apply(parse_date)

#parse data from the opponent column
data['Opponent_Info'] = data['Opponent'].apply(extract_player_info)

# Check Opponent ID columns to find the most frequent player ID
user_id = data['Opponent'].value_counts().idxmax()  # Most frequent ID in all matches

# Extract player_id and player_name from the temporary column
data['Opponent_ID'] = data['Opponent_Info'].apply(lambda x: x[0])
data['Opponent_Name'] = data['Opponent_Info'].apply(lambda x: x[1])

data.drop(columns=['Opponent_Info'], inplace=True)

# Total winrate
total_winrate = int((data['Result'].value_counts().get('Win', 0) / len(data)) * 100)

# Group data by opponent ID and calculate win rate
opponent_win_rate = data.groupby('Opponent_ID')['Result'].agg(
    win_rate=lambda x: (x == 'Win').mean() * 100
).reset_index()
opponent_win_rate.rename(columns={'win_rate': 'Win Rate'}, inplace=True)

# Calculate match count, win count, and loss count against each opponent
opponent_stats = data.groupby('Opponent_ID').agg(
    Match_Count=('Opponent_ID', 'size'),
    Win_Count=('Result', lambda x: (x == 'Win').sum()),  # Count the wins
    Loss_Count=('Result', lambda x: (x == 'Loss').sum())  # Count the losses
).reset_index()

# Calculate win rate for later use
opponent_stats['Win_Rate'] = opponent_stats['Win_Count'] / opponent_stats['Match_Count']

# Create a mapping of opponent ID to opponent name
id_to_name_map = data[['Opponent_ID', 'Opponent_Name']].drop_duplicates().set_index('Opponent_ID')[
    'Opponent_Name'].to_dict()

# Apply mapping to opponent stats
opponent_stats['Opponent_Name'] = opponent_stats['Opponent_ID'].map(id_to_name_map)

# Sort opponents by win rate
opponent_win_rate_sorted = opponent_win_rate.sort_values('Win Rate', ascending=True)
opponent_win_rate_sorted['Opponent_Name'] = opponent_win_rate_sorted['Opponent_ID'].map(id_to_name_map)

top_5_opponents = opponent_stats.nlargest(5, 'Match_Count')
number_opponents = len(opponent_stats)

# Group data by round and calculate win rate
round_win_rate = data.groupby('Round')['Result'].agg(
    win_rate=lambda x: (x == 'Win').mean() * 100
).reset_index()
round_win_rate.rename(columns={'win_rate': 'Win Rate'}, inplace=True)

round_win_rate['Win Rate'] = round_win_rate['Win Rate']

print(data)

# Create the figure
round_win_rate_figure = px.bar(round_win_rate, x='Round', y='Win Rate', title='Win Rate per Round')

# Update hover template to show percentage
round_win_rate_figure.update_traces(hovertemplate='Round %{x}<br>Win Rate=%{y:.2f}%')
round_win_rate_figure.update_layout(yaxis_title="Win Rate (%)")

# Assuming top_5_opponents is already sorted by 'Match_Count' descending
fig = go.Figure()
fig.add_trace(go.Bar(
    x=top_5_opponents['Opponent_Name'],
    y=top_5_opponents['Win_Count'],
    name='Wins',
    marker={'color': '#6495ED'}
))
fig.add_trace(go.Bar(
    x=top_5_opponents['Opponent_Name'],
    y=top_5_opponents['Loss_Count'],
    name='Losses',
    marker={'color': '#FF7F24'}
))

# Modify the layout to stack the bars
fig.update_layout(
    barmode='stack',
    title='Top 5 Opponents by Match Count',
    xaxis_title='Opponent',
    yaxis_title='Count'
)

fig_win_rate = px.bar(
    opponent_win_rate_sorted,
    x='Win Rate',
    y='Opponent_Name',
    orientation='h',
    title='Win Rate Against Each Opponent'
)
fig_win_rate.update_layout(yaxis={'categoryorder': 'total ascending'}, xaxis_title="Win Rate (%)")
fig_win_rate.update_traces(marker_color='cyan')

# Additional Data processing here

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of the app
app.layout = html.Div([
    html.H1('FaB History Analysis'),
    html.Div('Interactive visualization of matchup history.'),

    html.Div([
        dcc.RadioItems(
            id='rating_filter',
            options=[
                {'label': 'All', 'value': 'all'},
                {'label': 'Rated', 'value': 'yes'},
                {'label': 'Unrated', 'value': 'no'}
            ],
            value='all',  # Default value
            labelStyle={'display': 'inline-block'}
        ),
        html.Div(id='stats_output')  # Div to display updated stats
    ]),

    html.Div([
        dcc.Input(id='opponent_name_input', type='text', placeholder='Enter opponent name'),
        html.Button('Submit', id='opponent_name_submit'),
        html.Div(id='opponent_name_output')
    ]),

    dcc.Dropdown(
        id='sort_by_dropdown',
        options=[
            {'label': 'Name - Ascending', 'value': 'Name_asc'},
            {'label': 'Name - Descending', 'value': 'Name_desc'},
            {'label': 'Win Rate - Ascending', 'value': 'Win Rate_asc'},
            {'label': 'Win Rate - Descending', 'value': 'Win Rate_desc'}
        ],
        value='Name_asc'
    ),
    html.Div([
        dcc.RadioItems(
            id='rated_filter',
            options=[
                {'label': 'All', 'value': 'all'},
                {'label': 'Rated', 'value': 'yes'},
                {'label': 'Unrated', 'value': 'no'}
            ],
            value='all',  # Default value
            labelStyle={'display': 'inline-block'}
        ),
    ]),
    dcc.Graph(id='filtered_graph', figure=fig_win_rate),

    dcc.Graph(id='top-opponents-graph', figure=fig),

    dcc.Graph(figure=round_win_rate_figure)

])


@app.callback(
    Output('filtered_graph', 'figure'),
    [Input('sort_by_dropdown', 'value'), Input('rated_filter', 'value')]
)
def update_graph(sort_by_value, rated_value):
    # Filter by rated status if not 'all'
    if rated_value != 'all':
        filtered_data = data[data['Rated'] == rated_value]
    else:
        filtered_data = data.copy()

    # Group by opponent ID and calculate win rate and match count
    opponent_stats_filtered = filtered_data.groupby('Opponent_ID').agg(
        Match_Count=('Opponent_ID', 'size'),
        Win_Rate=('Result', lambda x: (x == 'Win').mean())
    ).reset_index()

    # Apply mapping to opponent stats for display
    opponent_stats_filtered['Opponent_Name'] = opponent_stats_filtered['Opponent_ID'].map(id_to_name_map)

    # Convert 'Win_Rate' to percentage
    opponent_stats_filtered['Win_Rate'] *= 100

    # Determine sorting
    sort_by, order = sort_by_value.split('_')
    ascending = order == 'asc'

    if sort_by == 'Name':
        opponent_stats_filtered.sort_values(by='Opponent_Name', ascending=ascending, inplace=True)
    elif sort_by == 'Win Rate':
        opponent_stats_filtered.sort_values(by='Win_Rate', ascending=ascending, inplace=True)

    # Create the figure
    figure = px.bar(
        opponent_stats_filtered,
        x='Opponent_Name',
        y='Win_Rate',
        title='Win Rate Against Each Opponent'
    )

    # Update hover template to show percentage and match count
    figure.update_traces(
        hovertemplate='Opponent: %{x}<br>Win Rate: %{y:.2f}%<br>Match Count: %{customdata}'
    )
    figure.update_layout(yaxis_title="Win Rate (%)")

    # Add customdata for hover info
    figure.update_traces(customdata=opponent_stats_filtered['Match_Count'])

    return figure


@app.callback(
    Output('opponent_name_output', 'children'),
    [Input('opponent_name_submit', 'n_clicks')],
    [State('opponent_name_input', 'value')]
)
def update_output(n_clicks, value):
    if n_clicks is None or value is None:
        return 'Enter an opponent name and click submit'

    # Replace NaN values in 'Opponent_Name' column and filter data
    filtered_data = data[data['Opponent_Name'].fillna('').str.contains(value, case=False)]

    if filtered_data.empty:
        return 'No matches found for this opponent'

    # Group by 'Opponent_ID' and calculate match count and win rate for each
    opponent_stats = filtered_data.groupby('Opponent_ID').agg(
        Match_Count=('Opponent_ID', 'size'),
        Win_Rate=('Result', lambda x: (x == 'Win').mean() * 100)  # Calculate win rate as a percentage
    ).reset_index()

    # Apply mapping to opponent stats for display
    opponent_stats['Opponent_Name'] = opponent_stats['Opponent_ID'].map(id_to_name_map)

    # Formatting the output
    results = []
    for index, row in opponent_stats.iterrows():
        opponent_name = row['Opponent_Name']
        matches = row['Match_Count']
        win_rate = row['Win_Rate']
        results.append(f"{opponent_name}: {matches} matches, {win_rate }% win rate")

    return html.Ul([html.Li(opponent) for opponent in results])


@app.callback(
    Output('stats_output', 'children'),
    [Input('rating_filter', 'value')]
)
def update_stats(rating_filter):
    if rating_filter == 'all':
        filtered_data = data
    elif rating_filter == 'True':
        filtered_data = data[data['Rated'] == 'yes']
    else:
        filtered_data = data[data['Rated'] == 'no']

    total_matches = len(filtered_data)
    total_winrate = (filtered_data['Result'] == 'Win').mean() * 100
    number_opponents = filtered_data['Opponent_ID'].nunique()

    return html.Div([
        html.H3(f'Total Matches: {total_matches}'),
        html.H3(f'Total Winrate: {total_winrate:.2f}%'),
        html.H3(f'Number of different Opponents: {number_opponents}')
    ])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=8050)
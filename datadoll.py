import dash
from dash.dependencies import Input, Output, State
from dash import dcc
from dash import html
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

# Load your CSV data
file_path = 'match_history.csv'  # Replace with your CSV file path
data = pd.read_csv(file_path)


def extract_player_id(player_str):
    # Extract the player ID from the string
    if pd.isna(player_str) or '(' not in player_str or ')' not in player_str:
        return None
    return player_str.split('(')[-1].split(')')[0]


def extract_player_name(player_str):
    # Extract the player name from the string
    if pd.isna(player_str) or '(' not in player_str:
        return player_str
    return player_str.split(' (')[0]


data['Player1_ID'] = data['Player 1'].apply(extract_player_id)
data['Player2_ID'] = data['Player 2'].apply(extract_player_id)

# Concatenate 'Player1_ID' and 'Player2_ID' columns to find the most frequent player ID
all_player_ids = pd.concat([data['Player1_ID'], data['Player2_ID']])
user_id = all_player_ids.value_counts().idxmax()  # Most frequent ID in all matches

# Find the user's name using the most frequent ID
user_name_row = data[(data['Player1_ID'] == user_id) | (data['Player2_ID'] == user_id)]
user_name = user_name_row['Player 1'].iloc[0] if user_name_row['Player1_ID'].iloc[0] == user_id else \
user_name_row['Player 2'].iloc[0]

# Determine opponent IDs and names, and whether the user won each match
data['Opponent_ID'] = data.apply(lambda row: row['Player2_ID'] if row['Player1_ID'] == user_id else row['Player1_ID'],
                                 axis=1)
data['Opponent_Name'] = data.apply(lambda row: row['Player 2'] if row['Player1_ID'] == user_id else row['Player 1'],
                                   axis=1)
data['User_Win'] = ((data['Player1_ID'] == user_id) & data['Result'].str.contains('Player 1 Win')) | \
                   ((data['Player2_ID'] == user_id) & data['Result'].str.contains('Player 2 Win'))

# Total winrate
total_winrate = data['User_Win'].mean()

# Winrate as Player 1 and Player 2
data['User_Is_Player1'] = data['Player1_ID'] == user_id
data['User_Is_Player2'] = data['Player2_ID'] == user_id
winrate_player1 = data[data['User_Is_Player1']]['User_Win'].mean()
winrate_player2 = data[data['User_Is_Player2']]['User_Win'].mean()

# Group data by opponent ID and calculate win rate
opponent_win_rate = data.groupby('Opponent_ID')['User_Win'].mean().reset_index()
opponent_win_rate.rename(columns={'User_Win': 'Win Rate'}, inplace=True)

# Calculate match count, win count, and loss count against each opponent
opponent_stats = data.groupby('Opponent_ID').agg(
    Match_Count=('Opponent_ID', 'size'),
    Win_Count=('User_Win', lambda x: x.sum()),  # Count the wins
    Loss_Count=('User_Win', lambda x: (1 - x).sum())  # Count the losses
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
round_win_rate = data.groupby('Round')['User_Win'].mean().reset_index()
round_win_rate.rename(columns={'User_Win': 'Win Rate'}, inplace=True)

round_win_rate['Win Rate'] = round_win_rate['Win Rate'] * 100

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
                {'label': 'Rated', 'value': 'True'},
                {'label': 'Unrated', 'value': 'False'}
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
                {'label': 'Rated', 'value': True},
                {'label': 'Unrated', 'value': False}
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
        Win_Rate=('User_Win', 'mean')
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

    # Group by 'Opponent_ID' and calculate win rate and count for each
    opponent_stats = filtered_data.groupby('Opponent_ID').agg(
        Match_Count=('Opponent_ID', 'size'),
        Win_Rate=('User_Win', 'mean')
    ).reset_index()

    # Apply mapping to opponent stats for display
    opponent_stats['Opponent_Name'] = opponent_stats['Opponent_ID'].map(id_to_name_map)

    # Formatting the output
    results = []
    for index, row in opponent_stats.iterrows():
        opponent_name = row['Opponent_Name']
        matches = row['Match_Count']
        win_rate = row['Win_Rate']
        results.append(f"{opponent_name}: {matches} matches, {win_rate:.2%} win rate")

    return html.Ul([html.Li(opponent) for opponent in results])


@app.callback(
    Output('stats_output', 'children'),
    [Input('rating_filter', 'value')]
)
def update_stats(rating_filter):
    if rating_filter == 'all':
        filtered_data = data
    elif rating_filter == 'True':
        filtered_data = data[data['Rated'] == True]
    else:
        filtered_data = data[data['Rated'] == False]

    total_matches = len(filtered_data)
    total_winrate = filtered_data['User_Win'].mean()
    winrate_player1 = filtered_data[filtered_data['User_Is_Player1']]['User_Win'].mean()
    winrate_player2 = filtered_data[filtered_data['User_Is_Player2']]['User_Win'].mean()
    number_opponents = len(filtered_data.groupby('Opponent_ID'))

    return html.Div([
        html.H3(f'Total Matches: {total_matches}'),
        html.H3(f'Total Winrate: {total_winrate:.2%}'),
        html.H3(f'Winrate as Player 1: {winrate_player1:.2%}'),
        html.H3(f'Winrate as Player 2: {winrate_player2:.2%}'),
        html.H3(f'Number of different Opponents: {number_opponents}')
    ])


# Run the app
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=8050)

import dash
from dash.dependencies import Input, Output, State
from dash import dcc
from dash import html
import pandas as pd
import plotly.express as px

# Load your CSV data
file_path = 'match_history.csv'  # Replace with your CSV file path
data = pd.read_csv(file_path)

# Concatenate 'Player 1' and 'Player 2' columns and find the most frequent player
all_players = pd.concat([data['Player 1'], data['Player 2']])
user_name = all_players.value_counts().idxmax()  # Most frequent name in all matches
total_matches = len(data)

# Determine opponent names and whether the user won each match
data['Opponent'] = data.apply(lambda row: row['Player 2'] if row['Player 1'] == user_name else row['Player 1'], axis=1)
data['User_Win'] = ((data['Player 1'] == user_name) & data['Result'].str.contains('Player 1 Win')) | \
                   ((data['Player 2'] == user_name) & data['Result'].str.contains('Player 2 Win'))

# Total winrate
total_winrate = data['User_Win'].mean()

# Winrate as Player 1 and Player 2
data['User_Is_Player1'] = data['Player 1'] == user_name
data['User_Is_Player2'] = data['Player 2'] == user_name
winrate_player1 = data[data['User_Is_Player1']]['User_Win'].mean()
winrate_player2 = data[data['User_Is_Player2']]['User_Win'].mean()

# Group data by opponent and calculate win rate
opponent_win_rate = data.groupby('Opponent')['User_Win'].mean().reset_index()
opponent_win_rate.rename(columns={'User_Win': 'Win Rate'}, inplace=True)

# Check the entire list of opponents
print(opponent_win_rate)


# Calculate match count and win rate against each opponent
opponent_stats = data.groupby('Opponent').agg(Match_Count=('Opponent', 'size'), Win_Rate=('User_Win', 'mean')).reset_index()
top_5_opponents = opponent_stats.nlargest(5, 'Match_Count')
number_opponents = len(opponent_stats)

# Group data by round and calculate win rate
round_win_rate = data.groupby('Round')['User_Win'].mean().reset_index()
round_win_rate.rename(columns={'User_Win': 'Win Rate'}, inplace=True)


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

    html.Div([
        dcc.Dropdown(
            id='rated_dropdown',
            options=[
                {'label': 'All', 'value': 'all'},
                {'label': 'Rated', 'value': 'True'},
                {'label': 'Unrated', 'value': 'False'}
            ],
            value='all'
        ),
        dcc.Graph(id='rated_filtered_graph')
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

    dcc.Graph(id='filtered_graph'),

    dcc.Graph(
        id='top-opponents-graph',
        figure=px.bar(top_5_opponents, x='Opponent', y='Match_Count', title='Top 5 Opponents by Match Count')
    ),

    dcc.Graph(
        figure=px.bar(round_win_rate, x='Round', y='Win Rate', title='Win Rate per Round')
    )

])

# Callback for updating the graph based on sorting
@app.callback(
    Output('filtered_graph', 'figure'),
    [Input('sort_by_dropdown', 'value')]
)
def update_graph(sort_by_value):
    sort_by, order = sort_by_value.split('_')
    ascending = order == 'asc'

    if sort_by == 'Name':
        sorted_data = opponent_win_rate.sort_values(by='Opponent', ascending=ascending)
    elif sort_by == 'Win Rate':
        sorted_data = opponent_win_rate.sort_values(by='Win Rate', ascending=ascending)

    figure = px.bar(sorted_data, x='Opponent', y='Win Rate', title='Win Rate Against Each Opponent')
    return figure

@app.callback(
    Output('opponent_name_output', 'children'),
    [Input('opponent_name_submit', 'n_clicks')],
    [State('opponent_name_input', 'value')]
)
def update_output(n_clicks, value):
    if n_clicks is None or value is None:
        return 'Enter an opponent name and click submit'

    # Replace NaN values in 'Opponent' column and filter data
    filtered_data = data[data['Opponent'].fillna('').str.contains(value, case=False)]

    if filtered_data.empty:
        return 'No matches found for this opponent'

    # Group by 'Opponent' and calculate win rate and count for each
    opponent_stats = filtered_data.groupby('Opponent').agg(
        Match_Count=('Opponent', 'size'),
        Win_Rate=('User_Win', 'mean')
    ).reset_index()

    # Formatting the output
    results = []
    for index, row in opponent_stats.iterrows():
        results.append(f"{row['Opponent']}: {row['Match_Count']} matches, {row['Win_Rate']:.2f} win rate")

    return html.Ul([html.Li(opponent) for opponent in results])


@app.callback(
    Output('rated_filtered_graph', 'figure'),
    [Input('rated_dropdown', 'value')]
)
def update_rated_graph(value):
    if value == 'all':
        filtered_data = data
    else:
        is_rated = True if value == 'True' else False
        filtered_data = data[data['Rated'] == is_rated]

    # Calculate Win Rate for the filtered data
    win_rate_filtered = filtered_data.groupby('Opponent').agg(Win_Rate=('User_Win', 'mean')).reset_index()

    # Plotting the figure with the newly calculated win rates
    figure = px.bar(win_rate_filtered, x='Opponent', y='Win_Rate', title='Win Rate (Filtered by Rated Status)')
    return figure

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
    number_opponents = len(filtered_data.groupby('Opponent'))

    return html.Div([
        html.H3(f'Total Matches: {total_matches}'),
        html.H3(f'Total Winrate: {total_winrate:.2f}'),
        html.H3(f'Winrate as Player 1: {winrate_player1:.2f}'),
        html.H3(f'Winrate as Player 2: {winrate_player2:.2f}'),
        html.H3(f'Number of different Opponents: {number_opponents}')
    ])


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)

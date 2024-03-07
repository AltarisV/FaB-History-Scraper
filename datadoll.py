import dash
from dash.dependencies import Input, Output
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
    html.H3(f'Total Matches: {total_matches}'),
    html.H3(f'Total Winrate: {total_winrate:.2f}'),
    html.H3(f'Winrate as Player 1: {winrate_player1:.2f}'),
    html.H3(f'Winrate as Player 2: {winrate_player2:.2f}'),
    html.H3(f'Number of different Opponents: {number_opponents:.2f}'),

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


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)

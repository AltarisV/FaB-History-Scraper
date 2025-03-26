import sys
import dash
from dash.dependencies import Input, Output, State
from dash import dcc, html, dash_table
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import io
from dateutil import parser
from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc
import textwrap

FILE_PATH = 'match_history.csv'


def load_csv_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        raise

    meta_lines = [line.strip() for line in lines if line.strip().startswith('#')]
    csv_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]

    meta = {}
    for line in meta_lines:
        if ':' in line:
            key, value = line[2:].split(':', 1)
            meta[key.strip()] = value.strip()

    try:
        csv_content = ''.join(csv_lines)
        df = pd.read_csv(
            io.StringIO(csv_content),
            sep=r',(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)',
            engine='python'
        )
        for col in df.select_dtypes(include='object'):
            df[col] = df[col].str.strip('"')
    except Exception as e:
        print(f"Error parsing CSV data: {e}")
        raise

    df.columns = df.columns.str.strip()
    return meta, df


def preprocess_data(df):
    if 'Opponent' not in df.columns:
        raise KeyError("Expected column 'Opponent' not found in CSV data.")

    df['Is_Bye'] = df['Opponent'].str.contains('Bye', case=False, na=False)
    df = df[~df['Is_Bye']].copy()

    df['Event_Date'] = pd.to_datetime(df['Event Date'], format='%b. %d, %Y', errors='coerce')
    missing = df['Event_Date'].isna()
    if missing.any():
        df.loc[missing, 'Event_Date'] = df.loc[missing, 'Event Date'].apply(
            lambda d: parser.parse(d.replace('noon', '12:00 PM'))
        )

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


def wrap_label(name):
    return "<br>".join(textwrap.wrap(name, width=12, break_long_words=False, break_on_hyphens=False))


# ------------------------------------------------
# Load & preprocess data
# ------------------------------------------------
meta, data = load_csv_data(FILE_PATH)
data = preprocess_data(data)

player_name = meta.get('Player Name', 'Unknown')
player_id = meta.get('GEM ID', 'Unknown')

id_to_name_map = (
    data[['Opponent_ID', 'Opponent_Name']]
        .drop_duplicates()
        .set_index('Opponent_ID')['Opponent_Name']
        .to_dict()
)

# ------------------------------------------------
# Figures
# ------------------------------------------------
rated_data = data[data['Rated'] == 'Yes'].copy()
rated_data['Rating_Change'] = pd.to_numeric(rated_data['Rating Change'], errors='coerce').fillna(0)
rated_data = rated_data.sort_values('Event_Date')
rated_data['Cumulative_Rating'] = 1500 + rated_data['Rating_Change'].cumsum()
rated_data['Date'] = rated_data['Event_Date'].dt.date

daily_data = rated_data.groupby('Date', as_index=False).last()
y_min, y_max = (
    daily_data['Cumulative_Rating'].min(), daily_data['Cumulative_Rating'].max()) if not daily_data.empty else (
    1400, 1600)
daily_elo_fig = px.area(daily_data, x='Date', y='Cumulative_Rating', title='Elo Rating Over Time')
daily_elo_fig.update_layout(xaxis_title="Date", yaxis_title="Elo Rating", yaxis=dict(range=[y_min - 10, y_max + 10]))

elo_by_opponent = rated_data.groupby("Opponent_ID")["Rating_Change"].sum().reset_index()
elo_by_opponent["Opponent_Name"] = elo_by_opponent["Opponent_ID"].map(id_to_name_map)

top_negative = elo_by_opponent.nsmallest(5, "Rating_Change")
top_negative['Opponent_Label'] = top_negative['Opponent_Name'].apply(wrap_label)
top_negative_fig = px.bar(
    top_negative,
    x="Opponent_Label",
    y="Rating_Change",
    title="Top 5 Opponents you donated Elo to",
    labels={"Opponent_Label": "Opponent", "Rating_Change": "Total Elo Change"},
    color_discrete_sequence=['#FF7F24']
)
top_negative_fig.update_layout(xaxis_title="Opponent", yaxis_title="Total Elo Change", xaxis_tickangle=0,
                               xaxis_tickfont=dict(size=10), margin=dict(t=50, b=80))

top_positive = elo_by_opponent.nlargest(5, "Rating_Change")
top_positive['Opponent_Label'] = top_positive['Opponent_Name'].apply(wrap_label)
top_positive_fig = px.bar(
    top_positive,
    x="Opponent_Label",
    y="Rating_Change",
    title="Top 5 Opponents donating Elo to you",
    labels={"Opponent_Label": "Opponent", "Rating_Change": "Total Elo Change"},
    color_discrete_sequence=['#006994'],
    template=top_negative_fig.layout.template
)
top_positive_fig.update_layout(xaxis_title="Opponent", yaxis_title="Total Elo Change", xaxis_tickangle=0,
                               xaxis_tickfont=dict(size=10), margin=dict(t=50, b=80))

opponent_stats = data.groupby('Opponent_ID').agg(
    Match_Count=('Opponent_ID', 'size'),
    Win_Count=('User_Win', 'sum'),
    Loss_Count=('User_Win', lambda x: (~x).sum())
).reset_index()
opponent_stats['Opponent_Name'] = opponent_stats['Opponent_ID'].map(id_to_name_map)

top_5_opponents = opponent_stats.nlargest(5, 'Match_Count')
top_5_opponents['Opponent_Label'] = top_5_opponents['Opponent_Name'].apply(wrap_label)

top_opponents_fig = go.Figure()
top_opponents_fig.add_trace(go.Bar(
    x=top_5_opponents['Opponent_Label'],
    y=top_5_opponents['Loss_Count'],
    name='Losses',
    marker={'color': '#FF7F24'}
))
top_opponents_fig.add_trace(go.Bar(
    x=top_5_opponents['Opponent_Label'],
    y=top_5_opponents['Win_Count'],
    name='Wins',
    marker={'color': '#006994'}
))
top_opponents_fig.update_layout(
    barmode='stack',
    title='Top 5 Opponents by Match Count',
    xaxis_title='Opponent',
    yaxis_title='Count',
    xaxis_tickangle=0,
    xaxis_tickfont=dict(size=10),
    margin=dict(t=50, b=80),
    template=top_negative_fig.layout.template
)

round_win_rate = data.groupby('Round')['User_Win'].mean().reset_index()
round_win_rate['Win Rate'] = round_win_rate['User_Win'] * 100


def round_sorter(df):
    df_sorted = df.copy()
    df_sorted['Round_Sort'] = df_sorted['Round'].apply(
        lambda x: int(x) if x.isdigit() else float('inf') if x.startswith('P') else float('inf')
    )
    df_sorted['Playoff_Sort'] = df_sorted['Round'].apply(
        lambda x: int(x[1:]) if x.startswith('P') and x[1:].isdigit() else float('inf')
    )
    return df_sorted.sort_values(['Round_Sort', 'Playoff_Sort'])


round_win_rate = round_sorter(round_win_rate)
round_win_rate_fig = px.bar(
    round_win_rate, x='Round', y='Win Rate', title='Win Rate per Round',
    color_discrete_sequence=['#006994']
)
round_win_rate_fig.update_traces(hovertemplate='Round %{x}<br>Win Rate=%{y:.2f}%')
round_win_rate_fig.update_layout(yaxis_title="Win Rate (%)")


# ------------------------------------------------
# Color bins for DataTable
# ------------------------------------------------
def discrete_background_color_bins(n_bins=5, col_name='Win_Rate'):
    bounds = [i * (100.0 / n_bins) for i in range(n_bins + 1)]
    styles = []
    color_scale = px.colors.sequential.Blues
    for i in range(n_bins):
        min_bound = bounds[i]
        max_bound = bounds[i + 1]
        backgroundColor = color_scale[int(i * (len(color_scale) - 1) / (n_bins - 1))]
        text_color = 'white' if i > n_bins / 2 else 'black'
        styles.append({
            'if': {
                'filter_query': f'{{{col_name}}} >= {min_bound} && {{{col_name}}} < {max_bound}',
                'column_id': col_name
            },
            'backgroundColor': backgroundColor,
            'color': text_color
        })
    return styles


# ------------------------------------------------
# Helper: Re-apply the AG Grid filter model
# ------------------------------------------------
def apply_filter_model(df, filter_model):
    filtered = df.copy()
    for col, cond in filter_model.items():
        if cond.get('filterType') != 'text' or col not in filtered.columns:
            continue

        # single‐filter
        if 'filter' in cond:
            filtered = filtered[filtered[col].str.contains(cond['filter'], case=False, na=False)]
            continue

        # multi‐condition
        masks = []
        for sub in cond.get('conditions', []):
            masks.append(filtered[col].str.contains(sub.get('filter', ''), case=False, na=False))

        if cond.get('operator') == 'OR':
            combined = pd.Series(False, index=filtered.index)
            for m in masks:
                combined |= m
        else:  # AND
            combined = pd.Series(True, index=filtered.index)
            for m in masks:
                combined &= m

        filtered = filtered[combined]

    return filtered


# ------------------------------------------------
# Dash App Layout
# ------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
app.layout = dbc.Container(fluid=True, children=[
    html.Link(id="theme_link", rel="stylesheet", href=dbc.themes.LUX),

    dbc.NavbarSimple(
        brand=f"FaB History Analysis for {player_name} (GEM ID: {player_id})",
        color="primary",
        dark=True,
        children=[
            dbc.Select(
                id="theme_selector",
                options=[
                    {"label": name, "value": url}
                    for name, url in vars(dbc.themes).items() if name.isupper()
                ],
                value=dbc.themes.LUX,
                style={"width": "180px"}
            )
        ],
        className="mb-4"
    ),

    # Elo Over Time graph
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dcc.Graph(id='elo_over_time_graph', figure=daily_elo_fig),
                body=True
            ),
            width=12,
            className="mb-4"
        )
    ]),

    # Top Negative and Positive graphs
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dcc.Graph(id='top-negative-graph', figure=top_negative_fig),
                body=True
            ),
            width=6,
            className="mb-4"
        ),
        dbc.Col(
            dbc.Card(
                dcc.Graph(id='top-positive-graph', figure=top_positive_fig),
                body=True
            ),
            width=6,
            className="mb-4"
        )
    ]),

    # ----------------------------
    # All Matches (Filters + Summary + Grid)
    # ----------------------------
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader(html.H2("All Matches")),
                dbc.CardBody([
                    html.Div(id='aggrid_summary', className="mb-3"),

                    # AG Grid
                    AgGrid(
                        id='all_matches_grid',
                        filterModel={},
                        columnDefs=[
                            {"headerName": "Event Name", "field": "Event Name", "sortable": True, "filter": True},
                            {"headerName": "Event Date", "field": "Event Date", "sortable": True, "filter": True},
                            {"headerName": "Rated", "field": "Rated", "sortable": True, "filter": True},
                            {"headerName": "Round", "field": "Round", "sortable": True, "filter": True},
                            {"headerName": "Opponent", "field": "Opponent", "sortable": True, "filter": True},
                            {"headerName": "Result", "field": "Result", "sortable": True, "filter": True},
                            {"headerName": "Rating Change", "field": "Rating Change", "sortable": True, "filter": True},
                        ],
                        rowData=data.to_dict('records'),
                        defaultColDef={"resizable": True, "flex": 1, "sortable": True, "filter": True},
                        style={'height': '500px', 'width': '100%'}
                    )
                ])
            ], className="mb-4"),
            width=12
        )
    ]),

    # Additional Graphs: Top Opponents and Win Rate per Round
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dcc.Graph(id='top-opponents-graph', figure=top_opponents_fig),
                body=True
            ),
            width=6,
            className="mb-4"
        ),
        dbc.Col(
            dbc.Card(
                dcc.Graph(figure=round_win_rate_fig),
                body=True
            ),
            width=6,
            className="mb-4"
        )
    ]),

    # Opponent Win Rate Table
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader(html.H2("Opponents by Win Rate")),
                dbc.CardBody([
                    dcc.Checklist(
                        id='extreme_filter',
                        options=[{'label': 'Hide 0% / 100% Opponents', 'value': 'exclude'}],
                        value=['exclude'],
                        labelStyle={'display': 'inline-block'},
                        className="mb-3"
                    ),
                    dash_table.DataTable(
                        id='winrate_table',
                        columns=[
                            {'name': 'Opponent Name', 'id': 'Opponent_Name'},
                            {'name': 'Match Count', 'id': 'Match_Count'},
                            {'name': 'Win Rate (%)', 'id': 'Win_Rate'}
                        ],
                        filter_action='native',
                        sort_action='native',
                        sort_by=[{'column_id': 'Win_Rate', 'direction': 'desc'}],  # ← default sort
                        page_action='native',
                        page_size=15,
                        style_table={'overflowX': 'auto', 'border': 'thin lightgrey solid'},
                        style_cell={
                            'textAlign': 'left',
                            'padding': '8px',
                            'minWidth': '80px',
                            'width': '120px',
                            'maxWidth': '180px',
                        },
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_data_conditional=[
                                                   {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
                                               ] + discrete_background_color_bins(n_bins=5, col_name='Win_Rate')
                    )
                ])
            ], className="mb-4"),
            width=12
        )
    ]),

    # Footer
    dbc.Row(
        dbc.Col(
            html.Footer(
                f"Data last updated: {meta.get('Export Date', '')}",
                className="text-center text-muted"
            ),
            width=12
        ),
        className="mt-4"
    )
], className="p-4")


# ------------------------------------------------
# Callbacks
# ------------------------------------------------
@app.callback(
    Output("theme_link", "href"),
    Input("theme_selector", "value")
)
def change_theme(theme_url):
    return theme_url


@app.callback(
    Output('winrate_table', 'data'),
    Input('extreme_filter', 'value')
)
def update_winrate_table(extreme_filter):
    stats = data.groupby('Opponent_ID').agg(
        Match_Count=('Opponent_ID', 'size'),
        Win_Rate=('User_Win', 'mean')
    ).reset_index()
    stats['Win_Rate'] *= 100
    stats['Opponent_Name'] = stats['Opponent_ID'].map(id_to_name_map)

    if 'exclude' in extreme_filter:
        stats = stats[(stats['Win_Rate'] > 0) & (stats['Win_Rate'] < 100)]

    return stats[['Opponent_Name', 'Match_Count', 'Win_Rate']].to_dict('records')


@app.callback(
    Output('aggrid_summary', 'children'),
    Input('all_matches_grid', 'filterModel'),
    State('all_matches_grid', 'rowData')
)
def update_aggrid_summary(filter_model, row_data):
    """
    Re-apply the filter model to row_data in Python
    and compute summary stats for the filtered subset.
    """
    df = pd.DataFrame(row_data)

    # If no filterModel is set, use the entire dataset
    if not filter_model:
        filtered_df = df
    else:
        filtered_df = apply_filter_model(df, filter_model)

    total_matches = len(filtered_df)
    total_wins = sum(filtered_df['Result'].str.lower() == 'win')
    total_winrate = total_wins / total_matches if total_matches else 0
    total_opponents = filtered_df['Opponent'].nunique()
    net_elo = pd.to_numeric(filtered_df['Rating Change'], errors='coerce').fillna(0).sum()

    return html.Div([
        html.Span(f"Matches Shown: {total_matches}  |  "),
        html.Span(f"Win Rate: {total_winrate:.2%}  |  "),
        html.Span(f"Unique Opponents: {total_opponents}  |  "),
        html.Span(f"Net Elo Change: {net_elo:.2f}")
    ])


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        app.run(debug=False, host='0.0.0.0')
    else:
        app.run(debug=True, host='0.0.0.0')

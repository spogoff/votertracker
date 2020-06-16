
from __future__ import print_function
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import pandas as pd
import numpy as np
import dash
from dash.dependencies import Input, Output, State, Event
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt
import plotly.graph_objs as go
import plotly
from credentials import Credentials


# Google Sheet Credentials
SPREADSHEET_ID = "1DAan2yEhaO8Mt9VmADAxNbCwhX8usfsSL51Pw9m4Fh0/edit#gid=2032235041"
RANGE_NAME = 'Version 3.0!A:U'

# Map Credentials
MAPBOX_API_TOKEN = "pk.eyJ1Ijoic2FtaW5wb2dvZmY0MjAiLCJhIjoiY2thd3Z1ZmE3MDA2ajJwcDllNnoxcmNmcSJ9.dV2ZE99BHBltYFLHgNkx6w"


# <editor-fold desc=" ++++++ DATA METHODS ++++++ ">
def get_google_sheet(spreadsheet_id, range_name):
    """ Retrieve sheet data using OAuth credentials and Google Python API. """
    scopes = 'https://www.googleapis.com/auth/spreadsheets.readonly'
    # Setup the Sheets API
    store = file.Storage('credentials/client_secret.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials/client_secret.json', scopes)
        creds = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=creds.authorize(Http()))

    # Call the Sheets API
    gsheet = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    return gsheet


def _parse_dates(df):
    """ Converts dates with BCE or CE suffix to -int or +int year, format +-YYYY. """
    df.loc[df['Last Known Eruption'] == 'Unknown', 'Last Known Eruption'] = 'Unknown Unknown'
    years_str = df['Last Known Eruption'].str.split(' ')
    years_int = list()
    for y in years_str:
        if y[1] == 'BCE':
            years_int.append(int(y[0]) * -1)  # BCE dates become negative ints
        elif y[1] == 'CE':
            years_int.append(int(y[0]) * +1)  # CE dates become positive ints
        elif y[1] == 'Unknown':
            years_int.append(np.nan)
    df['Last Known Eruption'] = years_int
    return df

def _parse_elevations(df):
    print('is elev int?', type(df.loc[0, 'Elevation (m)']))
    df['Elevation (m)'] = df['Elevation (m)'].astype(int)
    print('is elev int?', type(df.loc[0, 'Elevation (m)']))
    df['Elevation (ft)'] = (df['Elevation (m)'].round(0) * 3.28084).astype(int)
    print('is elev int?', type(df.loc[0, 'Elevation (ft)']))
    return df

def parse_dataframe(df):
    df = _parse_dates(df)
    df = _parse_elevations(df)
    return df


def gsheet2df(gsheet):
    """ Converts Google sheet data to a Pandas DataFrame.
    Note: This script assumes that your data contains a header file on the first row!
    Also note that the Google API returns 'none' from empty cells - in order for the code
    below to work, you'll need to make sure your sheet doesn't contain empty cells,
    or update the code to account for such instances.
    """
    header = gsheet.get('values', [])[0]   # Assumes first line is header!
    values = gsheet.get('values', [])[1:]  # Everything else is data.
    if not values:
        print('No data found.')
    else:
        all_data = []
        for col_id, col_name in enumerate(header):
            column_data = []
            for row in values:
                column_data.append(row[col_id])
            ds = pd.Series(data=column_data, name=col_name)
            all_data.append(ds)
        df = pd.concat(all_data, axis=1)
    df = parse_dataframe(df)
    return df


gsheet = get_google_sheet(SPREADSHEET_ID, RANGE_NAME)
df = gsheet2df(gsheet)
print('Dataframe size = ', df.shape)
print(df.head())
# </editor-fold>


# Global Layout Template
layout = dict(
    autosize=True,
    height=500,
    font=dict(color='#CCCCCC'),
    titlefont=dict(color='#CCCCCC', size='14'),
    margin=dict(
        l=35,
        r=35,
        b=35,
        t=45
    ),
    hovermode="closest",
    plot_bgcolor="#191A1A",
    paper_bgcolor="#020202",
    legend=dict(font=dict(size=10), orientation='h'),
    title='Satellite Overview',
)


def plot_location_map():
    return html.Div([
        dcc.Graph(
            id='location-map-plot',
            config={'displayModeBar': True},
            figure={
                'data': [
                    # This plots a larger circle marker that's dark red - make's things look more like a volcano
                    go.Scattermapbox(
                        lat=df['Latitude'],
                        lon=df['Longitude'],
                        text=df['Volcano Name'],
                        hoverinfo='text',
                        mode='markers',
                        marker=dict(
                            size=17,
                            color='rgb(255, 0, 0)',
                        ),
                    ),
                    # This plots a smaller circle marker that's light red
                    go.Scattermapbox(
                        lat=df['Latitude'],
                        lon=df['Longitude'],
                        text=df['Volcano Name'],
                        hoverinfo='text',
                        mode='markers',
                        marker=dict(
                            size=8,
                            color='rgb(242, 177, 172)',
                        ),
                    ),
                ],
                'layout': go.Layout(
                    autosize=True,
                    hovermode='closest',
                    height=600,
                    showlegend=False,
                    plot_bgcolor=layout['plot_bgcolor'],
                    paper_bgcolor=layout['paper_bgcolor'],
                    mapbox=dict(
                        accesstoken=MAPBOX_API_TOKEN,
                        style="dark",
                        center=dict(
                            lat=37.615,
                            lon=23.335
                        ),
                        zoom=3
                    ),
                ),
            },
        )
    ])


app = dash.Dash(__name__)
server = app.server


app.layout = html.Div([
    html.Div([
        html.H1('LavaVino'),
        html.H3('Volcanic Wines of the World...'),
        html.Div([
            plot_location_map(),
        ]),
        dt.DataTable(
            rows=df.to_dict('records'),
            editable=False,
            row_selectable=True,
            filterable=True,
            sortable=True,
            selected_row_indices=[],
            id='datatable'
        ),
        html.Div(id='selected-indexes'),
        dcc.Graph(
            id='graph-datatable'
        ),
    ], className="six-columns"),
    html.Div([

    ]),
], className='two-columns')


external_css = ["https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
                "//fonts.googleapis.com/css?family=Raleway:400,300,600",
                "//fonts.googleapis.com/css?family=Dosis:Medium",
                "https://cdn.rawgit.com/plotly/dash-app-stylesheets/62f0eb4f1fadbefea64b2404493079bf848974e8/dash-uber-ride-demo.css",
                "https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css"]
for css in external_css:
    app.css.append_css({"external_url": css})


@app.callback(Output('datatable', 'selected_row_indices'),
              [Input('graph-datatable', 'clickData')],
              [State('datatable', 'selected_row_indices')])
def update_selected_row_indices(clickData, selected_row_indices):
    if clickData:
        for point in clickData['points']:
            if point['pointNumber'] in selected_row_indices:
                selected_row_indices.remove(point['pointNumber'])
            else:
                selected_row_indices.append(point['pointNumber'])
    return selected_row_indices


@app.callback(Output('graph-datatable', 'figure'),
              [Input('datatable', 'rows'),
               Input('datatable', 'selected_row_indices')])
def update_figure(rows, selected_row_indices):
    dff = pd.DataFrame(rows).sort_values('Last Known Eruption')
    fig = plotly.tools.make_subplots(rows=2, cols=1, subplot_titles=('Last Known Eruption', 'Elevation (m)'), shared_xaxes=False)
    marker = {'color': ['#0074D9']*len(dff)}
    for i in (selected_row_indices or []):
        marker['color'][i] = '#FF851B'
    fig.append_trace({
        'orientation': 'h',
        'y': dff['Volcano Name'],
        'x': dff['Last Known Eruption'],
        # 'text': dff['Volcano Name'],
        'type': 'bar',
        'marker': marker
    }, 1, 1)
    fig.append_trace({
        'orientation': 'v',
        'x': dff['Volcano Name'],
        'y': dff['Elevation (m)'],
        'text': dff['Volcano Name'],
        'type': 'bar',
        'marker': marker
    }, 2, 1)
    fig['layout']['showlegend'] = False
    fig['layout']['height'] = 800
    fig['layout']['width'] = 600
    fig['layout']['margin'] = {
        'l': 40,
        'r': 10,
        't': 60,
        'b': 200
    }
    return fig



if __name__ == "__main__":
    app.run_server(debug=True)

# -*- coding: utf-8 -*-
"""
Created on Tue Mar 26 14:59:14 2019

@author: ander906
"""
import base64
import io
import os
import json
import re

import dash_table
import numpy as np
import matplotlib.pyplot as plt
import skrf as rf
import plotly.graph_objs as go
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from flask_caching import Cache
from uuid import uuid4

from app import app

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': os.path.join(os.getcwd(), 'cache'),
    'CACHE_THRESHOLD': 20
})

write_snp = False

col_header_test = ["m{}".format(i) for i in range(4)]

layout = html.Div([
    dcc.Tabs(id="tabs-example", value='data-import', children=[
        dcc.Tab(label='Data Import', value='data-import'),
        dcc.Tab(label='SnP Viewer', value='snp-viewer'),
    ]),

    html.Div([
        html.Div(
            [
                html.H4("Loaded Data:"),
                html.Hr(),
                html.Div(
                    dash_table.DataTable(
                        id='uploaded-data-table',
                        style_cell={
                            'whiteSpace': 'normal',
                            'textAlign': 'left'
                        },
                        style_table={
                            'table-layout': 'fixed',
                            'width': '100%',
                        },
                        css=[{
                            'selector': '.dash-cell div.dash-cell-value',
                            'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
                        }],
                        columns=[{"name": "Loaded Networks",
                                  "id": "data"}],
                        editable=False,
                        row_selectable="multi",
                        selected_rows=[],
                    ), style={'overflowX': 'auto'}
                ),
                dcc.Loading(id="loading-upload",
                            children=[html.Div(id='loaded-S-data')],
                            type="default"),
            ], className='three columns', style={'word-wrap': 'break-word'},
        ),
        html.Div(id='tabs-content', className='nine columns'), ], className='row'
    ),
    html.Div(id='loaded-S-data', style={'display': 'none'}),
    html.Div(id='uuid-hidden-div',
             children=str(uuid4()),
             style={'display': 'none'})
])


@app.callback(Output('tabs-content', 'children'),
              [Input('tabs-example', 'value')])
def render_content(tab):
    if tab == 'data-import':
        return html.Div([dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select a Touchstone File'),
                ' (~20 MB max).'
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=True
        ),
        ])
    if tab == 'snp-viewer':
        return html.Div([
            html.Div([
                html.Div([
                    html.Button('Plot', id='button'),
                    html.Details(id='parameter-control-div', open=True, children=[
                        html.Summary('Parameter Selection'),
                        html.Label('Parameter Type'),
                        dcc.RadioItems(
                            id='parm-select',
                            options=[
                                {'label': 'S Parameters', 'value': 'S'},
                                {'label': 'Y Parameters', 'value': 'Y'},
                                {'label': 'Z Parameters', 'value': 'Z'}
                                # {'label': 'ABCD Parameters', 'value': 'A'}
                            ],
                            value='S'),
                        html.Label('Plot Axes'),
                        dcc.RadioItems(
                            id='axes-select',
                            options=[
                                {'label': 'Magnitude/Phase', 'value': 'MAG'},
                                {'label': 'Real/Imaginary', 'value': 'RI'},
                                {'label': 'Bode', 'value': 'Bode'}
                            ],
                            value='MAG')]),
                    html.Details(id='port-table-div', children=[
                        html.Summary('Port Selection'),
                        html.Div(
                            dash_table.DataTable(
                                id='port-table',
                                css=[{
                                    'selector': '.dash-cell div.dash-cell-value',
                                    'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
                                }],
                                columns=[{"name": "Parameters",
                                          "id": "Parameters"}],
                                editable=False,
                                row_selectable="multi",
                                selected_rows=[],
                            ),
                        ),
                        # html.Div(
                        #     dash_table.DataTable(
                        #         id='port-table-test',
                        #         css=[{
                        #             'selector': '.dash-cell div.dash-cell-value',
                        #             'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
                        #         }],
                        #         style_table={'overflowX': 'scroll'},
                        #         columns=[{"name": i,
                        #                   "id": i,
                        #                   'presentation': 'dropdown'}
                        #                  for i in col_header_test],
                        #         data=[{i:j for i in col_header_test} for j in ['Plot']*len(col_header_test)],
                        #         dropdown={
                        #             j: {
                        #                 'options': [
                        #                     {'label': i, 'value': i}
                        #                     for i in ['Plot','Off']
                        #                 ]
                        #             } for j in col_header_test},
                        #         style_data_conditional=[
                        #             {
                        #                 'if': {
                        #                     'column_id': 'm0',
                        #                     'filter_query': '{m0} contains "Plot"'
                        #                 },
                        #                 'backgroundColor': '#38af2c3',
                        #             }],
                        #         # style_data_conditional=[
                        #         #     {
                        #         #         'if': {
                        #         #             'column_id': i,
                        #         #             'filter_query': '{{{}}} contains "l"'.format(i)
                        #         #         },
                        #         #         'backgroundColor': '#38af2c3',
                        #         #     } for i in col_header_test],
                        #         editable=True,
                        #         selected_rows=[],
                        #     ),
                        # )
                    ]
                                 ),
                    # html.Hr(),
                ], className="three columns"),
                html.Div([
                    html.Div(id='output-plot'),
                    dcc.Loading(id="loading-plot",
                                children=[html.Div(id='output-plot')],
                                type="default")
                ], className="nine columns")
            ], className="row"),
        ])


class TouchstoneEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.complex):
            return np.real(obj), np.imag(obj)  # split into [real, im]
        if isinstance(obj, rf.Frequency):
            return obj.f.tolist()
        return json.JSONEncoder.default(self, obj)

def to_json(network):
    return json.dumps(network, cls=TouchstoneEncoder)

def from_json(obj):
    ntwk = rf.Network(f_unit='hz')
    ntwk.name = obj['name']
    ntwk.comments = obj['comments']
    ntwk.port_names = obj['port_names']
    ntwk.z0 = np.array(obj['_z0'])[..., 0] + np.array(obj['_z0'])[..., 1] * 1j  # recreate complex numbers
    ntwk.s = np.array(obj['_s'])[..., 0] + np.array(obj['_s'])[..., 1] * 1j
    ntwk.f = np.array(obj['_frequency'])
    ntwk.variables = obj['variables']
    return ntwk


def load_touchstone(content_string: str, filename: str) -> rf.Network:
    """
    Loads s-parameter data into a skrf network object from an uploaded encoded str.

    Parameters
    ----------
    content_string : str
        Encoded string containing touchstone data
    filename : str
        The filename of the touchstone file.
    Returns
    -------
    d : skrf.Network
        A skrf Network object holding s-parameter data from the touchstone file.

    """
    class dataIO(io.BytesIO):
        """Class used to trick skrf into thinking it is reading a file object."""
        _filename: str

        def __init__(self, data, filename):
            super(dataIO, self).__init__(data)
            self.name = filename

        @property
        def name(self):
            """Filename of SnP data."""
            return self._name

        @name.setter
        def name(self, value):
            assert isinstance(value, str)
            self._name = value

    data = dataIO(content_string, filename)
    d = rf.Network()
    d.read_touchstone(data)
    return d


@app.callback([Output('port-table-div', 'open'),
               Output('port-table', 'data')],
              # [Input('tabs-example', 'value')],
              [Input('button', 'n_clicks')],
              [State('loaded-S-data', 'children')])
def update_port_table(_, json_data):
    if not json_data:
        return False, []
    else:
        maxports = 0
        data = json.loads(json_data['props']['children'])
        for key, val in data.items():
            if write_snp:
                ntwk = load_touchstone(val.encode(), key)
            else:
                ntwk = from_json(val)
            if maxports < ntwk.nports:
                maxports = ntwk.nports
        ports = []
        for i in range(maxports):
            for j in range(maxports):
                ports.append({"Parameters": '{}{}'.format(i + 1, j + 1)})
        return True, ports


@app.callback([Output('loaded-S-data', 'children'),
               Output('uploaded-data-table', 'data')],
              [Input('upload-data', 'contents')],
              [State('upload-data', 'filename'),
               State('upload-data', 'last_modified')])
def update_s_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        ch = []
        ports = []
        d = {}
        d2 = []
        content_type = []
        content_string = []
        for i, c in enumerate(list_of_contents):
            ct, cs = c.split(',')
            content_type.append(ct)
            content_string.append(cs)
        for c, n in zip(content_string, list_of_names):
            decoded = base64.b64decode(c)
            try:
                data = load_touchstone(decoded, n)
            except Exception as e:
                print(e)
                return (html.Div([
                    'There was an error processing this file.'
                ]),
                        html.Div([]))
            d2.append({'data': data.__str__()})
            if write_snp:
                d[n] = data.write_touchstone(return_string=True)
            else:
                d[n] = data.__dict__

        return html.Div(json.dumps(d, cls=TouchstoneEncoder)), d2

@app.callback(
    Output('output-plot', "children"),
    [Input('button', 'n_clicks')],
    #    Input('nsmooth_input', 'n_submit'), Input('nsmooth_input', 'n_blur')],
    [State('parm-select', 'value'),
     State('axes-select', 'value'),
     State('uploaded-data-table', "derived_virtual_selected_rows"),
     State('uploaded-data-table', "derived_virtual_data"),
     State('port-table', "derived_virtual_selected_rows"),
     State('port-table', "derived_virtual_data"),
     State('loaded-S-data', 'children'),
     ])
def update_graph(n_clicks, parm, axes_format, selected_ntwk_rows, selected_ntwk_data,
                 selected_rows, selected_data, s_data):
    if not selected_ntwk_rows:
        return html.Div(children='Please Upload and Select Data to Plot.')
    elif not selected_rows:
        return html.Div(children='Please Select Ports to Plot.')
    else:
        s_data = json.loads(s_data['props']['children'])
        data = {}
        for r in selected_ntwk_rows:
            m = re.search(r"Network: '(.*)', ", selected_ntwk_data[r]['data'])
            if m:
                for key, val in s_data.items():
                    if re.search(m.group(1), key):
                        data[key] = val
        # json_data = s_data

        traces1 = []
        traces2 = []
        layout1 = []
        layout2 = []

        for key, val in data.items():
            if write_snp:
                ntwk = load_touchstone(val.encode(), key)
            else:
                ntwk = from_json(val)
            if parm == 'S':
                pass
            elif parm == 'Y':
                ntwk.s = ntwk.y
            elif parm == 'Z':
                ntwk.s = ntwk.z
            elif parm == 'A':
                ntwk.s = ntwk.a
            for i in range(len(ntwk.s[0, :, 0])):
                for j in range(len(ntwk.s[0, 0, :])):
                    for k in selected_rows:
                        if selected_data[k]['Parameters'] == f'{i+1}{j+1}':
                            yvals1 = []
                            yvals2 = []
                            if axes_format == "MAG":
                                yvals1.append(np.abs(ntwk.s[:, i, j]))
                                yvals2.append(np.angle(ntwk.s[:, i, j]))
                            elif axes_format == "RI":
                                yvals1.append(np.real(ntwk.s[:, i, j]))
                                yvals2.append(np.imag(ntwk.s[:, i, j]))
                            elif axes_format == "Bode":
                                # mpl_to_plotly and plotly don't support Bode plots, so data is plotted
                                # in mpl and read in as image. traces1 stores y data, traces2 stores
                                # trace labels for figure
                                traces1.append(ntwk.s[:, i, j])
                                traces2.append(f'{parm}{i + 1}{j + 1}')
                                continue  # skip normal plotly output

                            traces1.append(
                                go.Scatter(x=ntwk.f, y=yvals1[0],
                                           name='{}{}{} {}'.format(parm, i + 1, j + 1, key)
                                           )
                            )
                            traces2.append(
                                go.Scatter(x=ntwk.f, y=yvals2[0],
                                           name='{}{}{} {}'.format(parm, i + 1, j + 1, key)
                                           )
                            )
                        else:
                            continue

# Define Layouts
        if axes_format == "MAG":
            layout1.append(go.Layout(
                xaxis={'title': 'Frequency [Hz]',
                       'exponentformat': 'SI'},
                yaxis={'type': 'log',
                       'title': '{} Parameter Magnitude'.format(parm)},
                margin={'l': 60, 'b': 40, 't': 10, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest'
            ))
            layout2.append(go.Layout(
                xaxis={'title': 'Frequency [Hz]',
                       'exponentformat': 'SI'},
                yaxis={'type': 'linear',
                       'title': '{} Parameter Phase'.format(parm)},
                margin={'l': 60, 'b': 40, 't': 10, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest'
            ))
        elif axes_format == "RI":
            layout1.append(go.Layout(
                xaxis={'title': 'Frequency [Hz]',
                       'exponentformat': 'SI'},
                yaxis={'type': 'linear',
                       'title': '{} Parameter Real'.format(parm)},
                margin={'l': 60, 'b': 40, 't': 10, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest'
            ))
            layout2.append(go.Layout(
                xaxis={'title': 'Frequency [Hz]',
                       'exponentformat': 'SI'},
                yaxis={'type': 'linear',
                       'title': '{} Parameter Imaginary'.format(parm)},
                margin={'l': 60, 'b': 40, 't': 10, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest'
            ))
        elif axes_format == "Bode":
            # See https://github.com/4QuantOSS/DashIntro/blob/master/notebooks/Tutorial.ipynb
            # for example of encoding mpl figure to image for dash
            fig = plt.figure()
            ax1 = fig.add_subplot(111)
            legend_entry = []
            for i, s in enumerate(traces1):
                if parm == 'Y':
                    rf.plotting.plot_smith(s, ax=ax1, label=traces2[i], chart_type='y')
                else:
                    rf.plotting.plot_smith(s, ax=ax1, label=traces2[i])
            out_img = io.BytesIO()
            fig.savefig(out_img, format='png')
            fig.clf()
            plt.close('all')
            out_img.seek(0)  # rewind file
            encoded = base64.b64encode(out_img.read()).decode("ascii").replace("\n", "")
            return html.Div([  # skip normal plotly graph return and return image of plt.figure() instead
                html.Div('Interactive Bode plots not yet supported.'),
                html.Img(src="data:image/png;base64,{}".format(encoded))
            ])
        return html.Div(
            [
                dcc.Graph(figure={'data': traces1, 'layout': layout1[0]}),
                dcc.Graph(figure={'data': traces2, 'layout': layout2[0]})
            ]
        )

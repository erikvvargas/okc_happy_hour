import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
from datetime import datetime, time
import pandas as pd
import os
from geopy.geocoders import Nominatim
from data_store import (
    load_locations,
    insert_location,
    update_description,
    delete_location
)

# Initialize the Dash app with Bootstrap for mobile responsiveness
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME], suppress_callback_exceptions=True)
server = app.server
app.title = "OKC Happy Hours"

# Initialize geocoder
geolocator = Nominatim(user_agent="okc_happy_hours_app")


# Helper functions
def geocode_address(address):
    """Convert address to lat/lon coordinates"""
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None

def time_to_minutes(time_str):
    """Convert HH:MM to minutes since midnight"""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m

def minutes_to_time(minutes):
    """Convert minutes since midnight to HH:MM"""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def get_locations(day_filter=None, time_filter=None):
    df = load_locations()

    if not df.empty:
        if day_filter and day_filter != "All":
            df = df[df['days'].str.contains(day_filter, na=False)]

        if time_filter:
            df = df[
                (df['start_time'] <= time_filter) &
                (df['end_time'] >= time_filter)
            ]

    return df


def create_map(df, dark_mode=False):
    if not df.empty:
        # Create hover text
        df['hover_text'] = (
            "<b>" + df['name'] + "</b><br>" +
            df['address'] + "<br>" +
            df['description'] + "<br>" +
            "Days: " + df['days'] + "<br>" +
            "Time: " + df['start_time'] + " - " + df['end_time']
        )
        
        fig = px.scatter_map(
            df,
            lat='lat',
            lon='lon',
            hover_name='name',
            hover_data={'lat': False, 'lon': False, 'hover_text': True},
            zoom=12,
            height=800
        )
        # Update marker appearance
        fig.update_traces(
            marker = dict(size=14, line=dict(width=2,
                                             color='DarkSlateGrey')),
            hovertemplate='%{customdata[0]}<extra></extra>'
        )
        
        # Customize hover data to show our formatted text
        fig.update_traces(customdata=df[['hover_text']])
        #fig.update_traces(cluster=dict(enabled=True))
    else:
        # Empty map centered on OKC
        empty_df = pd.DataFrame({'lat': [35.4676], 'lon': [-97.5164]})
        fig = px.scatter_map(
            empty_df,
            lat='lat',
            lon='lon',
            zoom=12,
            height=600
        )
        fig.update_traces(marker=dict(size=0))
        # #fig.update_traces(cluster=dict(enabled=True))
    # Set map style based on theme
    map_style = "carto-darkmatter" if dark_mode else "open-street-map"
    
    fig.update_layout(
        mapbox_style=map_style,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# Sidebar for adding locations
sidebar = html.Div([
    dbc.Button(
        [html.I(className="fas fa-plus me-2"), "Add Location"],
        id="sidebar-toggle",
        color="primary",
        className="mb-3 w-100",
        size="sm"
    ),
    dbc.Offcanvas([
        html.H4("Add Happy Hour Location", className="mb-3"),
        
        dbc.Label("Name:", className="fw-bold"),
        dbc.Input(id='input-name', type='text', placeholder='Bar/Restaurant Name', className="mb-3"),
        
        dbc.Label("Address:", className="fw-bold"),
        dbc.Input(id='input-address', type='text', 
                 placeholder='Full address with city and state', className="mb-3"),
        
        dbc.Label("Description:", className="fw-bold"),
        dbc.Textarea(id='input-description', 
                    placeholder='Happy hour specials...', className="mb-3", rows=3),
        
        dbc.Label("Days:", className="fw-bold"),
        dbc.Checklist(
            id='input-days',
            options=[
                {'label': 'Mon', 'value': 'Monday'},
                {'label': 'Tue', 'value': 'Tuesday'},
                {'label': 'Wed', 'value': 'Wednesday'},
                {'label': 'Thu', 'value': 'Thursday'},
                {'label': 'Fri', 'value': 'Friday'},
                {'label': 'Sat', 'value': 'Saturday'},
                {'label': 'Sun', 'value': 'Sunday'},
            ],
            value=[],
            className="mb-3"
        ),
        
        dbc.Label("Happy Hour Time Range:", className="fw-bold"),
        html.Div([
            dcc.RangeSlider(
                id='time-slider',
                min=0,
                max=1440,
                step=30,
                value=[900, 1140],  # 3 PM to 7 PM in minutes
                marks={
                    0: '12 AM',
                    360: '6 AM',
                    720: '12 PM',
                    1080: '6 PM',
                    1440: '12 AM'
                },
                tooltip={"placement": "bottom", "always_visible": False}
            ),
            html.Div(id='time-display', className="text-center mt-2 fw-bold")
        ], className="mb-3"),
        
        dbc.Button("Add Location", id='submit-button', color='success', 
                  className="w-100 mb-2"),
        html.Div(id='submit-feedback', className="mt-2")
    ],
    id="sidebar-collapse",
    is_open=False,
    placement="start",
    style={"width": "350px"}
    ),
], className="mb-3")

# Navigation bar
navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Map", href="/", id="map-link")),
        # dbc.NavItem(dbc.NavLink("Manage", href="/manage", id="manage-link")),
    ],
    brand="🍺 OKC Happy Hours",
    brand_href="/",
    color="primary",
    dark=True,
    className="mb-3"
)

# Map page layout
map_page = html.Div([
    dbc.Container([
        # dbc.Row([
        #     dbc.Col([
        #         sidebar
        #     ], width=12, className="mb-2")
        # ]),
        
        dbc.Row([
            dbc.Col([
                html.Label("Day of Week:", className="fw-bold small"),
                dcc.Dropdown(
                    id='day-filter',
                    options=[
                        {'label': 'All Days', 'value': 'All'},
                        {'label': 'Monday', 'value': 'Mon'},
                        {'label': 'Tuesday', 'value': 'Tue'},
                        {'label': 'Wednesday', 'value': 'Wed'},
                        {'label': 'Thursday', 'value': 'Thu'},
                        {'label': 'Friday', 'value': 'Fri'},
                        {'label': 'Saturday', 'value': 'Sat'},
                        {'label': 'Sunday', 'value': 'Sun'},
                    ],
                    value='All',
                    clearable=False,
                    className="mb-3"
                )
            ], xs=12, md=6),
            
            dbc.Col([
                html.Label("Time:", className="fw-bold small"),
                dcc.Dropdown(
                    id='time-filter',
                    options=[
                        {'label': 'All Times', 'value': ''},
                        {'label': '3:00 PM', 'value': '15:00'},
                        {'label': '4:00 PM', 'value': '16:00'},
                        {'label': '5:00 PM', 'value': '17:00'},
                        {'label': '6:00 PM', 'value': '18:00'},
                        {'label': '7:00 PM', 'value': '19:00'},
                        {'label': '8:00 PM', 'value': '20:00'},
                    ],
                    value='',
                    clearable=False,
                    className="mb-3"
                )
            ], xs=12, md=6),
        ]),
        
        dbc.Row([
            dbc.Col([
                dcc.Graph(
                    id='map', 
                    config={'displayModeBar': False},
                    style={'height': '70vh', 'minHeight': '400px'}
                )
            ], width=12)
        ])
    ], fluid=True, className="px-3 px-md-4 py-2")
])

# Management page layout
manage_page = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                sidebar
            ], width=12, className="mb-4")
        ]),
        dbc.Row([
            dbc.Col([
                html.H3("Manage Locations", className="mb-4"),
                html.Div(id='manage-feedback', className="mb-3"),
                html.Div(id='locations-table-container')
            ])
        ])
    ], fluid=True, className="px-3 px-md-4 py-4")
])

# App Layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='theme-store', data='light'),
    dcc.Store(id='refresh-trigger', data=0),
    dcc.Store(id='manage-refresh', data=0),
    dcc.Store(id="auth-store", data=False),

    html.Div(id='theme-container', children=[
        navbar,
        html.Div(id='page-content')
    ])
], style={"minHeight": "100vh"})

# login form for admin auth
login_form = dbc.Card(
    dbc.CardBody([
        html.H4("Admin Login", className="mb-3"),
        dbc.Input(
            id="password-input",
            type="password",
            placeholder="Enter admin password",
            className="mb-2"
        ),
        dbc.Button("Login", id="login-btn", color="primary"),
        html.Div(id="login-feedback", className="mt-2")
    ]),
    style={"maxWidth": "400px", "margin": "auto"}
)


# Callbacks
# @app.callback(
#     Output('page-content', 'children'),
#     Input('url', 'pathname')
# )
# def display_page(pathname):
#     if pathname == '/manage':
#         return manage_page
#     else:
#         return map_page


@app.callback(
    Output("auth-store", "data"),
    Output("login-feedback", "children"),
    Output("url", "pathname"),
    Input("login-btn", "n_clicks"),
    State("password-input", "value"),
    prevent_initial_call=True
)
def login(n_clicks, password):
    if password == os.getenv("ADMIN_PASSWORD"):
        return True, dbc.Alert("Login successful", color="success"), "/manage"

    return False, dbc.Alert("Incorrect password", color="danger"), dash.no_update


@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    Input('auth-store', 'data')
)
def display_page(pathname, is_authed):
    if pathname == "/manage":
        if is_authed:
            return manage_page
        return login_form
    return map_page


@app.callback(
    Output("sidebar-collapse", "is_open"),
    Input("sidebar-toggle", "n_clicks"),
    State("sidebar-collapse", "is_open"),
)
def toggle_sidebar(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output('time-display', 'children'),
    Input('time-slider', 'value')
)
def update_time_display(value):
    if value:
        start_time = minutes_to_time(value[0])
        end_time = minutes_to_time(value[1])
        return f"{start_time} - {end_time}"
    return ""

@app.callback(
    Output('map', 'figure'),
    Input('day-filter', 'value'),
    Input('time-filter', 'value'),
    Input('refresh-trigger', 'data'),
    Input('theme-store', 'data'),
    Input('url', 'pathname'),   # 👈 ADD THIS
)
def update_map(day, time, refresh, theme, pathname):
    if pathname != "/":
        raise dash.exceptions.PreventUpdate

    df = get_locations(day, time if time else None)
    dark_mode = theme == 'dark'
    return create_map(df, dark_mode)

@app.callback(
    [Output('submit-feedback', 'children'),
     Output('input-name', 'value'),
     Output('input-address', 'value'),
     Output('input-description', 'value'),
     Output('input-days', 'value'),
     Output('time-slider', 'value'),
     Output('refresh-trigger', 'data')],
    [Input('submit-button', 'n_clicks')],
    [State('input-name', 'value'),
     State('input-address', 'value'),
     State('input-description', 'value'),
     State('input-days', 'value'),
     State('time-slider', 'value'),
     State('refresh-trigger', 'data')]
)
def add_location(n_clicks, name, address, desc, days, time_range, refresh_count):
    if n_clicks is None:
        return "", None, None, None, [], [900, 1140], 0
    
    if not all([name, address, days, time_range]):
        return (dbc.Alert("Please fill in all required fields.", color="warning"), 
                name, address, desc, days, time_range, refresh_count)
    
    # Geocode the address
    lat, lon = geocode_address(address)
    
    if lat is None or lon is None:
        return (dbc.Alert("Could not find location. Please check the address.", color="danger"), 
                name, address, desc, days, time_range, refresh_count)
    
    # Convert time range to HH:MM format
    start_time = minutes_to_time(time_range[0])
    end_time = minutes_to_time(time_range[1])
    
    # Convert days list to comma-separated string
    days_str = ",".join(days)
    
    try:

        insert_location({
            "name": name,
            "address": address,
            "lat": lat,
            "lon": lon,
            "description": desc,
            "days": days_str,
            "start_time": start_time,
            "end_time": end_time
        })

        # Clear form on success and trigger map refresh
        return (dbc.Alert("Location added successfully!", color="success", duration=3000), 
                "", "", "", [], [900, 1140], refresh_count + 1)
    except Exception as e:
        return (dbc.Alert(f"Error: {str(e)}", color="danger"), 
                name, address, desc, days, time_range, refresh_count)

@app.callback(
    Output('locations-table-container', 'children'),
    Input('manage-refresh', 'data')
)
def update_locations_table(refresh):
    df = load_locations().sort_values("name")
    
    if df.empty:
        return dbc.Alert("No locations found.", color="info")
    
    # Create table with edit/delete buttons
    table_data = []
    for _, row in df.iterrows():
        table_data.append(
            html.Tr([
                html.Td(row['name']),
                html.Td(row['address']),
                html.Td(
                    dbc.Textarea(
                        id={'type': 'desc-input', 'index': row['id']},
                        value=row['description'],
                        rows=2,
                        style={'width': '100%', 'fontSize': '0.9rem'}
                    )
                ),
                html.Td(row['days']),
                html.Td(f"{row['start_time']} - {row['end_time']}"),
                html.Td([
                    dbc.Button(
                        "Save",
                        id={'type': 'save-btn', 'index': row['id']},
                        color="primary",
                        size="sm",
                        className="me-2"
                    ),
                    dbc.Button(
                        "Delete",
                        id={'type': 'delete-btn', 'index': row['id']},
                        color="danger",
                        size="sm"
                    )
                ])
            ])
        )
    
    return dbc.Table([
        html.Thead(
            html.Tr([
                html.Th("Name"),
                html.Th("Address"),
                html.Th("Description"),
                html.Th("Days"),
                html.Th("Time"),
                html.Th("Actions", style={'width': '180px'})
            ])
        ),
        html.Tbody(table_data)
    ], bordered=True, hover=True, responsive=True, striped=True)

@app.callback(
    [Output('manage-feedback', 'children'),
     Output('manage-refresh', 'data')],
    [Input({'type': 'save-btn', 'index': dash.dependencies.ALL}, 'n_clicks'),
     Input({'type': 'delete-btn', 'index': dash.dependencies.ALL}, 'n_clicks')],
    [State({'type': 'desc-input', 'index': dash.dependencies.ALL}, 'value'),
     State({'type': 'desc-input', 'index': dash.dependencies.ALL}, 'id'),
     State('manage-refresh', 'data')],
    prevent_initial_call=True
)
def handle_table_actions(save_clicks, delete_clicks, descriptions, desc_ids, refresh_count):
    ctx = callback_context
    
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    triggered_id = ctx.triggered[0]['prop_id']
    
    try:
        # Parse which button was clicked
        if 'save-btn' in triggered_id:
            # Extract the index from triggered_id
            import json
            button_info = json.loads(triggered_id.split('.')[0])
            location_id = button_info['index']
            
            # Find the corresponding description
            desc_value = None
            for i, desc_id in enumerate(desc_ids):
                if desc_id['index'] == location_id:
                    desc_value = descriptions[i]
                    break
            
            if desc_value is not None:

                update_description(location_id, desc_value)

                return (dbc.Alert("Description updated successfully!", color="success", duration=3000),
                        refresh_count + 1)
        
        elif 'delete-btn' in triggered_id:
            import json
            button_info = json.loads(triggered_id.split('.')[0])
            location_id = button_info['index']
            
            delete_location(location_id)
       
            return (dbc.Alert("Location deleted successfully!", color="success", duration=3000),
                    refresh_count + 1)
    
    except Exception as e:
        return (dbc.Alert(f"Error: {str(e)}", color="danger", duration=5000),
                refresh_count)
    
    return dash.no_update, dash.no_update

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8050, debug=True)


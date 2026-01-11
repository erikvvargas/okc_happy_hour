# app.py - Main application

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from db import init_db, get_locations, add_location
from map import create_map, create_sidebar, create_filters, geocode_address, minutes_to_time

# Initialize the Dash app with Bootstrap for mobile responsiveness
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
app.title = "OKC Happy Hours"

# Initialize database
init_db()

# App Layout
app.layout = html.Div([
    dcc.Store(id='theme-store', data='light'),
    dcc.Store(id='refresh-trigger', data=0),
    
    # Fixed theme toggle button
    dbc.Button(
        html.I(id='theme-icon', className="fas fa-moon"),
        id="theme-toggle",
        color="secondary",
        size="sm",
        outline=True,
        style={
            "position": "fixed",
            "top": "10px",
            "right": "10px",
            "zIndex": "1050"
        }
    ),
    
    html.Div(id='theme-container', children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("🍺 OKC Happy Hours", className="text-center my-3 mb-2"),
                    dbc.Button(
                        [html.I(className="fas fa-cog me-2"), "Admin"],
                        href="http://localhost:8051",
                        target="_blank",
                        color="secondary",
                        size="sm",
                        className="mb-3"
                    )
                ])
            ]),
            
            dbc.Row([
                dbc.Col([
                    create_sidebar()
                ], width=12, className="mb-2")
            ]),
            
            dbc.Row(create_filters()),
            
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
], style={"minHeight": "100vh"})

# Callbacks
@app.callback(
    [Output('theme-container', 'style'),
     Output('theme-icon', 'className'),
     Output('theme-store', 'data')],
    Input('theme-toggle', 'n_clicks'),
    State('theme-store', 'data'),
    prevent_initial_call=True
)
def toggle_theme(n_clicks, current_theme):
    if n_clicks:
        if current_theme == 'light':
            return (
                {'backgroundColor': '#1a1a1a', 'color': '#ffffff', 'minHeight': '100vh'},
                'fas fa-sun',
                'dark'
            )
        else:
            return (
                {'backgroundColor': '#ffffff', 'color': '#000000', 'minHeight': '100vh'},
                'fas fa-moon',
                'light'
            )
    return dash.no_update

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
    [Input('day-filter', 'value'),
     Input('time-filter', 'value'),
     Input('refresh-trigger', 'data'),
     Input('theme-store', 'data')]
)
def update_map(day, time, refresh, theme):
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
def add_location_callback(n_clicks, name, address, desc, days, time_range, refresh_count):
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
    
    success, message = add_location(name, address, lat, lon, desc, days_str, start_time, end_time)
    
    if success:
        # Clear form on success and trigger map refresh
        return (dbc.Alert(message, color="success", duration=3000), 
                "", "", "", [], [900, 1140], refresh_count + 1)
    else:
        return (dbc.Alert(message, color="danger"), 
                name, address, desc, days, time_range, refresh_count)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8050, debug=True)
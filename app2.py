import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import sqlite3
from datetime import datetime, time
import pandas as pd
from geopy.geocoders import Nominatim

# Initialize the Dash app with Bootstrap for mobile responsiveness
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
app.title = "OKC Happy Hours"

# Initialize geocoder
geolocator = Nominatim(user_agent="okc_happy_hours_app")

# Database setup
def init_db():
    conn = sqlite3.connect('happy_hours.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS locations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  address TEXT NOT NULL,
                  lat REAL NOT NULL,
                  lon REAL NOT NULL,
                  description TEXT,
                  days TEXT,
                  start_time TEXT,
                  end_time TEXT)''')
    
    # Check if table is empty and add sample data
    c.execute("SELECT COUNT(*) FROM locations")
    if c.fetchone()[0] == 0:
        sample_data = [
            ("The Pump Bar", "2425 N Walker Ave, Oklahoma City, OK", 35.4945, -97.5264, 
             "$3 wells, $4 drafts", "Monday,Tuesday,Wednesday,Thursday,Friday", "15:00", "19:00"),
            ("Fassler Hall", "7 E Sheridan Ave, Oklahoma City, OK", 35.4676, -97.5164,
             "$5 beer & brats", "Monday,Tuesday,Wednesday,Thursday,Friday", "16:00", "18:00"),
            ("Empire Slice House", "4029 N Western Ave, Oklahoma City, OK", 35.5153, -97.5347,
             "$2 off pizzas, $1 off drinks", "Monday,Tuesday,Wednesday,Thursday", "15:00", "18:00"),
        ]
        c.executemany("""INSERT INTO locations 
                        (name, address, lat, lon, description, days, start_time, end_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", sample_data)
        conn.commit()
    
    conn.close()

init_db()

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
    conn = sqlite3.connect('happy_hours.db')
    df = pd.read_sql_query("SELECT * FROM locations", conn)
    conn.close()
    
    if not df.empty:
        # Filter by day
        if day_filter and day_filter != "All":
            df = df[df['days'].str.contains(day_filter, na=False)]
        
        # Filter by time
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
            # marker=dict(size=14, color='#e74c3c'),
            marker = dict(size=14),
            hovertemplate='%{customdata[0]}<extra></extra>'
        )
        
        # Customize hover data to show our formatted text
        fig.update_traces(customdata=df[['hover_text']])
    else:
        # Empty map centered on OKC
        empty_df = pd.DataFrame({'lat': [35.4676], 'lon': [-97.5164]})
        fig = px.scatter_map(
            empty_df,
            lat='lat',
            lon='lon',
            zoom=12,
            height=800
        )
        fig.update_traces(marker=dict(size=0))
    
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
                {'label': 'Mon', 'value': 'Mon'},
                {'label': 'Tue', 'value': 'Tue'},
                {'label': 'Wed', 'value': 'Wed'},
                {'label': 'Thu', 'value': 'Thu'},
                {'label': 'Fri', 'value': 'Fri'},
                {'label': 'Sat', 'value': 'Sat'},
                {'label': 'Sun', 'value': 'Sun'},
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

# App Layout
app.layout = html.Div([
    dcc.Store(id='theme-store', data='light'),
    dcc.Store(id='refresh-trigger', data=0),
    
    html.Div(id='theme-container', children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H1("🍺 OKC Happy Hours", className="text-center my-3 mb-2"),
                        # dbc.Button(
                        #     html.I(id='theme-icon', className="fas fa-moon"),
                        #     id="theme-toggle",
                        #     color="secondary",
                        #     size="sm",
                        #     className="position-absolute top-0 end-0 m-3",
                        #     outline=True
                        # )
                    ], style={"position": "relative"})
                ])
            ]),
            
            dbc.Row([
                dbc.Col([
                    sidebar
                ], width=12, className="mb-2")
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Day of Week:", className="fw-bold small"),
                    dcc.Dropdown(
                        id='day-filter',
                        options=[
                            {'label': 'All Days', 'value': 'All'},
                            {'label': 'Monday', 'value': 'Monday'},
                            {'label': 'Tuesday', 'value': 'Tuesday'},
                            {'label': 'Wednesday', 'value': 'Wednesday'},
                            {'label': 'Thursday', 'value': 'Thursday'},
                            {'label': 'Friday', 'value': 'Friday'},
                            {'label': 'Saturday', 'value': 'Saturday'},
                            {'label': 'Sunday', 'value': 'Sunday'},
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
], style={"minHeight": "100vh"})

# Callbacks
# @app.callback(
#     [Output('theme-container', 'style'),
#      Output('theme-icon', 'className'),
#      Output('theme-store', 'data')],
#     Input('theme-toggle', 'n_clicks'),
#     State('theme-store', 'data'),
#     prevent_initial_call=True
# )
# def toggle_theme(n_clicks, current_theme):
#     if n_clicks:
#         if current_theme == 'light':
#             return (
#                 {'backgroundColor': '#1a1a1a', 'color': '#ffffff', 'minHeight': '100vh'},
#                 'fas fa-sun',
#                 'dark'
#             )
#         else:
#             return (
#                 {'backgroundColor': '#ffffff', 'color': '#000000', 'minHeight': '100vh'},
#                 'fas fa-moon',
#                 'light'
#             )
#     return dash.no_update

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
        conn = sqlite3.connect('happy_hours.db')
        c = conn.cursor()
        c.execute("""INSERT INTO locations 
                    (name, address, lat, lon, description, days, start_time, end_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (name, address, lat, lon, desc, days_str, start_time, end_time))
        conn.commit()
        conn.close()
        # Clear form on success and trigger map refresh
        return (dbc.Alert("Location added successfully!", color="success", duration=3000), 
                "", "", "", [], [900, 1140], refresh_count + 1)
    except Exception as e:
        return (dbc.Alert(f"Error: {str(e)}", color="danger"), 
                name, address, desc, days, time_range, refresh_count)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8050, debug=True)
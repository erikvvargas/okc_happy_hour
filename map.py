# maps.py - Map visualization and sidebar UI

import plotly.express as px
import pandas as pd
from dash import dcc, html
import dash_bootstrap_components as dbc
from geopy.geocoders import Nominatim

# Initialize geocoder
geolocator = Nominatim(user_agent="okc_happy_hours_app")

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

def create_map(df, dark_mode=False):
    """Create the Plotly map with markers"""
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
            zoom=2,
            height=700
        )
        
        # Update marker appearance - brighter color for dark mode visibility
        marker_color = '#ff6b6b' if dark_mode else '#e74c3c'
        fig.update_traces(
            marker=dict(size=14, color=marker_color),
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
            zoom=2,
            height=700
        )
        fig.update_traces(marker=dict(size=0))
    
    # Set map style based on theme - dark mode uses dark map tiles
    map_style = "carto-darkmatter" if dark_mode else "open-street-map"
    
    # Background colors for better integration with theme
    bg_color = '#1a1a1a' if dark_mode else '#ffffff'
    
    fig.update_layout(
        mapbox_style=map_style,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color
    )
    
    return fig

def create_sidebar():
    """Create the sidebar UI for adding locations"""
    return html.Div([
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
                    {'label': 'Monday', 'value': 'Monday'},
                    {'label': 'Tuesday', 'value': 'Tuesday'},
                    {'label': 'Wednesday', 'value': 'Wednesday'},
                    {'label': 'Thursday', 'value': 'Thursday'},
                    {'label': 'Friday', 'value': 'Friday'},
                    {'label': 'Saturday', 'value': 'Saturday'},
                    {'label': 'Sunday', 'value': 'Sunday'},
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

def create_filters():
    """Create the filter dropdowns for day and time"""
    return [
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
    ]
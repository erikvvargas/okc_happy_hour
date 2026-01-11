# admin.py - Admin page for managing locations

import dash
from dash import dcc, html, Input, Output, State, dash_table, ALL
import dash_bootstrap_components as dbc
from db import init_db, get_all_locations, delete_location, update_location, get_location_by_id
from map import geocode_address, time_to_minutes, minutes_to_time

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
app.title = "OKC Happy Hours - Admin"

# Initialize database
init_db()

def create_admin_layout():
    """Create the admin page layout"""
    return html.Div([
        dcc.Store(id='admin-refresh-trigger', data=0),
        dcc.Store(id='edit-location-id', data=None),
        
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("🍺 OKC Happy Hours - Admin", className="text-center my-4"),
                    dbc.Button(
                        [html.I(className="fas fa-home me-2"), "Back to Map"],
                        href="/",
                        color="primary",
                        className="mb-3"
                    )
                ])
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.H3("Manage Locations", className="mb-3"),
                    html.Div(id='locations-table-container')
                ])
            ]),
            
            # Edit Modal
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Edit Location")),
                dbc.ModalBody([
                    dbc.Label("Name:", className="fw-bold"),
                    dbc.Input(id='edit-name', type='text', className="mb-3"),
                    
                    dbc.Label("Address:", className="fw-bold"),
                    dbc.Input(id='edit-address', type='text', className="mb-3"),
                    
                    dbc.Label("Description:", className="fw-bold"),
                    dbc.Textarea(id='edit-description', className="mb-3", rows=3),
                    
                    dbc.Label("Days (comma-separated):", className="fw-bold"),
                    dbc.Input(id='edit-days', type='text', 
                             placeholder='Monday,Tuesday,Wednesday', className="mb-3"),
                    
                    dbc.Label("Start Time (HH:MM):", className="fw-bold"),
                    dbc.Input(id='edit-start-time', type='text', placeholder='15:00', className="mb-3"),
                    
                    dbc.Label("End Time (HH:MM):", className="fw-bold"),
                    dbc.Input(id='edit-end-time', type='text', placeholder='19:00', className="mb-3"),
                    
                    html.Div(id='edit-feedback', className="mt-2")
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancel", id="edit-cancel", color="secondary", className="me-2"),
                    dbc.Button("Save Changes", id="edit-save", color="primary")
                ])
            ], id="edit-modal", is_open=False, size="lg"),
            
        ], fluid=True, className="px-3 px-md-4")
    ], style={"minHeight": "100vh", "backgroundColor": "#f8f9fa"})

app.layout = create_admin_layout()

# Callbacks
@app.callback(
    Output('locations-table-container', 'children'),
    Input('admin-refresh-trigger', 'data')
)
def update_locations_table(refresh):
    df = get_all_locations()
    
    if df.empty:
        return dbc.Alert("No locations found.", color="info")
    
    # Create table rows
    table_rows = []
    for _, row in df.iterrows():
        table_rows.append(
            html.Tr([
                html.Td(row['id']),
                html.Td(row['name']),
                html.Td(row['address']),
                html.Td(row['description'][:50] + '...' if len(str(row['description'])) > 50 else row['description']),
                html.Td(row['days']),
                html.Td(f"{row['start_time']} - {row['end_time']}"),
                html.Td([
                    dbc.Button(
                        html.I(className="fas fa-edit"),
                        id={'type': 'edit-btn', 'index': row['id']},
                        color="warning",
                        size="sm",
                        className="me-2"
                    ),
                    dbc.Button(
                        html.I(className="fas fa-trash"),
                        id={'type': 'delete-btn', 'index': row['id']},
                        color="danger",
                        size="sm"
                    )
                ])
            ])
        )
    
    table = dbc.Table([
        html.Thead(html.Tr([
            html.Th("ID"),
            html.Th("Name"),
            html.Th("Address"),
            html.Th("Description"),
            html.Th("Days"),
            html.Th("Hours"),
            html.Th("Actions")
        ])),
        html.Tbody(table_rows)
    ], bordered=True, hover=True, responsive=True, striped=True)
    
    return table

@app.callback(
    Output('admin-refresh-trigger', 'data'),
    Input({'type': 'delete-btn', 'index': ALL}, 'n_clicks'),
    State('admin-refresh-trigger', 'data'),
    prevent_initial_call=True
)
def delete_location_callback(n_clicks, refresh_count):
    ctx = dash.callback_context
    if not ctx.triggered:
        return refresh_count
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id:
        import json
        button_data = json.loads(button_id)
        location_id = button_data['index']
        
        success, message = delete_location(location_id)
        if success:
            return refresh_count + 1
    
    return refresh_count

@app.callback(
    [Output('edit-modal', 'is_open'),
     Output('edit-name', 'value'),
     Output('edit-address', 'value'),
     Output('edit-description', 'value'),
     Output('edit-days', 'value'),
     Output('edit-start-time', 'value'),
     Output('edit-end-time', 'value'),
     Output('edit-location-id', 'data')],
    [Input({'type': 'edit-btn', 'index': ALL}, 'n_clicks'),
     Input('edit-cancel', 'n_clicks')],
    [State('edit-modal', 'is_open')],
    prevent_initial_call=True
)
def toggle_edit_modal(edit_clicks, cancel_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, "", "", "", "", "", "", None
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if 'edit-cancel' in button_id:
        return False, "", "", "", "", "", "", None
    
    if 'edit-btn' in button_id:
        import json
        button_data = json.loads(button_id)
        location_id = button_data['index']
        
        location = get_location_by_id(location_id)
        if location:
            return (True, location['name'], location['address'], 
                   location['description'], location['days'], 
                   location['start_time'], location['end_time'], location_id)
    
    return False, "", "", "", "", "", "", None

@app.callback(
    [Output('edit-feedback', 'children'),
     Output('edit-modal', 'is_open', allow_duplicate=True),
     Output('admin-refresh-trigger', 'data', allow_duplicate=True)],
    Input('edit-save', 'n_clicks'),
    [State('edit-location-id', 'data'),
     State('edit-name', 'value'),
     State('edit-address', 'value'),
     State('edit-description', 'value'),
     State('edit-days', 'value'),
     State('edit-start-time', 'value'),
     State('edit-end-time', 'value'),
     State('admin-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def save_edited_location(n_clicks, location_id, name, address, desc, days, start_time, end_time, refresh_count):
    if not n_clicks or not location_id:
        return "", True, refresh_count
    
    if not all([name, address, days, start_time, end_time]):
        return dbc.Alert("Please fill in all required fields.", color="warning"), True, refresh_count
    
    # Get existing location to preserve lat/lon
    existing = get_location_by_id(location_id)
    if not existing:
        return dbc.Alert("Location not found.", color="danger"), True, refresh_count
    
    # Check if address changed, re-geocode if needed
    if address != existing['address']:
        lat, lon = geocode_address(address)
        if lat is None or lon is None:
            return dbc.Alert("Could not geocode new address.", color="warning"), True, refresh_count
    else:
        lat, lon = existing['lat'], existing['lon']
    
    success, message = update_location(location_id, name, address, lat, lon, desc, days, start_time, end_time)
    
    if success:
        return dbc.Alert(message, color="success", duration=2000), False, refresh_count + 1
    else:
        return dbc.Alert(message, color="danger"), True, refresh_count

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8051, debug=True)
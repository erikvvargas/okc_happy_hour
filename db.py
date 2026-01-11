# db.py - Database management functions

import sqlite3
import pandas as pd

DB_NAME = 'happy_hours.db'

def init_db():
    """Initialize the database and create tables if they don't exist"""
    conn = sqlite3.connect(DB_NAME)
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

def get_locations(day_filter=None, time_filter=None):
    """Get locations from database with optional filters"""
    conn = sqlite3.connect(DB_NAME)
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

def get_all_locations():
    """Get all locations without filters for admin view"""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM locations ORDER BY id DESC", conn)
    conn.close()
    return df

def add_location(name, address, lat, lon, description, days, start_time, end_time):
    """Add a new location to the database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""INSERT INTO locations 
                    (name, address, lat, lon, description, days, start_time, end_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (name, address, lat, lon, description, days, start_time, end_time))
        conn.commit()
        conn.close()
        return True, "Location added successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def update_location(location_id, name, address, lat, lon, description, days, start_time, end_time):
    """Update an existing location in the database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""UPDATE locations 
                    SET name=?, address=?, lat=?, lon=?, description=?, days=?, start_time=?, end_time=?
                    WHERE id=?""",
                 (name, address, lat, lon, description, days, start_time, end_time, location_id))
        conn.commit()
        conn.close()
        return True, "Location updated successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def delete_location(location_id):
    """Delete a location from the database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM locations WHERE id=?", (location_id,))
        conn.commit()
        conn.close()
        return True, "Location deleted successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_location_by_id(location_id):
    """Get a specific location by ID"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM locations WHERE id=?", (location_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return {
            'id': result[0],
            'name': result[1],
            'address': result[2],
            'lat': result[3],
            'lon': result[4],
            'description': result[5],
            'days': result[6],
            'start_time': result[7],
            'end_time': result[8]
        }
    return None
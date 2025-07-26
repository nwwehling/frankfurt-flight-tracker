from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import requests
import json
import schedule
import time
import threading
from datetime import datetime
from geopy.distance import geodesic
import os
from dotenv import load_dotenv
import sys
sys.path.append('..')
from config import *
from pytz import timezone
# OpenSky OAuth2 credentials
OPENSKY_CLIENT_ID = "nicklasmw-api-client"
OPENSKY_CLIENT_SECRET = "YkQ4Ak015t5dE9Pqed1i93HD0xUZ1oFf"

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database setup
def init_db():
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            icao24 TEXT,
            callsign TEXT,
            aircraft_type TEXT,
            altitude_ft REAL,
            speed_kts REAL,
            latitude REAL,
            longitude REAL,
            distance_to_target REAL,
            timestamp DATETIME,
            is_departing_fra BOOLEAN,
            record_type TEXT DEFAULT 'current',  -- 'lowest_altitude', 'highest_speed', 'closest_distance', 'current'
            origin_airport TEXT,
            destination_airport TEXT
        )
    ''')
    # Add new columns if missing (for migration)
    try:
        cursor.execute('ALTER TABLE flights ADD COLUMN callsign TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE flights ADD COLUMN origin_airport TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE flights ADD COLUMN destination_airport TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE flights ADD COLUMN record_type TEXT DEFAULT "current"')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def is_departing_from_fra(flight_data):
    """Check if the flight is departing from Frankfurt Airport"""
    # This is a simplified check - in a real implementation, you'd use flight plan data
    # For now, we'll check if the aircraft is from Germany (FRA departure)
    if 'origin_country' in flight_data and flight_data['origin_country'] in FRA_DEPARTURE_COUNTRIES:
        return True
    return False

def calculate_distance(lat, lon):
    """Calculate horizontal (great-circle) distance in km from TARGET_COORDS to (lat, lon) using haversine formula"""
    from math import radians, sin, cos, sqrt, atan2
    lat1, lon1 = TARGET_COORDS
    lat2, lon2 = lat, lon
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance

def is_within_criteria(flight_data):
    """Check if flight meets all criteria"""
    if not flight_data:
        return False
    
    # Check altitude range
    altitude = flight_data.get('altitude', 0)
    if altitude < MIN_ALTITUDE_FT or altitude > MAX_ALTITUDE_FT:
        return False
    
    # Check if within radius
    lat = flight_data.get('latitude', 0)
    lon = flight_data.get('longitude', 0)
    distance = calculate_distance(lat, lon)
    if distance > RADIUS_KM:
        return False
    
    # Check if departing from FRA
    if not is_departing_from_fra(flight_data):
        return False
    return True

def get_opensky_token():
    """Get OpenSky access token using OAuth2 client credentials flow"""
    try:
        token_url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': OPENSKY_CLIENT_ID,
            'client_secret': OPENSKY_CLIENT_SECRET
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        print(f"Token request status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token')
        else:
            print(f"Token request failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error getting OpenSky token: {e}")
        return None

def fetch_flight_data():
    """Fetch flight data from OpenSky Network API using OAuth2"""
    try:
        # Get access token
        token = get_opensky_token()
        if not token:
            print("Failed to get OpenSky access token")
            return [], int(time.time())
        
        print("Successfully obtained OpenSky access token")
        
        # Use an expanded bounding box to catch more flights (still under 500km x 500km)
        min_lat, max_lat = 49.8, 50.1
        min_lon, max_lon = 8.4, 8.9
        
        url = "https://opensky-network.org/api/states/all"
        params = {
            'lamin': min_lat,
            'lamax': max_lat,
            'lomin': min_lon,
            'lomax': max_lon
        }
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        print(f"Fetching states for bounding box: ({min_lat}, {max_lat}, {min_lon}, {max_lon})")
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"OpenSky API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"OpenSky API Response: {data}")
            
            if 'states' in data and data['states']:
                print(f"Found {len(data['states'])} states from OpenSky")
                flights = []
                current_time = int(time.time())
                
                for state in data['states']:
                    # OpenSky states format: [icao24, callsign, country, time_position, time_velocity, longitude, latitude, altitude, on_ground, velocity, true_track, vertical_rate, sensors, geo_altitude, squawk, spi, position_source]
                    if len(state) >= 17:
                        # Ensure we have the correct data format
                        icao24 = state[0] if state[0] else ''
                        callsign = state[1] if state[1] else ''
                        country = state[2] if state[2] else ''
                        time_position = state[3] if state[3] else int(time.time())
                        time_velocity = state[4] if state[4] else int(time.time())
                        longitude = state[5] if state[5] is not None else 0
                        latitude = state[6] if state[6] is not None else 0
                        altitude = state[7] if state[7] is not None else 0
                        on_ground = state[8] if state[8] is not None else False
                        velocity = state[9] if state[9] is not None else 0
                        true_track = state[10] if state[10] is not None else 0
                        vertical_rate = state[11] if state[11] is not None else 0
                        sensors = state[12] if state[12] else []
                        geo_altitude = state[13] if state[13] is not None else 0
                        squawk = state[14] if state[14] else ''
                        spi = state[15] if state[15] is not None else False
                        position_source = state[16] if state[16] is not None else 0
                        
                        # Create properly formatted flight data
                        flight_data = [
                            icao24, callsign, country, time_position, time_velocity,
                            longitude, latitude, altitude, on_ground, velocity,
                            true_track, vertical_rate, sensors, geo_altitude,
                            squawk, spi, position_source
                        ]
                        flights.append(flight_data)
                
                print(f"Processed {len(flights)} valid flights from OpenSky")
                return flights, current_time
            else:
                print("No states found in OpenSky response")
                return [], int(time.time())
        else:
            print(f"OpenSky API error: {response.status_code} - {response.text}")
            return [], int(time.time())
            
    except Exception as e:
        print(f"Error fetching flight data from OpenSky: {e}")
        return [], int(time.time())

def fetch_route_info(callsign, icao24=None):
    """Fetch route info (origin/destination) from OpenSky or public API"""
    # Try OpenSky route API (public, limited)
    try:
        if callsign:
            url = f'https://opensky-network.org/api/routes?callsign={callsign.strip()}'
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return data[0].get('estDepartureAirport'), data[0].get('estArrivalAirport')
    except Exception:
        pass
    return None, None

def process_flight_data():
    """Process and store flight data"""
    flights, fetch_time = fetch_flight_data()
    
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    processed_count = 0
    for flight in flights:
        if len(flight) < 17:
            continue
        icao24, callsign, country, time_position, time_velocity, longitude, latitude, altitude, on_ground, velocity, true_track, vertical_rate, sensors, geo_altitude, squawk, spi, position_source = flight
        if not all([latitude, longitude]):
            print(f"DEBUG: Skipping flight - missing lat/lon: lat={latitude}, lon={longitude}")
            continue
        # Use geo_altitude if altitude is None
        if altitude is None:
            altitude = geo_altitude if geo_altitude is not None else 0
        altitude_ft = altitude * 3.28084
        
        flight_data = {
            'icao24': icao24,
            'callsign': callsign.strip() if callsign else None,
            'aircraft_type': 'Unknown',
            'altitude': altitude_ft,
            'speed_kts': velocity or 0,
            'latitude': latitude,
            'longitude': longitude,
            'origin_country': country
        }
        # Use OpenSky's time_position as the timestamp if available, else fallback to fetch_time or now
        # Convert to Berlin timezone (UTC+1/UTC+2)
        berlin_tz = timezone('Europe/Berlin')
        if time_position:
            timestamp_utc = datetime.utcfromtimestamp(time_position)
            timestamp = timestamp_utc.replace(tzinfo=timezone('UTC')).astimezone(berlin_tz).isoformat()
        elif fetch_time:
            timestamp_utc = datetime.utcfromtimestamp(fetch_time)
            timestamp = timestamp_utc.replace(tzinfo=timezone('UTC')).astimezone(berlin_tz).isoformat()
        else:
            timestamp = datetime.now(berlin_tz).isoformat()
        
        if is_within_criteria(flight_data):
            distance = calculate_distance(latitude, longitude)
            origin_airport, destination_airport = fetch_route_info(callsign, icao24)
            
            # Use the already converted Berlin timestamp
            timestamp_berlin = timestamp
            
            # Check for existing record for this icao24 today
            cursor.execute('''
                SELECT id, distance_to_target, altitude_ft, speed_kts FROM flights
                WHERE icao24 = ? AND DATE(timestamp) = DATE('now', 'localtime')
            ''', (icao24,))
            existing = cursor.fetchone()
            if existing:
                existing_id, existing_dist, existing_alt, existing_speed = existing
                update = False
                # Priority: lower distance, then lower altitude, then higher speed
                if distance < existing_dist:
                    update = True
                elif distance == existing_dist:
                    if altitude_ft < existing_alt:
                        update = True
                    elif altitude_ft == existing_alt:
                        if velocity > existing_speed:
                            update = True
                if update:
                    cursor.execute('''
                        UPDATE flights SET callsign=?, aircraft_type=?, altitude_ft=?, speed_kts=?, latitude=?, longitude=?, distance_to_target=?, timestamp=?, is_departing_fra=?, origin_airport=?, destination_airport=?
                        WHERE id=?
                    ''', (
                        callsign, flight_data['aircraft_type'], altitude_ft, velocity, latitude, longitude, distance, timestamp_berlin, True, origin_airport, destination_airport, existing_id
                    ))
                    processed_count += 1
            else:
                cursor.execute('''
                    INSERT INTO flights 
                    (icao24, callsign, aircraft_type, altitude_ft, speed_kts, latitude, longitude, 
                     distance_to_target, timestamp, is_departing_fra, origin_airport, destination_airport)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    icao24, callsign, flight_data['aircraft_type'], altitude_ft, 
                    velocity, latitude, longitude, distance,
                    timestamp_berlin, True, origin_airport, destination_airport
                ))
                processed_count += 1
    
    conn.commit()
    conn.close()
    print(f"Processed {processed_count} flights at {datetime.now()}")

def start_data_collection():
    """Start the data collection scheduler"""
    schedule.every(DATA_COLLECTION_INTERVAL).seconds.do(process_flight_data)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

@app.route('/api/flights', methods=['GET'])
def get_flights():
    """Get all recorded flights"""
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM flights 
        ORDER BY timestamp DESC 
        LIMIT 100
    ''')
    
    flights = []
    for row in cursor.fetchall():
        flights.append({
            'id': row[0],
            'icao24': row[1],
            'aircraft_type': row[2],
            'altitude_ft': row[3],
            'speed_kts': row[4],
            'latitude': row[5],
            'longitude': row[6],
            'distance_to_target': row[7],
            'timestamp': row[8],
            'is_departing_fra': row[9],
            'closest_point': row[10],
            'callsign': row[11],
            'origin_airport': row[12],
            'destination_airport': row[13],
            'record_type': row[14] if len(row) > 14 else 'current'
        })
    
    conn.close()
    return jsonify(flights)

@app.route('/api/flights/closest', methods=['GET'])
def get_closest_flights():
    """Get only the closest point for each flight"""
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM flights 
        WHERE closest_point = TRUE
        ORDER BY timestamp DESC 
        LIMIT 50
    ''')
    
    flights = []
    for row in cursor.fetchall():
        flights.append({
            'id': row[0],
            'icao24': row[1],
            'aircraft_type': row[2],
            'altitude_ft': row[3],
            'speed_kts': row[4],
            'latitude': row[5],
            'longitude': row[6],
            'distance_to_target': row[7],
            'timestamp': row[8],
            'is_departing_fra': row[9],
            'closest_point': row[10],
            'callsign': row[11],
            'origin_airport': row[12],
            'destination_airport': row[13]
        })
    
    conn.close()
    return jsonify(flights)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about recorded flights"""
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Total flights recorded
    cursor.execute('SELECT COUNT(*) FROM flights')
    total_flights = cursor.fetchone()[0]
    
    # Flights today
    cursor.execute('SELECT COUNT(*) FROM flights WHERE DATE(timestamp) = DATE("now")')
    flights_today = cursor.fetchone()[0]
    
    # Average altitude
    cursor.execute('SELECT AVG(altitude_ft) FROM flights')
    avg_altitude = cursor.fetchone()[0] or 0
    
    # Average speed
    cursor.execute('SELECT AVG(speed_kts) FROM flights')
    avg_speed = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return jsonify({
        'total_flights': total_flights,
        'flights_today': flights_today,
        'average_altitude_ft': round(avg_altitude, 2),
        'average_speed_kts': round(avg_speed, 2)
    })

@app.route('/api/flights/closest-aircraft', methods=['GET'])
def get_closest_aircraft():
    """Get the aircraft that came closest to target coordinates"""
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM flights 
        WHERE distance_to_target IS NOT NULL 
        ORDER BY distance_to_target ASC 
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        flight = {
            'id': row[0],
            'icao24': row[1],
            'aircraft_type': row[2],
            'altitude_ft': row[3],
            'speed_kts': row[4],
            'latitude': row[5],
            'longitude': row[6],
            'distance_to_target': row[7],
            'timestamp': row[8],
            'is_departing_fra': row[9],
            'closest_point': row[10],
            'callsign': row[11],
            'origin_airport': row[12],
            'destination_airport': row[13]
        }
        return jsonify(flight)
    else:
        return jsonify({'error': 'No flights recorded yet'}), 404

@app.route('/api/flights/lowest-aircraft', methods=['GET'])
def get_lowest_aircraft():
    """Get the aircraft that flew at the lowest altitude"""
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM flights 
        WHERE altitude_ft IS NOT NULL 
        ORDER BY altitude_ft ASC 
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        flight = {
            'id': row[0],
            'icao24': row[1],
            'aircraft_type': row[2],
            'altitude_ft': row[3],
            'speed_kts': row[4],
            'latitude': row[5],
            'longitude': row[6],
            'distance_to_target': row[7],
            'timestamp': row[8],
            'is_departing_fra': row[9],
            'closest_point': row[10],
            'callsign': row[11],
            'origin_airport': row[12],
            'destination_airport': row[13]
        }
        return jsonify(flight)
    else:
        return jsonify({'error': 'No flights recorded yet'}), 404

@app.route('/api/flights/fastest-aircraft', methods=['GET'])
def get_fastest_aircraft():
    """Get the aircraft that flew at the highest speed"""
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM flights 
        WHERE speed_kts IS NOT NULL 
        ORDER BY speed_kts DESC 
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        flight = {
            'id': row[0],
            'icao24': row[1],
            'aircraft_type': row[2],
            'altitude_ft': row[3],
            'speed_kts': row[4],
            'latitude': row[5],
            'longitude': row[6],
            'distance_to_target': row[7],
            'timestamp': row[8],
            'is_departing_fra': row[9],
            'closest_point': row[10],
            'callsign': row[11],
            'origin_airport': row[12],
            'destination_airport': row[13]
        }
        return jsonify(flight)
    else:
        return jsonify({'error': 'No flights recorded yet'}), 404

@app.route('/api/flights/filtered', methods=['GET'])
def get_filtered_flights():
    """Get flights with server-side filtering"""
    # Get filter parameters from query string
    altitude_min = request.args.get('altitude_min', type=float)
    altitude_max = request.args.get('altitude_max', type=float)
    distance_min = request.args.get('distance_min', type=float)
    distance_max = request.args.get('distance_max', type=float)
    speed_min = request.args.get('speed_min', type=float)
    speed_max = request.args.get('speed_max', type=float)
    tracking_number = request.args.get('tracking_number', type=str)
    
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Build the WHERE clause dynamically
    where_conditions = []
    params = []
    
    if altitude_min is not None:
        where_conditions.append('altitude_ft >= ?')
        params.append(altitude_min)
    
    if altitude_max is not None:
        where_conditions.append('altitude_ft <= ?')
        params.append(altitude_max)
    
    if distance_min is not None:
        where_conditions.append('distance_to_target >= ?')
        params.append(distance_min)
    
    if distance_max is not None:
        where_conditions.append('distance_to_target <= ?')
        params.append(distance_max)
    
    if speed_min is not None:
        where_conditions.append('speed_kts >= ?')
        params.append(speed_min)
    
    if speed_max is not None:
        where_conditions.append('speed_kts <= ?')
        params.append(speed_max)
    
    if tracking_number:
        where_conditions.append('icao24 LIKE ?')
        params.append(f'%{tracking_number}%')
    
    # Build the query
    query = 'SELECT * FROM flights'
    if where_conditions:
        query += ' WHERE ' + ' AND '.join(where_conditions)
    query += ' ORDER BY timestamp DESC LIMIT 200'
    
    cursor.execute(query, params)
    
    flights = []
    for row in cursor.fetchall():
        flights.append({
            'id': row[0],
            'icao24': row[1],
            'aircraft_type': row[2],
            'altitude_ft': row[3],
            'speed_kts': row[4],
            'latitude': row[5],
            'longitude': row[6],
            'distance_to_target': row[7],
            'timestamp': row[8],
            'is_departing_fra': row[9],
            'closest_point': row[10],
            'callsign': row[11],
            'origin_airport': row[12],
            'destination_airport': row[13]
        })
    
    conn.close()
    return jsonify(flights)

@app.route('/api/trigger-data-collection', methods=['POST'])
def trigger_data_collection():
    """Manually trigger data collection for testing"""
    try:
        process_flight_data()
        return jsonify({'message': 'Data collection triggered successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/fix-timezone', methods=['POST'])
def fix_timezone():
    """Fix existing flight timestamps by adding 2 hours (UTC to local time)"""
    try:
        # Use absolute path for database
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all flights that need timezone fixing
        cursor.execute('SELECT id, timestamp FROM flights')
        flights = cursor.fetchall()
        
        updated_count = 0
        berlin_tz = timezone('Europe/Berlin')
        
        for flight_id, timestamp_str in flights:
            try:
                # Parse the existing timestamp
                if timestamp_str:
                    # Try parsing as ISO format
                    if 'T' in timestamp_str:
                        # Remove timezone info if present for parsing
                        clean_timestamp = timestamp_str.split('+')[0].split('-')[0:3]
                        clean_timestamp = '-'.join(clean_timestamp[0:3])
                        if 'T' in clean_timestamp:
                            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                # Assume it's UTC and convert to Berlin time
                                dt_utc = dt.replace(tzinfo=timezone('UTC'))
                                dt_berlin = dt_utc.astimezone(berlin_tz)
                            else:
                                # Already has timezone info, convert to Berlin
                                dt_berlin = dt.astimezone(berlin_tz)
                        else:
                            # Old format, assume UTC and add 2 hours
                            dt = datetime.fromisoformat(timestamp_str)
                            dt_utc = dt.replace(tzinfo=timezone('UTC'))
                            dt_berlin = dt_utc.astimezone(berlin_tz)
                    else:
                        # Old format, assume UTC and add 2 hours
                        dt = datetime.fromisoformat(timestamp_str)
                        dt_utc = dt.replace(tzinfo=timezone('UTC'))
                        dt_berlin = dt_utc.astimezone(berlin_tz)
                    
                    # Update the flight with the corrected timestamp
                    cursor.execute('UPDATE flights SET timestamp = ? WHERE id = ?', 
                                 (dt_berlin.isoformat(), flight_id))
                    updated_count += 1
            except Exception as e:
                print(f"Error processing flight {flight_id}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': f'Fixed timezone for {updated_count} flights'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Start data collection in a separate thread
    data_thread = threading.Thread(target=start_data_collection, daemon=True)
    data_thread.start()
    
    # Run the Flask app
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT) 
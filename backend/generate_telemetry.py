import sqlite3
import random
import datetime

# Connect to SQLite database (or create it)
db_path = "telemetry.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create table for sensor telemetry
cursor.execute('''
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME,
    equipment_id TEXT,
    temperature REAL,
    pressure REAL,
    vibration REAL
)
''')

# Clear existing data just in case
cursor.execute('DELETE FROM sensor_data')

# Generate data
data = []
start_time = datetime.datetime.now() - datetime.timedelta(days=7)
equipment = "Pump_B"

print("Generating synthetic industrial telemetry data...")

# Generate 1000 normal readings
for i in range(1000):
    timestamp = start_time + datetime.timedelta(minutes=i*15)
    
    # Normal operating ranges
    # Temperature: 70-75 C
    # Pressure: 100-110 PSI
    # Vibration: 0.02-0.05 mm/s
    temp = random.uniform(70.0, 75.0)
    pressure = random.uniform(100.0, 110.0)
    vibration = random.uniform(0.02, 0.05)
    
    # Inject anomalies for Isolation Forest to catch (roughly 1% of data)
    if i in [150, 420, 780, 890, 950]:
        print(f"Injecting anomaly at index {i}...")
        # Extreme temperature spike
        if i == 150: temp = 95.5 
        # Massive pressure drop
        if i == 420: pressure = 45.2 
        # High vibration and high temp (bearing failure simulation)
        if i == 780: 
            vibration = 0.85
            temp = 89.0
        # Complete sensor failure (zeros)
        if i == 890:
            temp = 0
            pressure = 0
            vibration = 0
        # Pressure spike
        if i == 950: pressure = 180.5

    data.append((
        timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        equipment,
        round(temp, 2),
        round(pressure, 2),
        round(vibration, 3)
    ))

# Insert into database
cursor.executemany('''
INSERT INTO sensor_data (timestamp, equipment_id, temperature, pressure, vibration)
VALUES (?, ?, ?, ?, ?)
''', data)

conn.commit()
conn.close()

print(f"Successfully populated {db_path} with 1000 records (including 5 critical anomalies).")
print("Ready for Isolation Forest ML analysis!")

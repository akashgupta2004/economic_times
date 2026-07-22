import sqlite3
import random
import os
from datetime import datetime, timedelta

def generate_test_dataset():
    # Ensure the sqlite_uploads directory exists so we can directly place the DB there
    uploads_dir = os.path.join(os.path.dirname(__file__), "sqlite_uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    db_path = os.path.join(uploads_dir, "test_dataset.sqlite")
    
    # Remove old test DB if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create a realistic machine telemetry table
    cursor.execute("""
        CREATE TABLE sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            machine_id TEXT,
            temperature REAL,
            vibration REAL,
            pressure REAL
        )
    """)
    
    print("Generating 1000 normal data points...")
    start_time = datetime.now() - timedelta(days=10)
    
    # Generate 1000 normal data points
    for i in range(1000):
        ts = start_time + timedelta(minutes=i*15)
        
        # Normal operating ranges
        temp = round(random.uniform(60.0, 75.0), 2)
        vib = round(random.uniform(1.0, 2.5), 3)
        press = round(random.uniform(100.0, 110.0), 1)
        
        cursor.execute(
            "INSERT INTO sensor_data (timestamp, machine_id, temperature, vibration, pressure) VALUES (?, ?, ?, ?, ?)",
            (ts.strftime("%Y-%m-%d %H:%M:%S"), "EXTRUDER-01", temp, vib, press)
        )
        
    print("Injecting 15 anomalies into the dataset...")
    # Inject 15 anomalous data points scattered throughout
    for i in range(15):
        # Pick a random time in the last 10 days
        random_minutes = random.randint(0, 1000 * 15)
        ts = start_time + timedelta(minutes=random_minutes)
        
        # Anomalous ranges (spikes)
        temp = round(random.uniform(95.0, 120.0), 2) # Way too hot
        vib = round(random.uniform(5.0, 9.0), 3)     # Extreme vibration
        press = round(random.uniform(140.0, 160.0), 1) # High pressure
        
        cursor.execute(
            "INSERT INTO sensor_data (timestamp, machine_id, temperature, vibration, pressure) VALUES (?, ?, ?, ?, ?)",
            (ts.strftime("%Y-%m-%d %H:%M:%S"), "EXTRUDER-01", temp, vib, press)
        )
        
    conn.commit()
    conn.close()
    
    print(f"Successfully created {db_path} with 1015 rows!")
    print("You can now ask the Copilot to analyze 'test_dataset.sqlite' and detect anomalies.")

if __name__ == "__main__":
    generate_test_dataset()

import sqlite3
import datetime
import random
import os

DB_PATH = "machine_logs.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create the time-series table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            machine_id TEXT NOT NULL,
            sensor_type TEXT,
            value REAL,
            status_code TEXT
        )
    """)
    # Create an index on timestamp and machine_id for faster time-series queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_machine_time ON telemetry (machine_id, timestamp)")
    conn.commit()
    conn.close()

def insert_log(machine_id: str, sensor_type: str, value: float, status_code: str = "OK", timestamp: datetime.datetime = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if timestamp is None:
        timestamp = datetime.datetime.now()
    cursor.execute(
        "INSERT INTO telemetry (timestamp, machine_id, sensor_type, value, status_code) VALUES (?, ?, ?, ?, ?)",
        (timestamp.strftime("%Y-%m-%d %H:%M:%S"), machine_id, sensor_type, value, status_code)
    )
    conn.commit()
    conn.close()

def query_logs(machine_id: str, hours: int = 24, error_only: bool = False) -> list[dict]:
    """
    Queries the TSDB for a specific machine over the last N hours.
    Returns a list of dictionaries.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    time_threshold = (datetime.datetime.now() - datetime.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    
    query = "SELECT timestamp, machine_id, sensor_type, value, status_code FROM telemetry WHERE UPPER(machine_id) = UPPER(?) AND timestamp >= ?"
    params = [machine_id, time_threshold]
    
    if error_only:
        query += " AND status_code != 'OK'"
        
    query += " ORDER BY timestamp DESC LIMIT 100" # Limit to avoid overflowing LLM context
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "timestamp": row[0],
            "machine_id": row[1],
            "sensor_type": row[2],
            "value": row[3],
            "status_code": row[4]
        })
    return result

def get_machine_sensors(machine_id: str) -> list[str]:
    """
    Queries the TSDB to find all unique sensor types installed on a specific machine.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT sensor_type FROM telemetry WHERE UPPER(machine_id) = UPPER(?)", (machine_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return []
    return [row[0] for row in rows]

def detect_anomalies_isolation_tree(machine_id: str, sensor_type: str, hours: int = 24) -> list[dict]:
    """
    Pulls raw numeric telemetry data for a specific sensor and runs an Isolation Forest 
    to detect mathematical anomalies (outliers).
    """
    import pandas as pd
    from sklearn.ensemble import IsolationForest

    # 1. Fetch raw data
    logs = query_logs(machine_id, hours=hours, error_only=False)
    
    # Filter for the specific sensor type and sort chronologically
    sensor_logs = [log for log in logs if log['sensor_type'].lower() == sensor_type.lower()]
    sensor_logs.sort(key=lambda x: x['timestamp'])
    
    if len(sensor_logs) < 10:
        return [{"error": f"Not enough data points ({len(sensor_logs)}) to train Isolation Forest. Need at least 10."}]
        
    # 2. Prepare dataframe
    df = pd.DataFrame(sensor_logs)
    X = df[['value']].values
    
    # 3. Train Isolation Forest (contamination=0.1 means we expect roughly 10% anomalies)
    model = IsolationForest(contamination=0.1, random_state=42)
    predictions = model.fit_predict(X)
    
    # 4. Extract the anomalous records (predict returns -1 for anomalies, 1 for normal)
    anomalies = []
    for i, pred in enumerate(predictions):
        if pred == -1:
            anomalies.append(sensor_logs[i])
            
    return anomalies

def generate_mock_data():
    """Generates some mock sensor data and errors for testing the Agent."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM telemetry")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return # Data already exists
    conn.close()
    
    print("Generating mock machine telemetry data...")
    now = datetime.datetime.now()
    
    # Generate 50 hours of normal data for Pump_B
    for i in range(50, 0, -1):
        ts = now - datetime.timedelta(hours=i)
        insert_log("Pump_B", "Vibration", round(random.uniform(1.2, 1.8), 2), "OK", ts)
        insert_log("Pump_B", "Temperature", round(random.uniform(60, 65), 1), "OK", ts)
        insert_log("COMPRESSOR-B", "Pressure", round(random.uniform(100, 105), 1), "OK", ts)
        
    # Generate a recent error for Pump_B (High Vibration / Grinding)
    error_ts = now - datetime.timedelta(minutes=15)
    insert_log("Pump_B", "Vibration", 5.8, "ERR_HIGH_VIBRATION", error_ts)
    insert_log("Pump_B", "Temperature", 95.5, "ERR_HIGH_TEMP", error_ts)
    
    # Generate a recent error for COMPRESSOR-B
    error_ts2 = now - datetime.timedelta(minutes=5)
    insert_log("COMPRESSOR-B", "Pressure", 30.0, "ERR_PRESSURE_DROP", error_ts2)
    
    print("Mock data generated successfully.")

# Auto-initialize and populate when imported
init_db()
generate_mock_data()

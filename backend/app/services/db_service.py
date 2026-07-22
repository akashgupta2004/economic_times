import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "jobs.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert some initial dummy data if empty so the dashboard isn't completely blank
    cursor.execute("SELECT COUNT(*) FROM jobs")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO jobs (id, filename, status, timestamp) VALUES (?, ?, ?, ?)", 
                       ("JOB-INITIAL-1", "System_Init.log", "Completed", datetime.now().isoformat()))
        
    conn.commit()
    conn.close()

def get_recent_jobs(limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, status, timestamp FROM jobs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {"id": row[0], "filename": row[1], "status": row[2], "timestamp": row[3]}
        for row in rows
    ]

def add_job(job_id: str, filename: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (id, filename, status, timestamp) VALUES (?, ?, ?, ?)",
        (job_id, filename, status, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

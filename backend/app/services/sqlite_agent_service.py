import os
import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest

SQLITE_UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sqlite_uploads")

def list_uploaded_sqlite_dbs() -> list[str]:
    """Returns a list of available SQLite databases that the user has uploaded."""
    if not os.path.exists(SQLITE_UPLOADS_DIR):
        return []
    return [f for f in os.listdir(SQLITE_UPLOADS_DIR) if f.endswith((".sqlite", ".db"))]

def get_database_schema(db_filename: str) -> str:
    """Uses LangChain SQLDatabase to extract a highly readable schema (DDL + sample rows)."""
    db_path = os.path.join(SQLITE_UPLOADS_DIR, db_filename)
    if not os.path.exists(db_path):
        return f"Error: Database {db_filename} not found."
    
    try:
        from langchain_community.utilities import SQLDatabase
        # Create absolute URI for SQLAlchemy
        abs_path = os.path.abspath(db_path)
        uri = f"sqlite:///{abs_path}"
        db = SQLDatabase.from_uri(uri, sample_rows_in_table_info=3)
        return db.get_table_info()
    except Exception as e:
        return f"Error extracting schema: {str(e)}"

def query_database(db_filename: str, query: str) -> dict:
    """Executes a read-only SELECT query on the specified database and returns the results."""
    db_path = os.path.join(SQLITE_UPLOADS_DIR, db_filename)
    if not os.path.exists(db_path):
        return {"error": f"Database {db_filename} not found."}
        
    query = query.strip()
    if not query.upper().startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed for safety."}
        
    try:
        conn = sqlite3.connect(db_path)
        # Using pandas for safe and easy result formatting
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Limit to 10 rows to prevent LLM context overflow (Groq free tier has 6000 TPM limit)
        if len(df) > 10:
            df = df.head(10)
            return {"warning": f"Results truncated to 10 rows out of actual total", "results": df.astype(str).to_dict('records')}
        return {"results": df.astype(str).to_dict('records')}
    except Exception as e:
        return {"error": str(e)}

def run_isolation_forest_on_database(db_filename: str, table_name: str, column_name: str) -> dict:
    """
    Runs an Isolation Forest on the specified numeric column to detect mathematical anomalies.
    Returns the rows that were classified as anomalies.
    """
    db_path = os.path.join(SQLITE_UPLOADS_DIR, db_filename)
    if not os.path.exists(db_path):
        return {"error": f"Database {db_filename} not found."}
        
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if column_name not in df.columns:
            return {"error": f"Column {column_name} not found in table {table_name}."}
            
        if len(df) < 10:
            return {"error": f"Not enough data points ({len(df)}) to train Isolation Forest. Need at least 10."}
            
        df_numeric = pd.to_numeric(df[column_name], errors='coerce')
        if df_numeric.isna().all():
            return {"error": f"Column {column_name} does not contain valid numeric data."}
            
        # Drop rows with NaN in the target column
        df = df.dropna(subset=[column_name])
        X = df[[column_name]].values
        
        model = IsolationForest(contamination=0.1, random_state=42)
        predictions = model.fit_predict(X)
        
        df['is_anomaly'] = predictions
        anomalies_df = df[df['is_anomaly'] == -1].drop(columns=['is_anomaly'])
        anomalies = anomalies_df.astype(str).to_dict('records')
        
        if len(anomalies) > 5:
            return {"warning": f"Detected {len(anomalies)} anomalies. Showing first 5 to conserve context length.", "anomalies": anomalies[:5]}
            
        return {"anomalies": anomalies}
    except Exception as e:
        return {"error": str(e)}

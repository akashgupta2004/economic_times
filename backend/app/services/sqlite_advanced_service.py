import sqlite3
import os
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM

SQLITE_UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sqlite_uploads")

def list_uploaded_sqlite_dbs() -> list[str]:
    if not os.path.exists(SQLITE_UPLOADS_DIR):
        return []
    return [f for f in os.listdir(SQLITE_UPLOADS_DIR) if f.endswith((".sqlite", ".db"))]

def get_schema_summary(db_filename: str) -> dict:
    db_path = os.path.join(SQLITE_UPLOADS_DIR, db_filename)
    if not os.path.exists(db_path):
        return {"error": f"Database {db_filename} not found."}
    
    schema = {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            schema[table_name] = [{"name": col[1], "type": col[2]} for col in columns]
            
        conn.close()
        return schema
    except Exception as e:
        return {"error": str(e)}

def query_database(db_filename: str, query: str) -> dict:
    db_path = os.path.join(SQLITE_UPLOADS_DIR, db_filename)
    if not os.path.exists(db_path):
        return {"error": f"Database {db_filename} not found."}
        
    query = query.strip()
    if not query.upper().startswith("SELECT"):
        return {"error": "Use modify_database tool for non-SELECT queries."}
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        conn.close()
        
        results = [dict(zip(column_names, row)) for row in rows]
        if len(results) > 100:
            return {"warning": f"Truncated to 100 out of {len(results)} rows", "results": results[:100]}
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

def modify_database(db_filename: str, query: str) -> dict:
    db_path = os.path.join(SQLITE_UPLOADS_DIR, db_filename)
    if not os.path.exists(db_path):
        return {"error": f"Database {db_filename} not found."}
        
    query = query.strip()
    if query.upper().startswith("SELECT"):
        return {"error": "Use query_database tool for SELECT queries."}
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        return {"success": True, "affected_rows": affected_rows, "message": "Modification executed successfully."}
    except Exception as e:
        return {"error": str(e)}

def run_advanced_anomaly_detection(db_filename: str, table_name: str, column_name: str, algorithm: str = "isolation_forest") -> dict:
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
            return {"error": f"Not enough data ({len(df)} rows). Need at least 10."}
            
        df_numeric = pd.to_numeric(df[column_name], errors='coerce')
        if df_numeric.isna().all():
            return {"error": f"Column {column_name} is not numeric."}
            
        # Keep track of original index for dropping NaNs
        df_clean = df.dropna(subset=[column_name]).copy()
        X = df_clean[[column_name]].values
        
        if algorithm == "isolation_forest":
            model = IsolationForest(contamination=0.1, random_state=42)
            preds = model.fit_predict(X)
        elif algorithm == "lof":
            model = LocalOutlierFactor(contamination=0.1)
            preds = model.fit_predict(X)
        elif algorithm == "svm":
            model = OneClassSVM(nu=0.1)
            preds = model.fit_predict(X)
        else:
            return {"error": f"Unknown algorithm: {algorithm}. Use isolation_forest, lof, or svm."}
            
        df_clean['is_anomaly'] = preds
        anomalies_df = df_clean[df_clean['is_anomaly'] == -1].drop(columns=['is_anomaly'])
        
        anomalies = anomalies_df.astype(str).to_dict('records')
        if len(anomalies) > 50:
            return {"warning": f"Detected {len(anomalies)} anomalies. Showing first 50.", "anomalies": anomalies[:50], "algorithm_used": algorithm}
            
        return {"anomalies": anomalies, "algorithm_used": algorithm}
    except Exception as e:
        return {"error": str(e)}

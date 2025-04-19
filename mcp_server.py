from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import os

# Initialize FastAPI app
app = FastAPI()

# Path to the SQLite database
db_path = os.path.join(os.getcwd(), "medicine.db")

# Define Pydantic models for request bodies
class QueryRequest(BaseModel):
    query: str

@app.post("/mcp/read_query")
def read_query(request: QueryRequest):
    """Endpoint to execute SELECT queries on the SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(request.query)
        results = cursor.fetchall()
        conn.close()
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/mcp/write_query")
def write_query(request: QueryRequest):
    """Endpoint to execute INSERT, UPDATE, or DELETE queries on the SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(request.query)
        conn.commit()
        conn.close()
        return {"message": "Query executed successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

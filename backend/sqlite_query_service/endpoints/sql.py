import urllib.parse
from fastapi import APIRouter, HTTPException
import sqlite3
import requests
import uuid
import os

router = APIRouter()


@router.get("/sql")
async def execute_sql(record_id: str, query: str):
    db_file_url = None
    conn = None
    try:
        response = requests.get(
            f"http://127.0.0.1:8090/api/collections/tests/records/{record_id}")
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error retrieving record with ID {record_id}: {response.text}"
            )
        record = response.json()
        db_file_url = f"http://127.0.0.1:8090/api/files/tests/{record_id}/{record.get('db_file')}"

        file_name = str(uuid.uuid4())

        # Download the database file
        urllib.request.urlretrieve(db_file_url, file_name)

        # Connect to the database
        conn = sqlite3.connect(file_name)

        # Execute the query
        cursor = conn.cursor()
        cursor.execute(query)
        result_data = cursor.fetchall()

        # Get the column names
        column_names = [desc[0] for desc in cursor.description]

        # Prepare the result with column names
        result = [
            {column: value for column, value in zip(column_names, row)}
            for row in result_data
        ]

        # Close the connection and remove the temporary database file
        conn.close()
        os.remove(file_name)

        return {"columns": column_names, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        if conn is not None:
            conn.close()
        if os.path.exists(file_name):
            os.remove(file_name)
        raise HTTPException(status_code=500, detail=str(e))

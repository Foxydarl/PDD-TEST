from sqlalchemy import create_engine, MetaData
import urllib.parse
from fastapi import APIRouter, HTTPException
import sqlite3
import requests
import uuid
import os
import json
import re

router = APIRouter()


def get_schema_info(mysql_url):
    engine = create_engine(mysql_url)
    metadata = MetaData()
    metadata.reflect(bind=engine)

    # Get table names
    table_names = [table.name for table in metadata.sorted_tables]

    # Get field names for each table
    fields = {}
    for table in metadata.sorted_tables:
        fields[table.name] = [column.name for column in table.columns]

    # Get relationships between tables
    relationships = []
    for foreign_key in metadata.sorted_foreign_keys:
        relationships.append((foreign_key.column.table.name,
                              foreign_key.column.name,
                              foreign_key.referred_table.name,
                              foreign_key.referred_column.name))

    # Return as a JSON string
    schema_info = {
        'tables': table_names,
        'fields': fields,
        'relationships': relationships
    }
    return json.dumps(schema_info)


@router.get("/schema")
async def get_schema(record_id: str):
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

        # Get the schema as a single line
        schema_query = """
            SELECT GROUP_CONCAT(tbl.sql, '\n') AS schema
            FROM sqlite_master AS tbl
            WHERE type='table' AND name NOT LIKE 'sqlite_%';
        """
        cursor = conn.cursor()
        cursor.execute(schema_query)
        pattern = re.compile(r'\s+[A-Z]+\(?[0-9]*\)?\s+')
        schema_line = cursor.fetchone()[0]
        final = pattern.sub(' ', schema_line).replace(" NOT NULL,", "")

        # Close the connection and remove the temporary database file
        conn.close()
        os.remove(file_name)

        return {"schema": final}
    except HTTPException:
        raise
    except Exception as e:
        if conn is not None:
            conn.close()
        if os.path.exists(file_name):
            os.remove(file_name)
        raise HTTPException(status_code=500, detail=str(e))

"""
Utility script to create the initial MySQL database.
Run once before applying Django migrations.

Usage:
    python mydb.py
"""

import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

dataBase = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    passwd=os.getenv("DB_PASSWORD", ""),
)

cursorObject = dataBase.cursor()
db_name = os.getenv("DB_NAME", "elderco")
cursorObject.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
print(f"Database '{db_name}' is ready.")

import mysql.connector
import os

# Configuration
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'onurkocaman5353')
DB_NAME = 'motor_db'
SQL_FILE = 'son.sql'

def execute_sql_file(cursor, filename):
    with open(filename, 'r', encoding='utf-8') as f:
        sql_file = f.read()
    
    # Split queries by semicolon and filter out empty strings
    # This is a naive split, assuming new commands start after a semicolon and newline interactions
    # standard dumps usually format like INSERT ...;\n
    commands = sql_file.split(';')
    
    for command in commands:
        if command.strip():
            try:
                cursor.execute(command)
            except mysql.connector.Error as err:
                 # Ignore empty query errors or warn
                print(f"Skipping command due to error: {err}")


print(f"Connecting to {MYSQL_HOST}...")

try:
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )
    print("Connected.")
    
    cur = conn.cursor()
    
    print(f"Creating database {DB_NAME} if not exists...")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE {DB_NAME}")
    
    print(f"Importing {SQL_FILE}...")
    execute_sql_file(cur, SQL_FILE)
    
    conn.commit()
    print("Database initialized successfully!")
    
    cur.close()
    conn.close()

except mysql.connector.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"Error: {e}")

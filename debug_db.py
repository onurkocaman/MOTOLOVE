import mysql.connector
import os

# Configuration from app.py
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'onurkocaman5353')
MYSQL_DB = os.environ.get('MYSQL_DB', 'motor_db')

print(f"Connecting to {MYSQL_HOST} as {MYSQL_USER}...")

try:
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    print("Connection successful!")
    
    # Use dictionary=True for similarity with app usage
    cur = conn.cursor(dictionary=True)
    
    # Check users table
    print("Checking 'users' table schema...")
    cur.execute("DESCRIBE users")
    # mysql-connector returns dicts like {'Field': 'id', ...}
    columns = [row['Field'] for row in cur.fetchall()]
    print(f"Columns in 'users': {columns}")
    
    if 'role' in columns:
        print("'role' column exists.")
    else:
        print("'role' column is MISSING!")

    # Try a dummy select
    cur.execute("SELECT count(*) as cnt FROM users")
    count = cur.fetchone()['cnt']
    print(f"User count: {count}")

    conn.close()

except mysql.connector.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"Error: {e}")

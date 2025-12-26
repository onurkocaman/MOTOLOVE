import mysql.connector
import os
from werkzeug.security import generate_password_hash

# Configuration
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'onurkocaman5353')
MYSQL_DB = os.environ.get('MYSQL_DB', 'motor_db')

USER_NAME = "Onur Kocaman"
USER_EMAIL = "onurkocaman@email.com"
USER_PASSWORD = "onurkocaman5353"
USER_ROLE = "admin" # Giving admin access as requested implicity

print(f"Connecting to database...")

try:
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cur = conn.cursor()
    
    # Check if user exists
    cur.execute("SELECT id FROM users WHERE email = %s", (USER_EMAIL,))
    existing = cur.fetchone()
    
    password_hash = generate_password_hash(USER_PASSWORD)
    
    if existing:
        print(f"User {USER_EMAIL} already exists. Updating password...")
        cur.execute("UPDATE users SET password_hash = %s, role = %s WHERE email = %s", 
                    (password_hash, USER_ROLE, USER_EMAIL))
    else:
        print(f"Creating new user {USER_EMAIL}...")
        cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)", 
                    (USER_NAME, USER_EMAIL, password_hash, USER_ROLE))
    
    conn.commit()
    print("User account operation successful!")
    
    cur.close()
    conn.close()

except mysql.connector.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"Error: {e}")

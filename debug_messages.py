
import mysql.connector
import json

def debug_db():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='onurkocaman5353',
            database='motor_db'
        )
        cursor = conn.cursor(dictionary=True)

        print("--- CONVERSATIONS ---")
        cursor.execute("SELECT * FROM conversations ORDER BY id DESC LIMIT 5")
        convs = cursor.fetchall()
        for c in convs:
            print(c)

        print("\n--- MESSAGES ---")
        cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 5")
        msgs = cursor.fetchall()
        for m in msgs:
            print(m)
            
        print("\n--- USERS ---")
        cursor.execute("SELECT id, name FROM users LIMIT 10")
        users = cursor.fetchall()
        for u in users:
            print(u)

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    debug_db()

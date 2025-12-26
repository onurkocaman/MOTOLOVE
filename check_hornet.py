
import mysql.connector
import os

def check():
    conn = mysql.connector.connect(
        host=os.environ.get('MYSQL_HOST', 'localhost'),
        user=os.environ.get('MYSQL_USER', 'root'),
        password=os.environ.get('MYSQL_PASSWORD', 'onurkocaman5353'),
        database=os.environ.get('MYSQL_DB', 'motor_db')
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title, image_url FROM motorcycles WHERE title LIKE '%Hornet%'")
    rows = cursor.fetchall()
    print(rows)
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check()

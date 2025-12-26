
import mysql.connector
import os
from flask import Flask

app = Flask(__name__)
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'onurkocaman5353')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'motor_db')

def create_table():
    try:
        conn = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB']
        )
        cursor = conn.cursor()
        
        create_query = """
        CREATE TABLE IF NOT EXISTS comments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            motorcycle_id INT NOT NULL,
            user_id INT NOT NULL,
            content TEXT NOT NULL,
            rating INT DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (motorcycle_id) REFERENCES motorcycles(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
        
        cursor.execute(create_query)
        conn.commit()
        print("Comments table created successfully (or already exists).")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error creating table: {e}")

if __name__ == "__main__":
    create_table()

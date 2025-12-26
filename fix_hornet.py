
import mysql.connector
import os

def fix_hornet():
    # 1. Rename file on disk
    static_dir = r'c:\Users\HP\OneDrive\Masaüstü\moto\static\images'
    old_name = "HONDA_HORNET 750.png"
    new_name = "HONDA_HORNET_750.png"
    
    old_path = os.path.join(static_dir, old_name)
    new_path = os.path.join(static_dir, new_name)
    
    if os.path.exists(old_path):
        try:
            os.rename(old_path, new_path)
            print(f"Renamed: {old_name} -> {new_name}")
        except Exception as e:
            print(f"Error renaming file: {e}")
    elif os.path.exists(new_path):
        print(f"File already renamed to {new_name}")
    else:
        print(f"File not found: {old_name} (and new name doesn't exist either)")

    # 2. Update Database
    conn = mysql.connector.connect(
        host=os.environ.get('MYSQL_HOST', 'localhost'),
        user=os.environ.get('MYSQL_USER', 'root'),
        password=os.environ.get('MYSQL_PASSWORD', 'onurkocaman5353'),
        database=os.environ.get('MYSQL_DB', 'motor_db')
    )
    cursor = conn.cursor()
    
    # Update for the standard listing
    db_path = f"/static/images/{new_name}"
    
    # We update any Hornet 750 listings to use this new path
    cursor.execute("UPDATE motorcycles SET image_url = %s WHERE title LIKE '%Hornet 750%'", (db_path,))
    print(f"Updated {cursor.rowcount} listings in DB to point to {db_path}")
    
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    fix_hornet()


import mysql.connector
import os
import shutil

def fix_data():
    # Database connection
    conn = mysql.connector.connect(
        host=os.environ.get('MYSQL_HOST', 'localhost'),
        user=os.environ.get('MYSQL_USER', 'root'),
        password=os.environ.get('MYSQL_PASSWORD', 'onurkocaman5353'),
        database=os.environ.get('MYSQL_DB', 'motor_db')
    )
    cursor = conn.cursor()

    print("--- 1. Fixing Orphaned Listings ---")
    cursor.execute("UPDATE motorcycles SET user_id = 1 WHERE user_id IS NULL")
    print(f"Updated {cursor.rowcount} listings to belong to User ID 1.")
    conn.commit()

    print("\n--- 2. Fixing Image Paths ---")
    # Map broken DB paths to existing static files
    corrections = {
        '/static/images/ducati_v4.webp': '/static/images/ducati1.webp',
        '/static/images/vespa.webp': '/static/images/sym1.webp', # Placeholder scooter
        '/static/images/bmw_gs.webp': '/static/images/bmw1.webp',
        # CF Moto duplicates/missing
        '/static/images/cf_moto_250_nk.webp': '/static/images/cf1.webp',
        '/static/images/cf_moto_800mt.webp': '/static/images/cf2.webp'
    }

    for bad_path, good_path in corrections.items():
        cursor.execute("UPDATE motorcycles SET image_url = %s WHERE image_url = %s", (good_path, bad_path))
        if cursor.rowcount > 0:
            print(f"Fixed image for {cursor.rowcount} items: {bad_path} -> {good_path}")

    print("\n--- 3. Fixing Filename Encoding (TRIUMPH) ---")
    # Problem: File is named TRİUMPH_TRİDENT_660.png on disk, but we want ASCII TRIUMPH_TRIDENT_660.png
    static_dir = r'c:\Users\HP\OneDrive\Masaüstü\moto\static\images'
    
    # Check for the Turkish named file
    # We iterate to find it because direct access with special chars might be tricky
    found = False
    for filename in os.listdir(static_dir):
        if "TRİUMPH" in filename or "TRUMPH" in filename: # loosely match
            old_path = os.path.join(static_dir, filename)
            new_filename = "TRIUMPH_TRIDENT_660.png"
            new_path = os.path.join(static_dir, new_filename)
            
            try:
                os.rename(old_path, new_path)
                print(f"Renamed file: {filename} -> {new_filename}")
                found = True
                
                # Update DB to point to this new standard name
                db_url = f"/static/images/{new_filename}"
                # Update any record that looks like looking for this bike
                cursor.execute("UPDATE motorcycles SET image_url = %s WHERE title LIKE '%TRIUMPH%'", (db_url,))
                print("Updated DB records for TRIUMPH to new filename.")
                
            except Exception as e:
                print(f"Could not rename {filename}: {e}")
            break
    
    if not found:
        print("Turkish named TRIUMPH file not found (maybe already fixed).")

    conn.commit()
    cursor.close()
    conn.close()
    print("\nDone.")

if __name__ == "__main__":
    fix_data()

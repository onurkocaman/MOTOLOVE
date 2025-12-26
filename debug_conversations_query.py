
import mysql.connector

def debug_query():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='onurkocaman5353',
            database='motor_db'
        )
        cursor = conn.cursor(dictionary=True)

        user_id = 1
        print(f"--- Simulating Query for User ID: {user_id} ---")

        query = """
            SELECT 
                c.id as conversation_id,
                CASE 
                    WHEN c.user_one_id = %s THEN u2.name 
                    ELSE u1.name 
                END as other_user_name,
                m.content as last_message,
                m.created_at as last_message_time,
                (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id AND receiver_id = %s AND is_read = FALSE) as unread_count,
                 mt.title as listing_title
            FROM conversations c
            JOIN users u1 ON c.user_one_id = u1.id
            JOIN users u2 ON c.user_two_id = u2.id
            LEFT JOIN motorcycles mt ON c.listing_id = mt.id
            LEFT JOIN messages m ON m.id = (
                SELECT id FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1
            )
            WHERE c.user_one_id = %s OR c.user_two_id = %s
            ORDER BY m.created_at DESC
        """
        
        cursor.execute(query, (user_id, user_id, user_id, user_id))
        results = cursor.fetchall()

        if not results:
            print("No conversations found.")
        else:
            for row in results:
                print(row)

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    debug_query()

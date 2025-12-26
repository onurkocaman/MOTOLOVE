
# ==================================================
# MESAJLAŞMA API ROTLARI
# ==================================================

@app.route('/api/messages/start', methods=['POST'])
def start_conversation():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapmalısınız.'}), 401

    data = request.get_json()
    sender_id = session['user_id']
    receiver_id = data.get('receiver_id')
    listing_id = data.get('listing_id')

    if not receiver_id:
        return jsonify({'success': False, 'message': 'Alıcı belirtilmedi.'}), 400

    try:
        cur = mysql.connection.cursor()
        
        # Mevcut konuşmayı kontrol et
        cur.execute("""
            SELECT id FROM conversations 
            WHERE (buyer_id = %s AND seller_id = %s AND listing_id = %s)
               OR (buyer_id = %s AND seller_id = %s AND listing_id = %s)
        """, (sender_id, receiver_id, listing_id, receiver_id, sender_id, listing_id))
        
        existing_conv = cur.fetchone()
        
        if existing_conv:
            conversation_id = existing_conv['id']
        else:
            # Yeni konuşma başlat
            cur.execute("""
                INSERT INTO conversations (buyer_id, seller_id, listing_id, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (sender_id, receiver_id, listing_id))
            mysql.connection.commit()
            conversation_id = cur.lastrowid

        cur.close()
        return jsonify({'success': True, 'conversation_id': conversation_id})

    except Exception as e:
        print(f"Konuşma başlatma hatası: {e}")
        return jsonify({'success': False, 'message': 'Veritabanı hatası.'}), 500

@app.route('/api/messages/send', methods=['POST'])
def send_message_api():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapmalısınız.'}), 401

    data = request.get_json()
    conversation_id = data.get('conversation_id')
    content = data.get('content')
    sender_id = session['user_id']

    if not conversation_id or not content:
        return jsonify({'success': False, 'message': 'Eksik bilgi.'}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO messages (conversation_id, sender_id, content, created_at, is_read)
            VALUES (%s, %s, %s, NOW(), FALSE)
        """, (conversation_id, sender_id, content))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})

    except Exception as e:
        print(f"Mesaj gönderme hatası: {e}")
        return jsonify({'success': False, 'message': 'Mesaj gönderilemedi.'}), 500

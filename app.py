from flask import Flask, render_template, jsonify, request, session, redirect, flash
# from flask_mysqldb import MySQL 
import mysql.connector as db_connector
from flask import g

class MySQL:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        @app.teardown_appcontext
        def close_db(error):
            db = g.pop('db_conn', None)
            if db is not None:
                db.close()

    @property
    def connection(self):
        if 'db_conn' not in g:
            try:
                g.db_conn = db_connector.connect(
                    host=self.app.config.get('MYSQL_HOST'),
                    user=self.app.config.get('MYSQL_USER'),
                    password=self.app.config.get('MYSQL_PASSWORD'),
                    database=self.app.config.get('MYSQL_DB'),
                    charset='utf8mb4',
                    use_unicode=True
                    # Force dictionary cursor behavior via arguments if possible, 
                    # but mysql.connector.connect doesn't accept cursor options directly usually.
                    # We handle cursor creation in a wrapper or just trust the wrapper below.
                )
            except db_connector.Error as e:
                # Log error or re-raise
                print(f"Database connection error: {e}")
                raise e

        # Wrapper to Ensure Dictionary Cursor
        class ConnectionWrapper:
            def __init__(self, conn):
                self._conn = conn
            
            def cursor(self, *args, **kwargs):
                if 'dictionary' not in kwargs:
                    kwargs['dictionary'] = True
                return self._conn.cursor(*args, **kwargs)
            
            def __getattr__(self, name):
                return getattr(self._conn, name)
            
            def commit(self):
                return self._conn.commit()
            
            def rollback(self):
                return self._conn.rollback()
            
            def close(self):
                return self._conn.close()

        return ConnectionWrapper(g.db_conn) 

import json
from decimal import Decimal
from datetime import datetime, timedelta # DÜZELTME: 'timedelta' buraya eklendi
import math # YENİ: Sayfalama için eklendi

from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename

import os 
import re # Kural tabanlı bot için basit metin işleme
import httpx # YENİ: Gerçek AI API çağrıları için eklendi (pip install httpx)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Chart.js'in sayıları işlemesi için string yerine float'a çevir
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(CustomJSONEncoder, self).default(obj)

app = Flask(__name__, template_folder='.', static_folder='static')
app.json_encoder = CustomJSONEncoder # JSON encoder'ı uygula

app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'onurkocaman5353') # KENDİ ŞİFRENİZLE DEĞİİŞTİRİN
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'motor_db')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' 

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'BUNU_MUTLAKA_DEGISTIR_COK_GUVENLI_BIR_SEY_YAP')

GEMINI_API_KEY = "" # TALİMATLARA GÖRE BOŞ BIRAKILDI
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={GEMINI_API_KEY}"

PROFILE_PIC_FOLDER = 'static/uploads/profile_pics'
LISTING_UPLOAD_FOLDER = 'static/uploads/listings' # YENİ: İlan resimleri için
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'} # 'gif' kaldırıldı, 'webp' eklendi
app.config['PROFILE_PIC_FOLDER'] = PROFILE_PIC_FOLDER
app.config['LISTING_UPLOAD_FOLDER'] = LISTING_UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

os.makedirs(PROFILE_PIC_FOLDER, exist_ok=True)
os.makedirs(LISTING_UPLOAD_FOLDER, exist_ok=True) # YENİ

mysql = MySQL(app)

def is_admin():
    return session.get('user_role') == 'admin'

def get_user_common_data():
    user_id = session.get('user_id', None)
    user_name = session.get('user_name', None)
    user_role = session.get('user_role', None)
    user_image_url = None
    
    if user_id:
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT profile_image_url FROM users WHERE id = %s", (user_id,))
            user_data = cur.fetchone()
            cur.close()
            if user_data:
                user_image_url = user_data['profile_image_url']
        except Exception as e:
            print(f"Kullanıcı verisi çekme hatası: {e}")
            
    return {
        "user_id": user_id,
        "user_name": user_name,
        "user_role": user_role,
        "user_image_url": user_image_url
    }

# ==================================================
# ANA SAYFA VE KULLANICI ROTLARI
# ==================================================

@app.route('/')
def home():
    common_data = get_user_common_data()
    return render_template('index.html', **common_data)

@app.route('/login')
def login_page():
    common_data = get_user_common_data()
    return render_template('login.html', **common_data)

@app.route('/sifresifirlama')
def sifre_sifirlama_page():
    common_data = get_user_common_data()
    return render_template('sifresifirlama.html', **common_data)

@app.route('/ihale')
def ihale_list_page():
    common_data = get_user_common_data()
    all_auctions = []
    
    try:
        cur = mysql.connection.cursor()
        
        # Sütun adları büyük harfle düzeltildi (Start_price -> current_price)
        cur.execute("""
            SELECT id, title, description, image_url, Current_price as current_price, End_time as end_time 
            FROM auctions 
            WHERE Status = 'active' AND End_time > NOW()
            ORDER BY End_time ASC
        """)
        all_auctions = cur.fetchall()
        cur.close()
        
    except Exception as e:
        print(f"İhale listeleme sayfası hatası: {e}")
    
    return render_template('ihale.html', 
                           **common_data, # user_name, user_id, user_image_url buradan gelir
                           auctions_list=all_auctions)

@app.route('/ihale/<int:auction_id>')
def ihale_detail_page(auction_id):
    common_data = get_user_common_data()
    
    return render_template('ihale.html', 
                           **common_data, # user_name, user_id, user_image_url buradan gelir
                           auction_id=auction_id)

@app.route('/ilanlar')
def ilanlar_page():
    common_data = get_user_common_data()
            
    return render_template('ilan.html', **common_data)

@app.route('/ilan/<int:id>')
def ilan_detay_page(id):
    common_data = get_user_common_data()
    
    try:
        cur = mysql.connection.cursor()
        
        # 1. Fetch Listing Details + Seller Info
        # Using dictionary=True cursor implied by wrapper or explicit request
        cur.execute("""
            SELECT m.*, u.name as seller_name, u.phone as seller_phone, 
                   u.profile_image_url as seller_image, u.created_at as seller_joined
            FROM motorcycles m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = %s
        """, (id,))
        listing_data = cur.fetchone()
        
        if not listing_data:
            cur.close()
            return render_template('404.html', **common_data), 404

        # 2. Fetch Comments
        cur.execute("""
            SELECT c.*, u.name as user_name, u.profile_image_url as user_image
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.motorcycle_id = %s
            ORDER BY c.created_at DESC
        """, (id,))
        comments = cur.fetchall()
        
        cur.close()
        
        # Structure data for template
        listing = listing_data
        seller = {
            'name': listing_data['seller_name'],
            'phone': listing_data['seller_phone'],
            'profile_image_url': listing_data['seller_image'],
            'created_at': listing_data['seller_joined']
        }
        
        return render_template('ilan_detay.html', 
                               **common_data, 
                               listing=listing, 
                               seller=seller, 
                               comments=comments)
                               
    except Exception as e:
        print(f"İlan detay sayfası hatası: {e}")
        return redirect('/ilanlar')

@app.route('/api/listings/<int:id>/comment', methods=['POST'])
def add_comment(id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Yorum yapmak için giriş yapmalısınız.", "error")
        return redirect(f'/ilan/{id}')
        
    content = request.form.get('content')
    rating = request.form.get('rating')
    
    if not content or not rating:
        flash("Lütfen tüm alanları doldurun.", "error")
        return redirect(f'/ilan/{id}')
        
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO comments (motorcycle_id, user_id, content, rating)
            VALUES (%s, %s, %s, %s)
        """, (id, user_id, content, rating))
        mysql.connection.commit()
        cur.close()
        
        flash("Yorumunuz başarıyla eklendi!", "success")
    except Exception as e:
        mysql.connection.rollback()
        print(f"Yorum ekleme hatası: {e}")
        flash("Bir hata oluştu.", "error")
        
    return redirect(f'/ilan/{id}')

@app.route('/ilanver')
def ilan_ver_page():
    common_data = get_user_common_data()
    
    if not common_data.get('user_id'):
        flash("İlan vermek için lütfen giriş yapın.", "error")
        return redirect('/login')
        
    return render_template('ilanver.html', **common_data)

@app.route('/odeme')
def odeme_page():
    common_data = get_user_common_data()
    user_id = common_data.get('user_id')
    user = None
    
    if user_id:
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT name, email, phone, profile_image_url FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone() 
            cur.close()
        except Exception as e:
            print(f"Ödeme sayfası kullanıcı verisi çekme hatası: {e}")
            
    order_details = {
        "id": request.args.get('id'),
        "type": request.args.get('type'),
        "title": request.args.get('title'),
        "price": request.args.get('price'),
        "image": request.args.get('image')
    }
            
    return render_template('odeme.html', 
                           **common_data, # user_name buradan gelir
                           user=user, 
                           order_details=order_details) # Detayları şablona yolla

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_role', None) # YENİ: Admin çıkışı için role de temizlenmeli
    session.pop('chat_history', None) # YENİ: Çıkış yaparken sohbet geçmişini de temizle
    return redirect('/')

@app.route('/profile')
def profile():
    common_data = get_user_common_data()
    user_id = common_data.get('user_id')
    
    if not user_id:
        return redirect('/login')
        
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT name, email, phone, profile_image_url FROM users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        
        cur.execute("""
            SELECT id, title, price, status, image_url 
            FROM motorcycles 
            WHERE user_id = %s AND category = 'Satılık'
        """, (user_id,))
        user_listings = cur.fetchall()
        
        cur.execute("""
            SELECT m.id, m.title, m.price, m.image_url 
            FROM favorites f
            JOIN motorcycles m ON f.motorcycle_id = m.id
            WHERE f.user_id = %s
        """, (user_id,))
        user_favorites = cur.fetchall()
        
        cur.close()

        return render_template(
            'profil.html', 
            **common_data, # user_name buradan gelir
            user=user_data, 
            listings=user_listings, # Bu değişken profildeki 'İlanlarım' sekmesini doldurur
            favorites=user_favorites
        )
        
    except Exception as e:
        print(f"Profil sayfası hatası: {e}")
        return redirect('/')

@app.route('/ilanver/yayinla', methods=['POST'])
def create_listing():
    user_id = session.get('user_id', None)
    if not user_id:
        return jsonify({"success": False, "message": "İlan vermek için giriş yapmalısınız."}), 401
    
    try:
        title = request.form.get('ad-title')
        brand = request.form.get('ad-brand')
        model = request.form.get('ad-model')
        year = request.form.get('ad-year', type=int)
        km = request.form.get('ad-km', type=int)
        condition = request.form.get('ad-condition') # 'new' or 'used'
        price = request.form.get('ad-price', type=Decimal)
        location = request.form.get('ad-location')
        description = request.form.get('ad-description')
        contact = request.form.get('ad-contact')
        
        if not all([title, brand, model, year, km, condition, price, location, contact]):
             return jsonify({"success": False, "message": "Lütfen yıldızlı (*) tüm alanları doldurun."}), 400

        if 'ad-photos' not in request.files:
            return jsonify({"success": False, "message": "İlan fotoğrafı zorunludur."}), 400
            
        files = request.files.getlist('ad-photos')
        
        if not files or files[0].filename == '':
             return jsonify({"success": False, "message": "Lütfen en az bir fotoğraf seçin."}), 400
        
        file = files[0]
        image_url = None
        
        if file and allowed_file(file.filename):
            safe_title = re.sub(r'[^a-z0-9]', '_', title.lower())
            filename = f"user_{user_id}_{safe_title[:30]}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['LISTING_UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            # DÜZELTME: Windows'ta ters slash sorununu önlemek için değiştir
            image_url = f"/{filepath}".replace("\\", "/") # /static/uploads/listings/...
        else:
            return jsonify({"success": False, "message": "Geçersiz dosya formatı. Lütfen 'png', 'jpg', 'jpeg' veya 'webp' kullanın."}), 400

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO motorcycles (
                user_id, title, brand, model, year, km, `condition`, 
                price, location, description, contact_info, 
                image_url, category, status, created_at
            ) 
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, 
                %s, 'Satılık', 'pending', NOW()
            )
        """, (
            user_id, title, brand, model, year, km, 
            'Sıfır' if condition == 'new' else 'İkinci El', # HTML'deki 'new'/'used' değerini DB'ye çevir
            price, location, description, contact,
            image_url
        ))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "İlanınız başarıyla alındı! İncelemenin ardından yayınlanacaktır."}), 201

    except Exception as e:
        mysql.connection.rollback()
        print(f"İlan oluşturma hatası: {e}")
        if '1054' in str(e):
             return jsonify({"success": False, "message": f"Veritabanı hatası: {e}. 'motorcycles' tablosu güncellenmemiş olabilir."}), 500
        return jsonify({"success": False, "message": f"Sunucu hatası: {e}"}), 500

@app.route('/api/register', methods=['POST'])
def register():
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek: JSON bekleniyordu."}), 400

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"success": False, "message": "İsim, e-posta ve şifre alanları zorunludur."}), 400

    try:
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing_user = cur.fetchone()
        
        if existing_user:
            cur.close()
            return jsonify({"success": False, "message": "Bu e-posta adresi zaten kayıtlı."}), 409
            
        password_hash = generate_password_hash(password)
        
        cur.execute("INSERT INTO users (name, email, password_hash, phone, role) VALUES (%s, %s, %s, %s, 'user')", (name, email, password_hash, None))
        mysql.connection.commit()
        
        session['user_id'] = cur.lastrowid
        session['user_name'] = name
        session['user_role'] = 'user' # YENİ: Role session'a eklendi
        
        cur.close()
        
        return jsonify({"success": True, "message": "Başarıyla kayıt oldunuz! Yönlendiriliyorsunuz..."}), 201

    except Exception as e:
        mysql.connection.rollback()
        print(f"Kayıt hatası: {e}")
        if '1054' in str(e) and 'role' in str(e):
            flash("Veritabanı hatası: 'users' tablosunda 'role' sütunu bulunamadı. Lütfen app.py dosyasındaki SQL komutunu çalıştırın.", "error")
            return jsonify({"success": False, "message": "Kayıt sistemi yapılandırma hatası."}), 500
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek: JSON bekleniyordu."}), 400

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "E-posta ve şifre alanları zorunludur."}), 400

    try:
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT id, name, password_hash, role FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user.get('role', 'user') # YENİ: Role session'a eklendi
            
            return jsonify({"success": True, "message": "Başarıyla giriş yaptınız! Yönlendiriliyorsunuz..."}), 200
        else:
            return jsonify({"success": False, "message": "E-posta veya şifre hatalı."}), 401

    except Exception as e:
        print(f"Giriş hatası: {e}")
        if '1054' in str(e) and 'role' in str(e):
            flash("Veritabanı hatası: 'users' tablosunda 'role' sütunu bulunamadı. Lütfen app.py dosyasındaki SQL komutunu çalıştırın.", "error")
            return jsonify({"success": False, "message": "Giriş sistemi yapılandırma hatası."}), 500
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/create-order', methods=['POST'])
def create_order():
    user_id = session.get('user_id', None)
    if not user_id:
        return jsonify({"success": False, "message": "Sipariş oluşturmak için giriş yapmalısınız."}), 401
        
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek."}), 400
        
    data = request.get_json()
    
    motorcycle_id = data.get('motorcycle_id')
    transaction_type = data.get('transaction_type')
    
    customer_name = data.get('customer_name')
    customer_email = data.get('customer_email')
    customer_phone = data.get('customer_phone')
    
    delivery_address = data.get('delivery_address')
    delivery_method = data.get('delivery_method') # 'pickup' or 'home' (Satılık için)
    
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    
    billing_name = data.get('billing_name')
    billing_address = data.get('billing_address')
    billing_tax_no = data.get('billing_tax_no')
    
    payment_method = data.get('payment_method')
    coupon_code = data.get('coupon_code')

    if not motorcycle_id or not customer_name or not payment_method:
        return jsonify({"success": False, "message": "Eksik sipariş bilgisi (Motor ID, İsim, Ödeme Yöntemi)."}), 400
        
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT price, category FROM motorcycles WHERE id = %s", (motorcycle_id,))
        motor = cur.fetchone()
        
        if not motor:
            cur.close()
            return jsonify({"success": False, "message": "Motor bulunamadı."}), 404
            
        if motor['category'].lower() != transaction_type.lower():
            cur.close()
            return jsonify({"success": False, "message": "İşlem tipi hatası."}), 400
            
        db_price = motor['price']
        subtotal = Decimal(0)
        shipping_fee = Decimal(0)
        discount_amount = Decimal(0)
        tax_rate = Decimal(0.20)
        
        if transaction_type.lower() == 'satılık':
            subtotal = db_price
            if delivery_method == 'home' and delivery_address:
                shipping_fee = Decimal(500.00) # Sabit Kargo Ücreti
            
        elif transaction_type.lower() == 'kiralık':
            if not start_date_str or not end_date_str:
                cur.close()
                return jsonify({"success": False, "message": "Kiralama için tarihler zorunludur."}), 400
            
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                cur.close()
                return jsonify({"success": False, "message": "Geçersiz tarih formatı."}), 400
                
            days = (end_date - start_date).days
            if days <= 0: days = 1
                
            subtotal = db_price * days
            shipping_fee = Decimal(150.00) # Kiralama teslimat ücreti
            
            cur.execute("""
                SELECT id FROM orders
                WHERE motorcycle_id = %s
                AND transaction_type = 'Kiralık'
                AND (
                    (%s < end_date AND %s > start_date) OR
                    (%s < end_date AND %s > start_date) OR
                    (start_date < %s AND end_date > %s)
                )
            """, (motorcycle_id, start_date_str, start_date_str, end_date_str, end_date_str, end_date_str, start_date_str))
            
            existing_order = cur.fetchone()
            
            if existing_order:
                cur.close()
                return jsonify({"success": False, "message": "Bu motor seçtiğiniz tarihler arasında zaten kiralanmış."}), 409

        else:
            cur.close()
            return jsonify({"success": False, "message": "Geçersiz işlem tipi."}), 400

        if coupon_code == "MOTOLOVE10":
            discount_amount = (subtotal * Decimal(0.10)).quantize(Decimal('0.01'))
            
        discounted_subtotal = subtotal - discount_amount
        tax = (discounted_subtotal * tax_rate).quantize(Decimal('0.01'))
        total_price = discounted_subtotal + tax + shipping_fee

        status = 'Pending Payment' # Varsayılan (Bayide Öde)
        payment_successful = False
        
        if payment_method == 'Kredi Kartı':
            payment_successful = True 
            status = 'Completed'
        
        elif payment_method == 'Bayide Öde':
             payment_successful = True # Siparişin oluşması için başarılı sayıyoruz
             status = 'Pending Payment' # Durum: Ödeme Bekleniyor
        
        
        if payment_successful:
            cur.execute("""
                INSERT INTO orders (
                    user_id, motorcycle_id, total_amount, status, transaction_type, 
                    customer_name, customer_email, customer_phone, delivery_address, 
                    start_date, end_date,
                    payment_method, shipping_fee, discount_amount,
                    billing_name, billing_address, billing_tax_no,
                    created_at 
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                user_id, motorcycle_id, total_price, status, transaction_type, 
                customer_name, customer_email, customer_phone, 
                delivery_address if (transaction_type.lower() == 'kiralık' or delivery_method == 'home') else None,
                start_date_str if transaction_type.lower() == 'kiralık' else None,
                end_date_str if transaction_type.lower() == 'kiralık' else None,
                payment_method, shipping_fee, discount_amount,
                billing_name, billing_address, billing_tax_no
            ))
            
            if transaction_type.lower() == 'satılık' and status == 'Completed':
                cur.execute("""
                    UPDATE motorcycles SET status = 'Satıldı' 
                    WHERE id = %s
                """, (motorcycle_id,))
            
            mysql.connection.commit()
            cur.close()
            
            return jsonify({"success": True, "message": "Sipariş başarıyla oluşturuldu."}), 201
        
        else:
            cur.close()
            return jsonify({"success": False, "message": "Ödeme ağ geçidi tarafından reddedildi."}), 402

    except Exception as e:
        mysql.connection.rollback()
        print(f"Sipariş oluşturma hatası: {e}")
        if '1146' in str(e):
            return jsonify({"success": False, "message": "Sunucu hatası: 'orders' tablosu bulunamadı."}), 500
        if '1054' in str(e):
            return jsonify({"success": False, "message": f"Veritabanı hatası: {e}. 'orders' tablosu güncellenmemiş olabilir."}), 500
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500
        
@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    user_id = session.get('user_id', None)
    if not user_id:
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 401
        
    try:
        new_name = request.form.get('name')
        new_phone = request.form.get('phone')
        
        if not new_name:
            return jsonify({"success": False, "message": "İsim boş bırakılamaz."}), 400
        
        image_url = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            
            if file and file.filename != '' and allowed_file(file.filename):
                filename = f"user_{user_id}_{secure_filename(file.filename)}"
                filepath = os.path.join(app.config['PROFILE_PIC_FOLDER'], filename)
                
                file.save(filepath)
                
                # DÜZELTME: Windows slash sorunu çözümü
                image_url = f"/{filepath}".replace("\\", "/") # /static/uploads/profile_pics/...

        cur = mysql.connection.cursor()
        
        if image_url:
            cur.execute("""
                UPDATE users 
                SET name = %s, phone = %s, profile_image_url = %s 
                WHERE id = %s
            """, (new_name, new_phone, image_url, user_id))
        else:
            cur.execute("""
                UPDATE users 
                SET name = %s, phone = %s 
                WHERE id = %s
            """, (new_name, new_phone, user_id))

        mysql.connection.commit()
        cur.close()
        
        session['user_name'] = new_name
        
        return jsonify({"success": True, "message": "Profil bilgilerin başarıyla güncellendi!"}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        print(f"Profil güncelleme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/profile/change-password', methods=['POST'])
def change_password():
    user_id = session.get('user_id', None)
    if not user_id:
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 401

    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek."}), 400
        
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not current_password or not new_password or not confirm_password:
        return jsonify({"success": False, "message": "Tüm alanlar zorunludur."}), 400
        
    if new_password != confirm_password:
        return jsonify({"success": False, "message": "Yeni şifreler eşleşmiyor."}), 400
        
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            return jsonify({"success": False, "message": "Kullanıcı bulunamadı."}), 404
            
        if not check_password_hash(user['password_hash'], current_password):
            cur.close()
            return jsonify({"success": False, "message": "Mevcut şifreniz hatalı."}), 403
            
        new_password_hash = generate_password_hash(new_password)
        cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, user_id))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "Şifreniz başarıyla değiştirildi!"}), 200
        
    except Exception as e:
        mysql.connection.rollback()
        print(f"Şifre değiştirme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/listing/delete/<int:listing_id>', methods=['DELETE'])
def delete_listing(listing_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Yetkisiz erişim"}), 401
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM motorcycles WHERE id = %s AND user_id = %s", (listing_id, user_id))
        mysql.connection.commit()
        
        if cur.rowcount > 0: 
            cur.close()
            return jsonify({"success": True, "message": "İlan silindi."}), 200
        else:
            cur.close()
            return jsonify({"success": False, "message": "İlan bulunamadı veya bu ilanı silme yetkiniz yok."}), 404
            
    except Exception as e:
        mysql.connection.rollback()
        print(f"İlan silme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/favorite/add', methods=['POST'])
def add_favorite():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Favoriye eklemek için giriş yapmalısınız."}), 401
        
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek."}), 400
        
    data = request.get_json()
    motorcycle_id = data.get('motorcycle_id')
    
    if not motorcycle_id:
        return jsonify({"success": False, "message": "Motor ID eksik."}), 400
        
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM favorites WHERE user_id = %s AND motorcycle_id = %s", (user_id, motorcycle_id))
        exists = cur.fetchone()
        
        if exists:
            cur.close()
            return jsonify({"success": False, "message": "Bu ilan zaten favorilerinizde."}), 409
        
        cur.execute("INSERT INTO favorites (user_id, motorcycle_id) VALUES (%s, %s)", (user_id, motorcycle_id))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "Favorilere eklendi."}), 201
        
    except Exception as e:
        mysql.connection.rollback()
        print(f"Favori ekleme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/favorite/remove/<int:motorcycle_id>', methods=['DELETE'])
def remove_favorite(motorcycle_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Yetkisiz erişim"}), 401
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM favorites WHERE motorcycle_id = %s AND user_id = %s", (motorcycle_id, user_id))
        mysql.connection.commit()
        
        if cur.rowcount > 0:
            cur.close()
            return jsonify({"success": True, "message": "Favoriden kaldırıldı."}), 200
        else:
            cur.close()
            return jsonify({"success": False, "message": "Favori bulunamadı."}), 404
            
    except Exception as e:
        mysql.connection.rollback()
        print(f"Favori kaldırma hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/motorcycles', methods=['GET'])
def get_motorcycles():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM motorcycles WHERE category = 'Satılık' ORDER BY RAND() LIMIT 3")
        data = cur.fetchall()
        cur.close()
        response = jsonify(data)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        print(f"Veritabanı hatası (Satılık): {e}")
        return jsonify({"error": f"Veritabanı hatası: {e}"}), 500
    


# ==================================================
# MESAJLAŞMA SİSTEMİ API
# ==================================================

@app.route('/api/messages/start', methods=['POST'])
def start_conversation():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Giriş yapmalısınız."}), 401
    
    data = request.get_json()
    listing_id = data.get('listing_id')
    receiver_id = data.get('receiver_id') 

    # Eğer listing_id varsa receiver_id'yi bulmaya çalış (ilan sahibini)
    try:
        cur = mysql.connection.cursor()
        
        if listing_id and not receiver_id:
            cur.execute("SELECT user_id FROM motorcycles WHERE id = %s", (listing_id,))
            res = cur.fetchone()
            if res:
                receiver_id = res['user_id']
        
        if not receiver_id:
            cur.close()
            return jsonify({"success": False, "message": "Alıcı bulunamadı."}), 400
            
        if int(receiver_id) == int(user_id):
             cur.close()
             return jsonify({"success": False, "message": "Kendinize mesaj atamazsınız."}), 400

        # Mevcut konuşma var mı?
        # user_one_id her zaman küçük olan ID olsun (Unique constraint için pratik)
        u1_id = min(int(user_id), int(receiver_id))
        u2_id = max(int(user_id), int(receiver_id))
        
        cur.execute("""
            SELECT id FROM conversations 
            WHERE user_one_id = %s AND user_two_id = %s
        """, (u1_id, u2_id))
        
        existing_conv = cur.fetchone()
        
        if existing_conv:
            conversation_id = existing_conv['id']
            # Eğer ilan farklıysa güncelle (Opsiyonel: İsterseniz güncellemeyebilirsiniz)
            if listing_id:
                 cur.execute("UPDATE conversations SET listing_id = %s WHERE id = %s", (listing_id, conversation_id))
                 mysql.connection.commit()
        else:
            # Yeni konuşma oluştur
            cur.execute("""
                INSERT INTO conversations (user_one_id, user_two_id, listing_id)
                VALUES (%s, %s, %s)
            """, (u1_id, u2_id, listing_id))
            mysql.connection.commit()
            conversation_id = cur.lastrowid
            
        cur.close()
        return jsonify({"success": True, "conversation_id": conversation_id}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Konuşma başlatma hatası: {e}")
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/mesajlarim')
def mesajlarim_page():
    common_data = get_user_common_data()
    if not common_data.get('user_id'):
        return redirect('/login')
    return render_template('mesajlarim.html', **common_data)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json(silent=True)
    email = None
    if data and 'email' in data:
        email = data['email']
    if email is None and request.form:
        if 'email' in request.form:
            email = request.form['email']
    
    if email is None:
        flash('E-posta adresi bulunamadı.', 'error')
        return redirect(request.referrer or '/')
    if not email:
        flash('E-posta adresi boş olamaz.', 'error')
        return redirect(request.referrer or '/')
        
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO subscribers (email) VALUES (%s)", (email,))
        mysql.connection.commit()
        cur.close()
        flash('Başarıyla abone oldunuz!', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        if 'Duplicate entry' in str(e):
            flash('Bu e-posta adresi zaten kayıtlı.', 'error')
        else:
            flash('Bir veritabanı hatası oluştu.', 'error')
            
    return redirect(request.referrer or '/')

@app.route('/api/motorcycles/rentals', methods=['GET'])
def get_rentals():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM motorcycles WHERE category = 'Kiralık' ORDER BY RAND() LIMIT 3")
        data = cur.fetchall()
        cur.close()
        
        response = jsonify(data)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        print(f"Kiralık motorlar veritabanı hatası: {e}")
        return jsonify({"error": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/auctions/featured', methods=['GET'])
def get_featured_auction():
    try:
        cur = mysql.connection.cursor()
        
        # Sütun adları büyük harfle düzeltildi
        cur.execute("""
            SELECT id, title, description, End_time as end_time, Current_price as current_price, image_url
            FROM auctions 
            WHERE Status = 'active' AND End_time > NOW()
            ORDER BY End_time ASC 
            LIMIT 1
        """)
        featured_auction = cur.fetchone()
        cur.close()
        
        if featured_auction:
            return jsonify({"success": True, "auction": featured_auction}), 200
        else:
            return jsonify({"success": False, "message": "Aktif ihale bulunamadı."}), 404

    except Exception as e:
        print(f"Öne çıkan ihale çekme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# ==================================================
# İHALE API ROTLARI
# ==================================================

@app.route('/api/auctions/<int:auction_id>', methods=['GET'])
def get_auction_details(auction_id):
    try:
        cur = mysql.connection.cursor()
        
        # Sütun adları büyük harfle düzeltildi
        cur.execute("""
            SELECT 
                a.id, a.title, a.description, a.image_url, a.End_time as end_time,
                a.Current_price as current_price, a.Min_increment as min_increment, a.Status as status,
                a.Highest_bidder_id as highest_bidder_id,
                u.name AS highest_bidder_name
            FROM auctions a
            LEFT JOIN users u ON a.Highest_bidder_id = u.id
            WHERE a.id = %s
        """, (auction_id,))
        auction_data = cur.fetchone()
        
        if not auction_data:
            cur.close()
            return jsonify({"success": False, "message": "İhale bulunamadı."}), 404
            
        cur.execute("""
            SELECT 
                b.id, b.user_id, b.bid_amount, b.bid_time,
                u.name AS bidder_name
            FROM bids b
            JOIN users u ON b.user_id = u.id
            WHERE b.auction_id = %s
            ORDER BY b.bid_time DESC
            LIMIT 10
        """, (auction_id,))
        bids_history = cur.fetchall()
        
        cur.close()
        
        return jsonify({
            "success": True,
            "auction": auction_data,
            "bids": bids_history
        }), 200

    except Exception as e:
        print(f"İhale verisi çekme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/auctions/<int:auction_id>/bid', methods=['POST'])
def place_bid(auction_id):
    user_id = session.get('user_id', None)
    if not user_id:
        return jsonify({"success": False, "message": "Teklif vermek için giriş yapmalısınız."}), 401
        
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek."}), 400
        
    data = request.get_json()
    try:
        bid_amount = Decimal(data.get('amount'))
    except Exception:
        return jsonify({"success": False, "message": "Geçersiz teklif tutarı."}), 400

    if bid_amount <= 0:
        return jsonify({"success": False, "message": "Teklif tutarı pozitif olmalıdır."}), 400

    try:
        cur = mysql.connection.cursor()
        
        # Sütun adları büyük harfle düzeltildi
        cur.execute("""
            SELECT Current_price as current_price, Min_increment as min_increment, 
                   End_time as end_time, Status as status, Highest_bidder_id as highest_bidder_id
            FROM auctions
            WHERE id = %s
            FOR UPDATE
        """, (auction_id,))
        auction = cur.fetchone()

        if not auction:
            cur.close()
            return jsonify({"success": False, "message": "İhale bulunamadı."}), 404
            
        if auction['status'] != 'active':
            cur.close()
            return jsonify({"success": False, "message": "Bu ihale şu anda aktif değil."}), 400
            
        # DÜZELTME: Saat farkı sorunları için
        current_time = datetime.now()
        if current_time >= auction['end_time']:
            cur.close()
            # Otomatik bitir
            cur = mysql.connection.cursor()
            cur.execute("UPDATE auctions SET Status = 'ended' WHERE id = %s", (auction_id,))
            mysql.connection.commit()
            cur.close()
            return jsonify({"success": False, "message": "İhale sona erdi."}), 400
            
        if user_id == auction['highest_bidder_id']:
            cur.close()
            return jsonify({"success": False, "message": "En yüksek teklif zaten sizde."}), 400
            
        min_bid = auction['current_price'] + auction['min_increment']
        if bid_amount < min_bid:
            cur.close()
            return jsonify({"success": False, "message": f"Teklifiniz en az {min_bid:,.0f} TL olmalıdır."}), 400

        cur.execute("""
            INSERT INTO bids (auction_id, user_id, bid_amount, bid_time)
            VALUES (%s, %s, %s, NOW())
        """, (auction_id, user_id, bid_amount))
        
        # Sütun adları büyük harfle düzeltildi
        cur.execute("""
            UPDATE auctions
            SET Current_price = %s, Highest_bidder_id = %s
            WHERE id = %s
        """, (bid_amount, user_id, auction_id))
        
        time_left = (auction['end_time'] - datetime.now()).total_seconds()
        if time_left < 120: # 2 dakikadan az kaldıysa
            # Sütun adı büyük harfle düzeltildi
            cur.execute("""
                UPDATE auctions
                SET End_time = (NOW() + INTERVAL 2 MINUTE)
                WHERE id = %s
            """, (auction_id,))
            print(f"Anti-Sniping tetiklendi: İhale {auction_id} uzatıldı.")

        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "Teklifiniz başarıyla alındı!"}), 201

    except Exception as e:
        mysql.connection.rollback()
        print(f"Teklif verme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/auctions/others', methods=['GET'])
def get_other_auctions():
    exclude_id = request.args.get('exclude', 0, type=int)
    
    try:
        cur = mysql.connection.cursor()
        
        # Sütun adları büyük harfle düzeltildi
        query = """
            SELECT id, title, image_url, Current_price as current_price, Status as status, End_time as end_time
            FROM auctions 
            WHERE Status IN ('active', 'ended') AND id != %s
            ORDER BY RAND()
            LIMIT 3
        """
        cur.execute(query, (exclude_id,))
        auctions = cur.fetchall()
        cur.close()
        
        return jsonify({"success": True, "auctions": auctions}), 200

    except Exception as e:
        print(f"Diğer ihaleler çekme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# ==================================================
# İLAN API ROTLARI
# ==================================================

@app.route('/api/filtre-verisi', methods=['GET'])
def get_filter_data():
    try:
        cur = mysql.connection.cursor()
        
        brands_list = []
        
        cur.execute("SELECT MAX(price) AS max_price FROM motorcycles")
        max_price_data = cur.fetchone()
        max_price = max_price_data.get('max_price') if max_price_data.get('max_price') else 1000000
        
        cur.close()
        
        return jsonify({
            "success": True,
            "brands": brands_list, # Boş liste gönderiyoruz
            "max_price": max_price 
        }), 200

    except Exception as e:
        print(f"Filtre verisi çekme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/ilanlar', methods=['GET'])
def get_all_listings():
    user_id = session.get('user_id', None)

    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 9))
    except ValueError:
        page = 1
        limit = 9
    
    if page < 1: page = 1
    if limit < 1: limit = 9
    offset = (page - 1) * limit
    
    sort_by = request.args.get('sort', 'newest') # 'newest', 'price_asc', 'price_desc'
    
    category = request.args.get('category') # 'Satılık', 'Kiralık'
    condition = request.args.getlist('condition') # 'Sıfır', 'İkinci El' (Liste olarak alır)
    price_min = request.args.get('price_min', type=int)
    price_max = request.args.get('price_max', type=int)
    year_min = request.args.get('year_min', type=int)
    year_max = request.args.get('year_max', type=int)
    km_min = request.args.get('km_min', type=int)
    km_max = request.args.get('km_max', type=int)
    
    search_query = request.args.get('q') # Arama sorgusunu al

    params = []
    where_conditions = []
    
    where_conditions.append("m.status != 'Satıldı'")
    
    if category and category != 'Tümü':
        where_conditions.append("m.category = %s")
        params.append(category)
        
    if price_min is not None:
        where_conditions.append("m.price >= %s")
        params.append(price_min)
        
    if price_max is not None and price_max < 1000000:
        where_conditions.append("m.price <= %s")
        params.append(price_max)
        
    if year_min is not None:
        where_conditions.append("m.year >= %s")
        params.append(year_min)
        
    if year_max is not None:
        where_conditions.append("m.year <= %s")
        params.append(year_max)
        
    if km_min is not None:
        where_conditions.append("m.km >= %s")
        params.append(km_min)
        
    if km_max is not None:
        where_conditions.append("m.km <= %s")
        params.append(km_max)
        
    if condition and len(condition) == 1:
        where_conditions.append("m.condition = %s")
        params.append(condition[0])
    
    if search_query:
        where_conditions.append("(m.title LIKE %s)")
        search_param = f"%{search_query}%"
        params.append(search_param) # params'a ekle (sadece 1 kez)
        
    where_clause = " AND ".join(where_conditions)
    
    order_clause = "ORDER BY m.created_at DESC" # Varsayılan
    if sort_by == 'price_asc':
        order_clause = "ORDER BY m.price ASC"
    elif sort_by == 'price_desc':
        order_clause = "ORDER BY m.price DESC"
        
    try:
        cur = mysql.connection.cursor()
        
        count_query = f"""
            SELECT COUNT(m.id) AS total
            FROM motorcycles m
            WHERE {where_clause}
        """
        cur.execute(count_query, tuple(params))
        total_items = cur.fetchone()['total']
        total_pages = math.ceil(total_items / limit)

        data_params = [user_id] + params + [limit, offset]
        
        data_query = f"""
            SELECT 
                m.*,
                CASE WHEN f.user_id IS NOT NULL THEN true ELSE false END AS is_favorited
            FROM motorcycles m
            LEFT JOIN favorites f ON m.id = f.motorcycle_id AND f.user_id = %s
            WHERE {where_clause}
            {order_clause}
            LIMIT %s OFFSET %s
        """
        
        cur.execute(data_query, tuple(data_params))
        items = cur.fetchall()
        cur.close()

        return jsonify({
            "success": True,
            "items": items,
            "pagination": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": limit
            }
        }), 200

    except Exception as e:
        print(f"İlan listeleme API hatası: {e}")
        if '1054' in str(e): # Unknown column
             return jsonify({"success": False, "message": f"Veritabanı hatası: Sorguda bilinmeyen bir sütun var (örn: 'condition' veya 'brand'). Hata: {e}"}), 500
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# ==================================================
# FORUM SAYFASI VE API ROTLARI
# ==================================================

def render_forum_page():
    common_data = get_user_common_data()
            
    return render_template('forum.html', **common_data)

@app.route('/forum')
def forum_home():
    return render_forum_page()

@app.route('/forum/category/<int:category_id>')
def forum_category(category_id):
    return render_forum_page()

@app.route('/forum/thread/<int:thread_id>')
def forum_thread(thread_id):
    return render_forum_page()

# ===== DÜZELTİLMİŞ FONKSİYON =====
def handle_db_error(e, operation="API"):
    """Veritabanı hatalarını yakalar ve anlamlı JSON mesajları döndürür."""
    error_str = str(e)
    print(f"{operation} hatası: {e}")
    
    try: # YENİ: Hata ayıklarken hata olmaması için try..except
        if '1146' in error_str: # Table doesn't exist
            table_name = "bilinmeyen bir tablo"
            # Önce tam yolu (db_name.table_name) arar
            table_name_match = re.search(r"Table '.*?\.(.*?)' doesn't exist", error_str)
            
            if table_name_match: # Eşleşme bulunduysa
                table_name = table_name_match.group(1)
            else: # Eşleşme bulunamadıysa, daha basit bir regex (sadece tablo adı) dener
                table_name_match_simple = re.search(r"Table '(.*?)' doesn't exist", error_str)
                if table_name_match_simple:
                    table_name = table_name_match_simple.group(1).split('.')[-1] # db.tablo ise sadece tabloyu al

            message = f"Veritabanı hatası: '{table_name}' tablosu bulunamadı."

            # Hangi özelliğin etkilendiğine dair ipucu ver
            if 'forum' in table_name:
                message = "Veritabanı hatası: Gerekli forum tabloları (örn: 'forum_categories') bulunamadı. Lütfen app.py dosyasındaki SQL talimatlarını kontrol edin."
            elif 'conversation' in table_name or 'message' in table_name:
                message = "Veritabanı hatası: Mesajlaşma tabloları (örn: 'conversations', 'messages') bulunamadı. Lütfen app.py dosyasındaki SQL talimatlarını kontrol edin."
            elif 'auction' in table_name or 'bid' in table_name:
                 message = "Veritabanı hatası: İhale tabloları (örn: 'auctions', 'bids') bulunamadı. Lütfen app.py dosyasındaki SQL talimatlarını kontrol edin."
            
            return jsonify({"success": False, "message": message}), 500
            
        if '1054' in error_str: # Unknown column
            return jsonify({"success": False, "message": f"Veritabanı hatası: Bilinmeyen sütun. Hata: {e}"}), 500
            
        return jsonify({"success": False, "message": f"Sunucu hatası: {e}"}), 500
    except Exception as internal_e:
        # handle_db_error'un kendisi çökerse
        print(f"!!! handle_db_error İÇİNDE HATA OLUŞTU: {internal_e}")
        return jsonify({"success": False, "message": f"Sunucu hata işleme hatası: {e}"}), 500
# ===== /DÜZELTİLMİŞ FONKSİYON =====

@app.route('/api/forum/categories', methods=['GET'])
def get_forum_categories():
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT 
                c.id, c.name, c.description, c.icon,
                COUNT(DISTINCT t.id) AS thread_count,
                COUNT(p.id) AS post_count
            FROM forum_categories c
            LEFT JOIN forum_threads t ON c.id = t.category_id
            LEFT JOIN forum_posts p ON t.id = p.thread_id
            GROUP BY c.id, c.name, c.description, c.icon
            ORDER BY c.id ASC
        """)
        categories = cur.fetchall()
        cur.close()
        
        return jsonify({"success": True, "categories": categories}), 200

    except Exception as e:
        return handle_db_error(e, "Kategori listeleme")

@app.route('/api/forum/threads/<int:category_id>', methods=['GET'])
def get_forum_threads(category_id):
    try:
        page = request.args.get('page', 1, type=int)
        limit = 15 # Sayfa başına konu sayısı
        offset = (page - 1) * limit
        
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT id, name, description FROM forum_categories WHERE id = %s", (category_id,))
        category_info = cur.fetchone()
        
        if not category_info:
            cur.close()
            return jsonify({"success": False, "message": "Kategori bulunamadı."}), 404
            
        cur.execute("SELECT COUNT(id) AS total FROM forum_threads WHERE category_id = %s", (category_id,))
        total_items = cur.fetchone()['total']
        total_pages = math.ceil(total_items / limit)
        
        cur.execute("""
            SELECT
                t.id, t.title, t.created_at, t.views,
                t.user_id,
                u.name AS author_name,
                u.profile_image_url AS author_image,
                (SELECT COUNT(id) FROM forum_posts p WHERE p.thread_id = t.id) - 1 AS reply_count,
                t.last_reply_at,
                (SELECT usr.name 
                 FROM forum_posts lp 
                 JOIN users usr ON lp.user_id = usr.id 
                 WHERE lp.thread_id = t.id 
                 ORDER BY lp.created_at DESC 
                 LIMIT 1) AS last_reply_author
            FROM forum_threads t
            JOIN users u ON t.user_id = u.id
            WHERE t.category_id = %s
            ORDER BY t.last_reply_at DESC
            LIMIT %s OFFSET %s
        """, (category_id, limit, offset))
        
        threads = cur.fetchall()
        cur.close()
        
        return jsonify({
            "success": True,
            "category": category_info,
            "threads": threads,
            "pagination": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": limit
            }
        }), 200

    except Exception as e:
        return handle_db_error(e, "Konu listeleme")

@app.route('/api/forum/thread/<int:thread_id>', methods=['GET'])
def get_forum_thread_posts(thread_id):
    user_id = session.get('user_id', None)
    
    try:
        page = request.args.get('page', 1, type=int)
        limit = 10 # Sayfa başına gönderi sayısı (forum.html JS ile eşleşmeli)
        offset = (page - 1) * limit

        cur = mysql.connection.cursor()
        
        cur.execute("UPDATE forum_threads SET views = views + 1 WHERE id = %s", (thread_id,))
        
        cur.execute("""
            SELECT t.id, t.title, t.category_id, c.name AS category_name
            FROM forum_threads t
            JOIN forum_categories c ON t.category_id = c.id
            WHERE t.id = %s
        """, (thread_id,))
        thread_info = cur.fetchone()
        
        if not thread_info:
            cur.close()
            mysql.connection.rollback() # 'views' artışını geri al
            return jsonify({"success": False, "message": "Konu bulunamadı."}), 404
            
        cur.execute("SELECT COUNT(id) AS total FROM forum_posts WHERE thread_id = %s", (thread_id,))
        total_items = cur.fetchone()['total']
        total_pages = math.ceil(total_items / limit)
        
        cur.execute("""
            SELECT 
                p.id, p.content, p.created_at,
                p.is_edited, p.edited_at, -- YENİ: Düzenlenme bilgisi
                p.user_id,
                u.name AS author_name,
                u.profile_image_url AS author_image,
                (SELECT COUNT(id) FROM forum_posts WHERE user_id = p.user_id) AS author_post_count,
                COUNT(DISTINCT l.id) AS like_count, -- YENİ: Toplam beğeni sayısı
                CASE WHEN ul.user_id IS NOT NULL THEN true ELSE false END AS has_liked -- YENİ: Bu kullanıcı beğenmiş mi?
            FROM forum_posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN forum_post_likes l ON p.id = l.post_id -- Toplam beğeni için
            LEFT JOIN forum_post_likes ul ON p.id = ul.post_id AND ul.user_id = %s -- Kullanıcının beğenisi için
            WHERE p.thread_id = %s
            GROUP BY p.id, u.id, ul.user_id -- YENİ: Group by'a eklendi
            ORDER BY p.created_at ASC
            LIMIT %s OFFSET %s
        """, (user_id, thread_id, limit, offset))
        
        posts = cur.fetchall()
        
        mysql.connection.commit() # 'views' artışını onayla
        cur.close()
        
        return jsonify({
            "success": True,
            "thread": thread_info,
            "posts": posts,
            "pagination": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": limit
            }
        }), 200

    except Exception as e:
        mysql.connection.rollback()
        return handle_db_error(e, "Gönderi listeleme")

@app.route('/api/forum/new-thread', methods=['POST'])
def create_forum_thread():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Konu açmak için giriş yapmalısınız."}), 401
        
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek."}), 400
        
    data = request.get_json()
    category_id = data.get('category_id')
    title = data.get('title')
    content = data.get('content')
    
    if not category_id or not title or not content:
        return jsonify({"success": False, "message": "Kategori, başlık ve içerik alanları zorunludur."}), 400
        
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            INSERT INTO forum_threads (category_id, user_id, title)
            VALUES (%s, %s, %s)
        """, (category_id, user_id, title))
        
        thread_id = cur.lastrowid
        
        cur.execute("""
            INSERT INTO forum_posts (thread_id, user_id, content)
            VALUES (%s, %s, %s)
        """, (thread_id, user_id, content))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "Konu başarıyla oluşturuldu!", "thread_id": thread_id}), 201

    except Exception as e:
        mysql.connection.rollback()
        return handle_db_error(e, "Yeni konu oluşturma")

@app.route('/api/forum/reply/<int:thread_id>', methods=['POST'])
def create_forum_reply(thread_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Cevap yazmak için giriş yapmalısınız."}), 401
        
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek."}), 400
        
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({"success": False, "message": "Cevap içeriği boş olamaz."}), 400
        
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT id FROM forum_threads WHERE id = %s", (thread_id,))
        thread = cur.fetchone()
        
        if not thread:
            cur.close()
            return jsonify({"success": False, "message": "Cevap yazılmak istenen konu bulunamadı."}), 404
            
        cur.execute("""
            INSERT INTO forum_posts (thread_id, user_id, content)
            VALUES (%s, %s, %s)
        """, (thread_id, user_id, content))
        
        cur.execute("""
            UPDATE forum_threads
            SET last_reply_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (thread_id,))
        
        limit = 10 # forum.html'deki JS ile aynı olmalı
        cur.execute("SELECT COUNT(id) AS total FROM forum_posts WHERE thread_id = %s", (thread_id,))
        total_posts = cur.fetchone()['total']
        go_to_page = math.ceil(total_posts / limit)
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({
            "success": True, 
            "message": "Cevap başarıyla eklendi!",
            "go_to_page": go_to_page # YENİ: JS'in kullanması için
        }), 201

    except Exception as e:
        mysql.connection.rollback()
        return handle_db_error(e, "Cevap yazma")

@app.route('/api/forum/post/like', methods=['POST'])
def like_post():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Beğeni yapmak için giriş yapmalısınız."}), 401
        
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek."}), 400
        
    data = request.get_json()
    post_id = data.get('post_id')
    
    if not post_id:
        return jsonify({"success": False, "message": "Gönderi ID eksik."}), 400
        
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT id FROM forum_post_likes WHERE user_id = %s AND post_id = %s", (user_id, post_id))
        existing_like = cur.fetchone()
        
        has_liked = False
        
        if existing_like:
            cur.execute("DELETE FROM forum_post_likes WHERE id = %s", (existing_like['id'],))
            has_liked = False
        else:
            cur.execute("INSERT INTO forum_post_likes (user_id, post_id) VALUES (%s, %s)", (user_id, post_id))
            has_liked = True
            
        cur.execute("SELECT COUNT(id) AS total FROM forum_post_likes WHERE post_id = %s", (post_id,))
        like_count = cur.fetchone()['total']
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({
            "success": True,
            "has_liked": has_liked,
            "like_count": like_count
        }), 200

    except Exception as e:
        mysql.connection.rollback()
        return handle_db_error(e, "Gönderi beğenme")

@app.route('/api/forum/post/edit', methods=['POST'])
def edit_post():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Düzenleme yapmak için giriş yapmalısınız."}), 401
        
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek."}), 400
        
    data = request.get_json()
    post_id = data.get('post_id')
    content = data.get('content')
    
    if not post_id or not content:
        return jsonify({"success": False, "message": "Gönderi ID veya içerik eksik."}), 400
        
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("""
            UPDATE forum_posts 
            SET content = %s, is_edited = TRUE, edited_at = NOW() 
            WHERE id = %s AND user_id = %s
        """, (content, post_id, user_id))
        
        if cur.rowcount == 0:
            mysql.connection.rollback()
            cur.close()
            return jsonify({"success": False, "message": "Gönderi bulunamadı veya düzenleme yetkiniz yok."}), 403

        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "content": content}), 200

    except Exception as e:
        mysql.connection.rollback()
        return handle_db_error(e, "Gönderi düzenleme")

@app.route('/api/forum/post/delete/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Silme işlemi için giriş yapmalısınız."}), 401
        
    try:
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT thread_id, user_id FROM forum_posts WHERE id = %s", (post_id,))
        post = cur.fetchone()
        
        if not post:
            cur.close()
            return jsonify({"success": False, "message": "Gönderi bulunamadı."}), 404
            
        if post['user_id'] != user_id:
            cur.close()
            return jsonify({"success": False, "message": "Bu gönderiyi silme yetkiniz yok."}), 403
            
        thread_id = post['thread_id']
        
        cur.execute("""
            SELECT id FROM forum_posts 
            WHERE thread_id = %s 
            ORDER BY created_at ASC 
            LIMIT 1
        """, (thread_id,))
        first_post = cur.fetchone()
        
        action_taken = "post_deleted"
        
        if first_post['id'] == post_id:
            cur.execute("DELETE FROM forum_threads WHERE id = %s", (thread_id,))
            action_taken = "thread_deleted"
        else:
            cur.execute("DELETE FROM forum_posts WHERE id = %s", (post_id,))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "action": action_taken}), 200

    except Exception as e:
        mysql.connection.rollback()
        return handle_db_error(e, "Gönderi silme")


# ==================================================
# KULLANICI MESAJLAŞMA SİSTEMİ (ÖZELLİK 4)
#
# BU ÖZELLİĞİN ÇALIŞMASI İÇİN VERİTABANINIZA BU TABLOLARI EKLEMELİSİNİZ:
#
# CREATE TABLE conversations (
#   id INT AUTO_INCREMENT PRIMARY KEY,
#   listing_id INT,
#   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#   KEY listing_id_idx (listing_id),
#   CONSTRAINT fk_listing_id FOREIGN KEY (listing_id) REFERENCES motorcycles(id) ON DELETE SET NULL
# );
#
# CREATE TABLE conversation_participants (
#   id INT AUTO_INCREMENT PRIMARY KEY,
#   conversation_id INT NOT NULL,
#   user_id INT NOT NULL,
#   FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
#   FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
#   UNIQUE KEY unique_conversation_user (conversation_id, user_id)
# );
#
# CREATE TABLE messages (
#   id INT AUTO_INCREMENT PRIMARY KEY,
#   conversation_id INT NOT NULL,
#   sender_id INT NOT NULL,
#   content TEXT NOT NULL,
#   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#   is_read BOOLEAN DEFAULT FALSE,
#   FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
#   FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
# );
# ==================================================



@app.route('/admin')
def admin_panel():
    if not is_admin():
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect('/admin/login')
        
    common_data = get_user_common_data()
    return render_template('admin.html', **common_data)

@app.route('/admin/login')
def admin_login_page():
    common_data = get_user_common_data()
    
    if is_admin():
        return redirect('/admin')
        
    return render_template('adminlogin.html', **common_data)

@app.route('/api/admin/login', methods=['POST'])
def admin_login_api():
    if not request.is_json:
        return jsonify({"success": False, "message": "Geçersiz istek: JSON bekleniyordu."}), 400

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "E-posta ve şifre alanları zorunludur."}), 400

    try:
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT id, name, password_hash, role FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        
        if user and check_password_hash(user['password_hash'], password):
            if user.get('role') == 'admin':
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_role'] = 'admin'
                
                return jsonify({
                    "success": True, 
                    "message": "Admin girişi başarılı. Yönlendiriliyorsunuz...",
                    "redirect_url": "/admin" # Admin paneline yönlendir
                }), 200
            else:
                return jsonify({"success": False, "message": "Bu hesaba admin yetkisi atanmamış."}), 403
        else:
            return jsonify({"success": False, "message": "E-posta veya şifre hatalı."}), 401

    except Exception as e:
        print(f"Admin giriş hatası: {e}")
        if '1054' in str(e) and 'role' in str(e):
            return jsonify({"success": False, "message": "Veritabanı hatası: 'users.role' sütunu bulunamadı."}), 500
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# --- Admin Gösterge Paneli (Dashboard) ---

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """
    Admin panelinin (Gösterge Paneli) ihtiyaç duyduğu tüm
    istatistik, grafik ve tablo verilerini döndürür.
    """
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    try:
        cur = mysql.connection.cursor()
        
        # --- 1. İstatistik Kartları ---
        cur.execute("SELECT COUNT(id) AS total FROM users")
        total_users = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(id) AS total FROM motorcycles")
        total_listings = cur.fetchone()['total']

        cur.execute("SELECT SUM(total_amount) AS total FROM orders WHERE status = 'Completed'")
        total_sales_data = cur.fetchone()
        total_sales = total_sales_data['total'] if total_sales_data['total'] else 0

        # Sütun adları büyük harfle düzeltildi
        cur.execute("SELECT COUNT(id) AS total FROM auctions WHERE Status = 'active' AND End_time > NOW()")
        active_auctions = cur.fetchone()['total']

        cur.execute("SELECT COUNT(id) AS total FROM orders WHERE status = 'Pending Payment'")
        pending_orders = cur.fetchone()['total']

        stats = {
            "total_users": total_users,
            "total_listings": total_listings,
            "total_sales": f"₺{total_sales:,.0f}", # Formatlayıp gönder
            "active_auctions": active_auctions,
            "pending_orders": pending_orders
        }

        # --- 2. Grafikler (GERÇEK VERİ) ---
        
        # Kullanıcı Grafiği (Son 7 gün)
        today = datetime.now()
        user_data_map = {}
        user_chart_labels = []
        
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            user_data_map[day_str] = 0 
            day_name_tr = ['Pzt', 'Salı', 'Çar', 'Per', 'Cuma', 'Cmt', 'Paz'][day.weekday()]
            user_chart_labels.append(day_name_tr)
            
        cur.execute("""
            SELECT DATE_FORMAT(created_at, %s) AS gun, COUNT(id) AS sayi
            FROM users WHERE created_at >= %s GROUP BY gun
        """, ('%Y-%m-%d', (today - timedelta(days=6)).strftime('%Y-%m-%d')))
        
        db_user_data = cur.fetchall()
        
        for row in db_user_data:
            if row['gun'] in user_data_map:
                user_data_map[row['gun']] = int(row['sayi'])

        user_chart_data = list(user_data_map.values())

        user_chart = {
            "labels": user_chart_labels,
            "data": user_chart_data 
        }

        # Satış Grafiği (Son 4 Hafta)
        sales_data_map = {}
        sales_chart_labels = []
        
        for i in range(3, -1, -1):
            week_start_day = (today - timedelta(days=today.weekday())) - timedelta(weeks=i)
            week_num = week_start_day.isocalendar()[1]
            label = f"Hafta {week_num}"
            sales_chart_labels.append(label)
            map_key = week_start_day.strftime('%Y-%V')
            sales_data_map[map_key] = 0.0
        
        cur.execute("""
            SELECT DATE_FORMAT(created_at, %s) AS hafta_key, SUM(total_amount) AS toplam
            FROM orders WHERE status = 'Completed' AND created_at >= %s GROUP BY hafta_key
        """, ('%Y-%V', (today - timedelta(weeks=4)).strftime('%Y-%m-%d')))
        
        db_sales_data = cur.fetchall()
        
        for row in db_sales_data:
            if row['hafta_key'] in sales_data_map:
                sales_data_map[row['hafta_key']] = float(row['toplam']) if row['toplam'] else 0.0

        sales_chart_data = list(sales_data_map.values())

        sales_chart = {
            "labels": sales_chart_labels,
            "data": sales_chart_data
        }
        
        # İlan Durumları (Pie)
        cur.execute("""
            SELECT 
                CASE 
                    WHEN status = 'Satıldı' THEN 'Satıldı'
                    WHEN category = 'Kiralık' THEN 'Kiralık'
                    ELSE 'Aktif Satılık'
                END AS status_group,
                COUNT(id) AS count
            FROM motorcycles GROUP BY status_group
        """)
        listing_status_data = cur.fetchall()
        
        listing_status_chart = {
            "labels": [row['status_group'] for row in listing_status_data],
            "data": [int(row['count']) for row in listing_status_data]
        }

        # --- 3. Son Aktiviteler Tabloları ---
        
        # Son Kayıtlar
        cur.execute("""
            SELECT name, email, created_at FROM users 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent_users = cur.fetchall()

        # YENİ: Son Siparişler (Dashboard için)
        cur.execute("""
            SELECT 
                o.id, o.total_amount, o.status, o.created_at,
                u.name AS user_name,
                m.title AS motorcycle_title
            FROM orders o
            JOIN users u ON o.user_id = u.id
            LEFT JOIN motorcycles m ON o.motorcycle_id = m.id
            ORDER BY o.created_at DESC
            LIMIT 5
        """)
        recent_orders = cur.fetchall()
        
        cur.close()

        return jsonify({
            "success": True,
            "stats": stats,
            "charts": {
                "users": user_chart,
                "sales": sales_chart,
                "listing_status": listing_status_chart
            },
            "tables": {
                "recent_users": recent_users,
                "recent_orders": recent_orders # YENİ EKLENDİ (Diğer tablolar kaldırıldı)
            }
        }), 200

    except Exception as e:
        print(f"Admin stats API hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# --- Kullanıcı Yönetimi Rotaları ---

@app.route('/admin/kullanici_yonetimi')
def admin_kullanici_page():
    """Admin Kullanıcı Yönetimi sayfasını render eder."""
    if not is_admin():
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect('/admin/login')

    common_data = get_user_common_data()
    return render_template('admin_kullanicilar.html', **common_data)

@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    """Admin paneli için tüm kullanıcıları listeler."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, name, email, phone, role, 'Active' as status 
            FROM users 
            ORDER BY id ASC
        """)
        users = cur.fetchall()
        cur.close()

        return jsonify({"success": True, "users": users}), 200

    except Exception as e:
        print(f"Admin kullanıcı listesi hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/admin/user/update_role', methods=['POST'])
def admin_update_user_role():
    """Bir kullanıcının rolünü günceller (admin/user)."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    if not request.is_json:
         return jsonify({"success": False, "message": "Geçersiz istek."}), 400

    data = request.get_json()
    user_id = data.get('user_id')
    new_role = data.get('new_role')

    if not user_id or new_role not in ['admin', 'user']:
        return jsonify({"success": False, "message": "Geçersiz kullanıcı ID veya rol."}), 400

    if str(user_id) == str(session.get('user_id')):
        return jsonify({"success": False, "message": "Kendi rolünüzü değiştiremezsiniz."}), 403

    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        mysql.connection.commit()
        cur.close()

        return jsonify({"success": True, "message": "Kullanıcı rolü başarıyla güncellendi."}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin rol güncelleme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# --- İlan Yönetimi Rotaları ---

@app.route('/admin/ilan_yonetimi')
def admin_ilan_page():
    """Admin İlan Yönetimi sayfasını render eder."""
    if not is_admin():
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect('/admin/login')

    common_data = get_user_common_data()
    return render_template('admin_ilanlar.html', **common_data)

@app.route('/api/admin/listings', methods=['GET'])
def get_admin_listings():
    """Admin paneli için tüm ilanları listeler (FİLTRELİ)."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    try:
        # Filtre parametrelerini al
        title_filter = request.args.get('title')
        user_id_filter = request.args.get('user_id')
        status_filter = request.args.get('status')
        
        base_query = """
            SELECT m.*, u.name AS user_name
            FROM motorcycles m
            LEFT JOIN users u ON m.user_id = u.id
        """
        
        where_conditions = []
        params = []
        
        if title_filter:
            where_conditions.append("m.title LIKE %s")
            params.append(f"%{title_filter}%")
            
        if user_id_filter:
            try:
                int(user_id_filter)
                where_conditions.append("m.user_id = %s")
                params.append(user_id_filter)
            except ValueError:
                pass # Geçersiz ID'yi yoksay
                
        if status_filter and status_filter != 'Tümü':
            where_conditions.append("m.status = %s")
            params.append(status_filter)
            
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
            
        base_query += " ORDER BY m.created_at DESC"
        
        cur = mysql.connection.cursor()
        cur.execute(base_query, tuple(params))
        listings = cur.fetchall()
        cur.close()

        return jsonify({"success": True, "listings": listings}), 200

    except Exception as e:
        print(f"Admin ilan listesi hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/admin/listing/update_status', methods=['POST'])
def admin_update_listing_status():
    """Bir ilanın durumunu günceller (active, pending, Satıldı)."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    if not request.is_json:
         return jsonify({"success": False, "message": "Geçersiz istek."}), 400

    data = request.get_json()
    listing_id = data.get('listing_id')
    new_status = data.get('new_status')

    if not listing_id or not new_status:
        return jsonify({"success": False, "message": "Eksik bilgi: listing_id ve new_status gereklidir."}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE motorcycles SET status = %s WHERE id = %s", (new_status, listing_id))
        mysql.connection.commit()
        cur.close()

        return jsonify({"success": True, "message": "İlan durumu başarıyla güncellendi."}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin ilan durumu güncelleme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# ===== YENİ FONKSİYON (ÖZELLİK 5) - Admin İlan Ekleme Sayfası =====
@app.route('/admin/ilan/yeni')
def admin_ilan_ekle_page():
    """Adminin yeni ilan eklemesi için formu render eder."""
    if not is_admin():
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect('/admin/login')
        
    common_data = get_user_common_data()
    return render_template('admin_ilan_ekle.html', **common_data)

# ===== YENİ FONKSİYON (ÖZELLİK 5) - Admin İlan Ekleme API =====
@app.route('/api/admin/listing/create', methods=['POST'])
def admin_create_listing():
    """Adminin yeni ilan oluşturmasını sağlar (ilanver'e benzer)."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 401
    
    try:
        # Admin formundan user_id'yi de al
        user_id = request.form.get('ad-user-id', type=int) 
        title = request.form.get('ad-title')
        brand = request.form.get('ad-brand')
        model = request.form.get('ad-model')
        year = request.form.get('ad-year', type=int)
        km = request.form.get('ad-km', type=int)
        condition = request.form.get('ad-condition')
        price = request.form.get('ad-price', type=Decimal)
        location = request.form.get('ad-location')
        description = request.form.get('ad-description')
        contact = request.form.get('ad-contact')
        category = request.form.get('ad-category') # Kiralık mı Satılık mı
        
        if not all([user_id, title, brand, model, year, km, condition, price, location, contact, category]):
             return jsonify({"success": False, "message": "Lütfen yıldızlı (*) tüm alanları doldurun (Kullanıcı ID dahil)."}), 400

        if 'ad-photos' not in request.files:
            return jsonify({"success": False, "message": "İlan fotoğrafı zorunludur."}), 400
            
        files = request.files.getlist('ad-photos')
        
        if not files or files[0].filename == '':
             return jsonify({"success": False, "message": "Lütfen en az bir fotoğraf seçin."}), 400
        
        file = files[0]
        image_url = None
        
        if file and allowed_file(file.filename):
            safe_title = re.sub(r'[^a-z0-9]', '_', title.lower())
            filename = f"user_{user_id}_{safe_title[:30]}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['LISTING_UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            image_url = f"/{filepath}"
        else:
            return jsonify({"success": False, "message": "Geçersiz dosya formatı."}), 400

        cur = mysql.connection.cursor()
        
        # Admin oluşturduğu için 'active' başlasın
        cur.execute("""
            INSERT INTO motorcycles (
                user_id, title, brand, model, year, km, `condition`, 
                price, location, description, contact_info, 
                image_url, category, status, created_at
            ) 
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, 
                %s, %s, 'active', NOW()
            )
        """, (
            user_id, title, brand, model, year, km, 
            'Sıfır' if condition == 'new' else 'İkinci El',
            price, location, description, contact,
            image_url,
            category # Kiralık veya Satılık
        ))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "İlan admin tarafından başarıyla oluşturuldu!"}), 201

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin ilan oluşturma hatası: {e}")
        if '1452' in str(e): # Foreign Key constraint fails (user_id)
            return jsonify({"success": False, "message": f"Kullanıcı ID hatası: Girdiğiniz '{user_id}' ID'sine sahip bir kullanıcı bulunamadı."}), 400
        return jsonify({"success": False, "message": f"Sunucu hatası: {e}"}), 500

# ===== YENİ FONKSİYON (ÖZELLİK 1) - Admin İlan Düzenleme Sayfası =====
@app.route('/admin/ilan/duzenle/<int:listing_id>')
def admin_ilan_duzenle_page(listing_id):
    """Adminin ilanı düzenlemesi için formu render eder."""
    if not is_admin():
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect('/admin/login')
        
    common_data = get_user_common_data()
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM motorcycles WHERE id = %s", (listing_id,))
        listing_data = cur.fetchone()
        cur.close()
        
        if not listing_data:
            flash("Düzenlenecek ilan bulunamadı.", "error")
            return redirect('/admin/ilan_yonetimi')
            
        return render_template('admin_ilan_duzenle.html', **common_data, listing=listing_data)
        
    except Exception as e:
        print(f"İlan düzenleme sayfası hatası: {e}")
        flash(f"Hata: {e}", "error")
        return redirect('/admin/ilan_yonetimi')

# ===== YENİ FONKSİYON (ÖZELLİK 1) - Admin İlan Güncelleme API =====
@app.route('/api/admin/listing/update/<int:listing_id>', methods=['POST'])
def admin_update_listing(listing_id):
    """Adminin bir ilanı güncellemesini sağlar."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 401
    
    try:
        # Formdan tüm verileri al
        user_id = request.form.get('ad-user-id', type=int) 
        title = request.form.get('ad-title')
        brand = request.form.get('ad-brand')
        model = request.form.get('ad-model')
        year = request.form.get('ad-year', type=int)
        km = request.form.get('ad-km', type=int)
        condition = request.form.get('ad-condition')
        price = request.form.get('ad-price', type=Decimal)
        location = request.form.get('ad-location')
        description = request.form.get('ad-description')
        contact = request.form.get('ad-contact')
        category = request.form.get('ad-category')
        
        if not all([user_id, title, brand, model, year, km, condition, price, location, contact, category]):
             return jsonify({"success": False, "message": "Lütfen yıldızlı (*) tüm alanları doldurun."}), 400

        image_url = None
        # Yeni bir fotoğraf yüklendiyse onu işle
        if 'ad-photos' in request.files:
            files = request.files.getlist('ad-photos')
            if files and files[0].filename != '':
                file = files[0]
                if allowed_file(file.filename):
                    safe_title = re.sub(r'[^a-z0-9]', '_', title.lower())
                    filename = f"user_{user_id}_{safe_title[:30]}_{secure_filename(file.filename)}"
                    filepath = os.path.join(app.config['LISTING_UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    image_url = f"/{filepath}"
                else:
                    return jsonify({"success": False, "message": "Yeni fotoğraf geçersiz formatta."}), 400
        
        cur = mysql.connection.cursor()
        
        if image_url:
            # Fotoğraf güncellendiyse
            cur.execute("""
                UPDATE motorcycles SET
                user_id = %s, title = %s, brand = %s, model = %s, year = %s, km = %s, 
                `condition` = %s, price = %s, location = %s, description = %s, 
                contact_info = %s, category = %s, image_url = %s
                WHERE id = %s
            """, (
                user_id, title, brand, model, year, km, 
                'Sıfır' if condition == 'new' else 'İkinci El',
                price, location, description, contact, category,
                image_url,
                listing_id
            ))
        else:
            # Fotoğraf güncellenmediyse
            cur.execute("""
                UPDATE motorcycles SET
                user_id = %s, title = %s, brand = %s, model = %s, year = %s, km = %s, 
                `condition` = %s, price = %s, location = %s, description = %s, 
                contact_info = %s, category = %s
                WHERE id = %s
            """, (
                user_id, title, brand, model, year, km, 
                'Sıfır' if condition == 'new' else 'İkinci El',
                price, location, description, contact, category,
                listing_id
            ))

        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "İlan başarıyla güncellendi!"}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin ilan güncelleme hatası: {e}")
        if '1452' in str(e): # Foreign Key constraint fails (user_id)
            return jsonify({"success": False, "message": f"Kullanıcı ID hatası: Girdiğiniz '{user_id}' ID'sine sahip bir kullanıcı bulunamadı."}), 400
        return jsonify({"success": False, "message": f"Sunucu hatası: {e}"}), 500

@app.route('/api/admin/listing/delete/<int:listing_id>', methods=['DELETE'])
def admin_delete_listing(listing_id):
    """Admin'in bir ilanı silmesini sağlar."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM motorcycles WHERE id = %s", (listing_id,))
        mysql.connection.commit()

        if cur.rowcount == 0:
            cur.close()
            return jsonify({"success": False, "message": "İlan bulunamadı."}), 404

        cur.close()
        return jsonify({"success": True, "message": "İlan başarıyla silindi."}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin ilan silme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# --- İhale Yönetimi Rotaları ---

# ===== YENİ FONKSİYON 1 (Sayfayı Göster) =====
@app.route('/admin/ihale/yeni')
def admin_ihale_ekle_page():
    """Admin Yeni İhale Ekleme form sayfasını render eder."""
    if not is_admin():
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect('/admin/login')

    common_data = get_user_common_data()
    
    # === Hata 1364 Çözümü: Motosikletleri Çek ===
    motorcycles = []
    try:
        cur = mysql.connection.cursor()
        # Sadece satılık ve aktif olan (henüz satılmamış) motosikletleri çek
        cur.execute("""
            SELECT id, title FROM motorcycles 
            WHERE category = 'Satılık' AND status = 'active'
                    AND id NOT IN (
                SELECT DISTINCT motorcycle_id FROM auctions 
                WHERE Status = 'active' AND motorcycle_id IS NOT NULL
            )
            ORDER BY title ASC
        """)
        motorcycles = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"İhale için motosiklet listesi çekme hatası: {e}")
        flash("İhaleye uygun motosiklet listesi çekilemedi.", "error")
    # === /Hata 1364 Çözümü ===
        
    # Yeni oluşturduğumuz HTML dosyasını göster ve motor listesini yolla
    return render_template('admin_ihale_ekle.html', **common_data, motorcycles=motorcycles)

# ===== YENİ FONKSİYON 2 (Formu İşle) =====
@app.route('/admin/ihale/ekle', methods=['POST']) # <--- BU SATIRI DEĞİŞTİRİYORUZ
def admin_create_auction():
    """Adminin yeni bir ihale oluşturmasını sağlar."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    try:
        # 1. Formdan verileri al
        title = request.form.get('title')
        description = request.form.get('description')
        starting_price = request.form.get('starting_price', type=Decimal)
        min_increment = request.form.get('min_increment', type=Decimal)
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        motorcycle_id = request.form.get('motorcycle_id', type=int) # Hata 1364 için eklendi

        # 2. Zorunlu alanları kontrol et
        if not all([title, starting_price, min_increment, start_time_str, end_time_str, motorcycle_id]): # motorcycle_id eklendi
             return jsonify({"success": False, "message": "Lütfen yıldızlı (*) tüm alanları doldurun (Motosiklet seçimi dahil)."}), 400

        # 3. Fotoğrafı işle
        if 'image' not in request.files:
            return jsonify({"success": False, "message": "İhale fotoğrafı zorunludur."}), 400
            
        file = request.files['image']
        
        if file.filename == '':
             return jsonify({"success": False, "message": "Lütfen bir fotoğraf seçin."}), 400
        
        image_url = None
        if file and allowed_file(file.filename):
            filename = f"auction_{secure_filename(title[:20])}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['LISTING_UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            image_url = f"/{filepath}" # /static/uploads/listings/...
        else:
            return jsonify({"success": False, "message": "Geçersiz dosya formatı. Lütfen 'png', 'jpg', 'jpeg' veya 'webp' kullanın."}), 400
        
        # 4. Tarih formatlarını veritabanına uygun hale getir (YYYY-MM-DD HH:MM:SS)
        try:
            start_time = datetime.fromisoformat(start_time_str).strftime('%Y-%m-%d %H:%M:%S')
            end_time = datetime.fromisoformat(end_time_str).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"success": False, "message": "Geçersiz tarih formatı."}), 400

        # 5. Veritabanına kaydet
        # DÜZELTME: Sütun adları (Start_price vb.) ve motorcycle_id eklendi
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO auctions (
                motorcycle_id, 
                title, description, Start_price, Current_price, Min_increment, 
                Start_time, End_time, image_url, 
                Status, Created_at
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW())
        """, (
            motorcycle_id, 
            title, description, starting_price, 
            starting_price, # Current_price, başlangıç fiyatı ile aynı başlar
            min_increment, 
            start_time, end_time, image_url
        ))
        mysql.connection.commit()
        cur.close()

        return jsonify({"success": True, "message": "İhale başarıyla oluşturuldu!"}), 201

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin ihale oluşturma hatası: {e}")
        if '1054' in str(e): # Bilinmeyen sütun
             return jsonify({"success": False, "message": f"Veritabanı hatası: {e}. 'auctions' tablosunda sütun adı hatası (Büyük/küçük harf?)."}), 500
        if '1364' in str(e): # Varsayılan değer yok
            return jsonify({"success": False, "message": f"Veritabanı hatası: {e}. Muhtemelen 'motorcycle_id' eksik."}), 500
        return jsonify({"success": False, "message": f"Sunucu hatası: {e}"}), 500


@app.route('/admin/ihale_yonetimi')
def admin_ihale_page():
    """Admin İhale Yönetimi sayfasını render eder."""
    if not is_admin():
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect('/admin/login')

    common_data = get_user_common_data()
    return render_template('admin_ihaleler.html', **common_data)

@app.route('/api/admin/auctions', methods=['GET'])
def get_admin_auctions():
    """Admin paneli için tüm ihaleleri listeler."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    try:
        cur = mysql.connection.cursor()
        # DÜZELTME: Sütun adları büyük harfle düzeltildi
        cur.execute("""
            SELECT a.*, 
                   a.Current_price as current_price, 
                   a.End_time as end_time, 
                   a.Status as status,
                   u.name AS highest_bidder_name
            FROM auctions a
            LEFT JOIN users u ON a.Highest_bidder_id = u.id
            ORDER BY a.Created_at DESC
        """)
        auctions = cur.fetchall()
        cur.close()

        return jsonify({"success": True, "auctions": auctions}), 200

    except Exception as e:
        print(f"Admin ihale listesi hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/admin/auction/update_status', methods=['POST'])
def admin_update_auction_status():
    """Bir ihalenin durumunu günceller (active, ended, cancelled)."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    if not request.is_json:
         return jsonify({"success": False, "message": "Geçersiz istek."}), 400

    data = request.get_json()
    auction_id = data.get('auction_id')
    new_status = data.get('new_status')

    if not auction_id or new_status not in ['active', 'ended', 'cancelled']:
        return jsonify({"success": False, "message": "Eksik bilgi veya geçersiz durum."}), 400

    try:
        cur = mysql.connection.cursor()
        # DÜZELTME: Sütun adı büyük harfle düzeltildi
        cur.execute("UPDATE auctions SET Status = %s WHERE id = %s", (new_status, auction_id))
        mysql.connection.commit()
        cur.close()

        return jsonify({"success": True, "message": "İhale durumu başarıyla güncellendi."}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin ihale durumu güncelleme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/admin/auction/delete/<int:auction_id>', methods=['DELETE'])
def admin_delete_auction(auction_id):
    """Admin'in bir ihaleyi (ve ilgili teklifleri) silmesini sağlar."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM bids WHERE auction_id = %s", (auction_id,))
        cur.execute("DELETE FROM auctions WHERE id = %s", (auction_id,))
        mysql.connection.commit()

        if cur.rowcount == 0:
            cur.close()
            return jsonify({"success": False, "message": "İhale bulunamadı."}), 404

        cur.close()
        return jsonify({"success": True, "message": "İhale ve ilgili teklifler başarıyla silindi."}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin ihale silme hatası: {e}")
        if '1451' in str(e):
            return jsonify({"success": False, "message": f"Veritabanı hatası: Bu ihale silinemedi (ilişkili veriler mevcut). Hata: {e}"}), 500
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# --- SİPARİŞ YÖNETİMİ ROTLARI ---

@app.route('/admin/siparis_yonetimi')
def admin_siparis_page():
    """Admin Sipariş Yönetimi sayfasını render eder."""
    if not is_admin():
        flash("Bu sayfaya erişim yetkiniz yok.", "error")
        return redirect('/admin/login')

    common_data = get_user_common_data()
    return render_template('admin_siparisler.html', **common_data)

@app.route('/api/admin/orders', methods=['GET'])
def get_admin_orders():
    """Admin paneli için tüm siparişleri listeler."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT 
                o.*, 
                m.title AS motorcycle_title
            FROM orders o
            LEFT JOIN motorcycles m ON o.motorcycle_id = m.id
            ORDER BY o.created_at DESC
        """)
        orders = cur.fetchall()
        cur.close()

        return jsonify({"success": True, "orders": orders}), 200

    except Exception as e:
        print(f"Admin sipariş listesi hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/admin/order/update_status', methods=['POST'])
def admin_update_order_status():
    """Bir siparişin durumunu günceller."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    if not request.is_json:
         return jsonify({"success": False, "message": "Geçersiz istek."}), 400

    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('new_status')

    if not order_id or new_status not in ['Pending Payment', 'Completed', 'Cancelled']:
        return jsonify({"success": False, "message": "Eksik bilgi veya geçersiz durum."}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
        mysql.connection.commit()
        cur.close()

        return jsonify({"success": True, "message": "Sipariş durumu başarıyla güncellendi."}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin sipariş durumu güncelleme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

@app.route('/api/admin/order/delete/<int:order_id>', methods=['DELETE'])
def admin_delete_order(order_id):
    """Admin'in bir siparişi silmesini sağlar."""
    if not is_admin():
        return jsonify({"success": False, "message": "Yetkisiz erişim."}), 403

    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))
        mysql.connection.commit()

        if cur.rowcount == 0:
            cur.close()
            return jsonify({"success": False, "message": "Sipariş bulunamadı."}), 404

        cur.close()
        return jsonify({"success": True, "message": "Sipariş başarıyla silindi."}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Admin sipariş silme hatası: {e}")
        return jsonify({"success": False, "message": f"Veritabanı hatası: {e}"}), 500

# ==================================================
# CHATBOT VE FALLBACK ROTLARI
# ==================================================

def get_fallback_response(user_prompt, history):
    prompt = user_prompt.lower()
    prompt = re.sub(r'[^\w\s]', '', prompt) # Noktalamaları kaldır
    
    greetings = ['merhaba', 'selam', 'hey', 'meraba', 'mrb', 'slm', 'naber']
    if any(word in prompt for word in greetings):
        if len(history) < 2: # Bu ilk mesajıysa
             return "Merhaba! Ben MotoAsistan. Size motosikletler, ihaleler veya kiralama konusunda nasıl yardımcı olabilirim?"
        else:
             return "Tekrar merhaba! Başka bir sorunuz var mı?"

    if 'ihale' in prompt:
        return "İhaleler sayfamızda aktif tüm açık artırmaları görebilirsiniz. En yakın tarihli ihaleyi ana sayfamızdaki 'Açık Artırmada' bölümünde bulabilirsiniz. Sizi /ihale sayfasına yönlendiriyorum."
    
    if 'kirala' in prompt or 'kiralık' in prompt:
        return "Motosiklet kiralamak çok kolay! Ana sayfamızdaki 'Günlük Heyecan' bölümünden veya 'İlanlar' sayfasından kiralık motorları filtreleyebilirsiniz. Beğendiğiniz motorun detaylarına gidip tarih seçerek kiralayabilirsiniz."
    
    if 'satılık' in prompt or 'satın al' in prompt or 'satınal' in prompt:
        return "Harika bir karar! 'Sıcak Satışlar' veya 'İlanlar' bölümünden satılık motosikletlerimize bakabilirsiniz. Beğendiğiniz modelin detay sayfasından 'Hemen Satın Al' butonuna tıklayarak işlemi başlatabilirsiniz."

    if 'teşekkür' in prompt or 'tşk' in prompt or 'sağ ol' in prompt:
        return "Rica ederim! Başka sorularınız varsa çekinmeyin."

    if 'nasıl' in prompt and ('çalışır' in prompt or 'kiralarım' in prompt or 'alırım' in 'prompt'):
        return "Sistemimiz çok basit: 1. Tutkunu Seç (Beğendiğin motoru bul). 2. Rezervasyon Yap (Güvenli ödeme ile tamamla). 3. Sürüşe Başla! Detaylar için ana sayfamızdaki '3 Adımda Aşka Başla' bölümüne bakabilirsiniz."
    
    if 'forum' in prompt:
        return "Topluluk forumumuzda diğer motosiklet tutkunlarıyla sohbet edebilirsiniz! Sizi /forum sayfasına yönlendiriyorum."

    fallback_responses = [
        "Üzgünüm, bu konuyu tam olarak anlayamadım. Kiralama, satılık motorlar veya ihaleler hakkında soru sormayı deneyebilirsiniz.",
        "Hmm, bu sorunun cevabını henüz bilmiyorum. Size ilanlar veya ihaleler hakkında bilgi verebilirim.",
        "Bu konuda size yardımcı olamıyorum. Lütfen sorunuzu farklı bir şekilde sormayı deneyin. Örneğin: 'Kiralık motorlar nerede?'"
    ]
    return fallback_responses[len(history) % len(fallback_responses)]


def get_bot_response(user_prompt, history):
    try:
        
        system_prompt = (
            "Sen, MotoLove adlı bir motosiklet sitesinde yer alan dost canlısı ve sohbet etmeyi seven bir yapay zeka asistanısın. "
            "Kullanıcılarla her konuda (sadece motosiklet değil) samimi bir şekilde sohbet edebilirsin. 'Naber', 'nasılsın' gibi sorulara doğal cevaplar ver. "
            "Motosikletler hakkında spesifik bütçe veya model soruları sorarlarsa (örn: '40 bine motor var mı?'), "
            "elinde güncel bir veritabanı listesi olmadığını, bu yüzden net bir model öneremeyeceğini, "
            "ancak genel bilgi verebileceğini veya en doğru bilgi için /ilanlar ve /ihale sayfalarına bakmalarını önerebileceğini belirt. "
            "Ana hedefin kurallara bağlı kalmadan, akıcı ve doğal bir sohbet sürdürmek."
        )
        
        gemini_history = []
        for item in history:
            role = "user" if item["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [{"text": item["message"]}]})
        
        payload = {
            "contents": gemini_history, 
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.9, 
                "topP": 0.9,
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        
        with httpx.Client(timeout=20.0) as client:
            response = client.post(GEMINI_API_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            
            if not result.get('candidates'):
                print(f"Gemini API'den 'candidates' olmadan cevap alındı (örn: Güvenlik filtresi): {result}")
                return "Üzgünüm, bu isteğinize şu anda yanıt veremiyorum. Lütfen farklı bir soru sorun."

            try:
                text = result['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError, TypeError):
                text = '' # Boş cevap
            
            if text:
                return text
            else:
                print(f"Gemini API'den boş cevap alındı: {result}")
                return get_fallback_response(user_prompt, history)
        else:
            print(f"Gemini API Hatası: {response.status_code} - {response.text}")
            return get_fallback_response(user_prompt, history)

    except httpx.ConnectError as e:
        print(f"Gemini API'ye bağlanırken hata oluştu (Sunucu kapalı olabilir): {e}")
        return "Bağlantı hatası yaşıyorum. Lütfen daha sonra tekrar deneyin."
    except Exception as e:
        print(f"Yapay zeka çağrılırken istisna oluştu: {e}")
        return get_fallback_response(user_prompt, history)


@app.route('/api/chat', methods=['POST'])
def api_chat():
    if not request.is_json:
        return jsonify({"error": "Geçersiz istek: JSON bekleniyordu."}), 400
        
    data = request.get_json()
    prompt = data.get('prompt')
    
    if not prompt:
        return jsonify({"error": "Geçersiz istek: 'prompt' alanı eksik."}), 400
        
    try:
        chat_history = session.get('chat_history', [])
        
        chat_history.append({"role": "user", "message": prompt})
        
        bot_response = get_bot_response(prompt, chat_history)
        
        chat_history.append({"role": "bot", "message": bot_response})
        
        session['chat_history'] = chat_history[-10:]
        
        return jsonify({"reply": bot_response}), 200
        
    except Exception as e:
        print(f"Sohbet API hatası: {e}")
        return jsonify({"error": "Sunucuda bir hata oluştu."}), 500


# ==================================================
# MESAJLAŞMA API ROTLARI
# ==================================================


@app.route('/api/messages/conversations', methods=['GET'])
def get_conversations_api():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapmalısınız.'}), 401
    
    user_id = session['user_id']
    try:
        cur = mysql.connection.cursor()
        query = """
            SELECT 
                c.id as conversation_id,
                CASE 
                    WHEN c.user_one_id = %s THEN u2.name 
                    ELSE u1.name 
                END as other_user_name,
                CASE 
                    WHEN c.user_one_id = %s THEN u2.profile_image_url 
                    ELSE u1.profile_image_url 
                END as other_user_image,
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
        cur.execute(query, (user_id, user_id, user_id, user_id, user_id))
        conversations = cur.fetchall()
        cur.close()
        
        return jsonify({'success': True, 'conversations': conversations})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Konuşmaları getirme hatası: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/messages/conversation/<int:conversation_id>', methods=['GET'])
def get_conversation_messages(conversation_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapmalısınız.'}), 401
        
    user_id = session['user_id']
    try:
        cur = mysql.connection.cursor()
        
        # Security check: User must be part of conversation
        cur.execute("SELECT * FROM conversations WHERE id = %s AND (user_one_id = %s OR user_two_id = %s)", (conversation_id, user_id, user_id))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'Yetkisiz erişim.'}), 403
            
        cur.execute("""
            SELECT id, sender_id, receiver_id, content, created_at, is_read 
            FROM messages 
            WHERE conversation_id = %s 
            ORDER BY created_at ASC
        """, (conversation_id,))
        messages = cur.fetchall()
        
        # Mark as read
        cur.execute("UPDATE messages SET is_read = TRUE WHERE conversation_id = %s AND receiver_id = %s", (conversation_id, user_id))
        mysql.connection.commit()
        
        cur.close()
        return jsonify({'success': True, 'messages': messages})
        
    except Exception as e:
        print(f"Mesaj detay hatası: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

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
        
        # Find receiver_id from conversation
        cur.execute("SELECT user_one_id, user_two_id FROM conversations WHERE id = %s", (conversation_id,))
        conv = cur.fetchone()
        
        if not conv:
             return jsonify({'success': False, 'message': 'Konuşma bulunamadı.'}), 404
             
        receiver_id = conv['user_two_id'] if int(conv['user_one_id']) == int(sender_id) else conv['user_one_id']

        cur.execute("""
            INSERT INTO messages (conversation_id, sender_id, receiver_id, content, created_at, is_read)
            VALUES (%s, %s, %s, %s, NOW(), FALSE)
        """, (conversation_id, sender_id, receiver_id, content))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})

    except Exception as e:
        print(f"Mesaj gönderme hatası: {e}")
        return jsonify({'success': False, 'message': 'Mesaj gönderilemedi.'}), 500


if __name__ == '__main__':
   
    app.run(host='0.0.0.0', debug=True)
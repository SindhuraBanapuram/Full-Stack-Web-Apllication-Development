from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from apscheduler.jobstores.base import ConflictingIdError
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_ADDED, EVENT_JOB_REMOVED
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import sqlite3
import logging
import os
os.environ['TZ'] = 'UTC'

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

REQUEST_TIMEOUT = 15 
PRICE_CHANGE_THRESHOLD = 0.01

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    wishlists = db.relationship('Wishlist', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    details = db.Column(db.String(500))
    url = db.Column(db.String(500), nullable=False)

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.String(100), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)

    def __init__(self, user_id, product_id, name, price, image_url):
        self.user_id = user_id
        self.product_id = product_id
        self.name = name
        self.price = price
        self.image_url = image_url

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    old_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Notification {self.id} - {self.product_name}>"

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(username=data['username'], email=data['email'], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter((User.email == data['identifier']) | (User.username == data['identifier'])).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({'token': access_token, 'username': user.username}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    if not products:
        print("No products found, scraping...")
        scrape_products()
        products = Product.query.all()
    return jsonify([{
        "id": p.id,
        "name": p.name,
        "price": p.price,
        "image_url": p.image_url,
        "url": p.url
    } for p in products])

wishlist = []

@app.route("/wishlist", methods=["POST"])
def add_to_wishlist():
    data = request.json 
    print("Received Wishlist Request:", data)
    
    if not data or "product_id" not in data:
        return jsonify({"error": "Invalid product data"}), 400

    existing_product = Wishlist.query.filter_by(product_id=data["product_id"]).first()
    if existing_product:
        return jsonify({"message": "Product already in wishlist"}), 400

    new_wishlist_item = Wishlist(
        user_id=1,
        product_id=data["product_id"],
        name=data["name"],
        price=data["price"],
        image_url=data["image_url"]
    )
    db.session.add(new_wishlist_item)
    db.session.commit()

    return jsonify({"message": "Product added to wishlist"}), 201

@app.route("/wishlist", methods=["GET"])
def get_wishlist():
    wishlist_items = Wishlist.query.all()
    
    return jsonify([
        {
            "product_id": item.product_id,
            "name": item.name,
            "price": item.price,
            "image_url": item.image_url
        }
        for item in wishlist_items
    ]), 200

@app.route('/wishlist/<product_id>', methods=['DELETE'])
def delete_from_wishlist(product_id):
    print(f"Trying to delete product_id: {product_id}")
    wishlist_item = Wishlist.query.filter_by(product_id=product_id).first()
    
    if not wishlist_item:
        print("Product not found in wishlist!") 
        return jsonify({"error": "Product not found"}), 404
    
    db.session.delete(wishlist_item)
    db.session.commit()

    return jsonify({"message": "Product removed from wishlist"})


@app.route('/notifications', methods=['GET'])
def get_notifications():
    try:
        notifications = Notification.query.order_by(Notification.timestamp.desc()).limit(50).all()
        
        return jsonify([{
            'id': n.id,
            'product_id': n.product_id,
            'product_name': n.product_name,
            'old_price': n.old_price,
            'new_price': n.new_price,
            'timestamp': n.timestamp.isoformat(),
            'read': n.read
        } for n in notifications]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    try:
        Notification.query.update({'read': True})
        db.session.commit()
        
        return jsonify({
            'message': 'All notifications marked as read',
            'count': Notification.query.count()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def scrape_products():
    print("Starting Amazon scrape...")
    try:
        URL = "https://www.amazon.com/s?k=phones&language=en_EN&crid=3A15I2OVN30B3&currency=INR&sprefix=phones%2Caps%2C384&ref=nb_sb_noss_1"
        HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US, en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'DNT': '1'
        }

        response = requests.get(URL, headers=HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch page (Status: {response.status_code})")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        products = []

        items = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        for item in items[:20]:
            try:
                title = item.find('h2').text.strip()
                
                price_whole = item.find('span', class_='a-price-whole')
                price_fraction = item.find('span', class_='a-price-fraction')
                price = float(f"{price_whole.text.replace(',','')}{price_fraction.text}" if price_whole and price_fraction else "0")
                
                image = item.find('img', class_='s-image')
                image_url = image['src'] if image else ""
                
                link = item.find('a', class_='a-link-normal')['href']
                product_url = f"https://www.amazon.com{link}" if not link.startswith('http') else link
                
                product = Product.query.filter_by(name=title).first()
                if product:
                    if product.price != price:
                        product.price = price
                        db.session.commit() 
                else:
                    product = Product(
                        name=title,
                        price=price,
                        image_url=image_url,
                        url=product_url
                    )
                    db.session.add(product)
                    db.session.commit()
                
                products.append({
                    'name': title,
                    'price': price,
                    'image_url': image_url,
                    'url': product_url
                })
                
            except Exception as e:
                print(f"Error processing product: {e}")
                continue

        print(f"Successfully scraped {len(products)} products")
        return products

    except Exception as e:
        print(f"Scraping failed: {e}")
        return []

def get_current_price(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9"
        }
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        price_whole = soup.find("span", class_="a-price-whole")
        price_fraction = soup.find("span", class_="a-price-fraction")
        
        return parse_amazon_price(price_whole, price_fraction)
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {url}: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Failed to get price from {url}: {str(e)}")
        return None

def notify_price_change(product, new_price):
    try:
        with app.app_context():
            notification = Notification(
                user_id=product.user_id,
                product_id=product.id,
                old_price=product.price,
                new_price=new_price
            )
            product.price = new_price
            product.last_updated = datetime.now(timezone.utc)
            db.session.add(notification)
            db.session.commit()
            logging.info(f"Price changed for product {product.id}: {product.price} -> {new_price}")
    except Exception as e:
        logging.error(f"Error saving notification: {str(e)}")

def clean_price_text(price_text):
    if not price_text:
        return None
    cleaned = re.sub(r'[^\d.]', '', price_text.strip())
    parts = cleaned.split('.')
    if len(parts) > 1:
        cleaned = f"{parts[0]}.{''.join(parts[1:])}"
    return cleaned if cleaned else None

def check_price_drops():
    with app.app_context():
        start_time = datetime.now(timezone.utc)
        logging.info(f"Starting price check at {start_time.isoformat()}")
        try:
            stale_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
            products_to_check = Product.query.filter(Product.last_updated < stale_threshold).limit(50).all()
            if not products_to_check:
                logging.info("No stale products found to check")
                return
            
            for product in products_to_check:
                try:
                    time.sleep(random.uniform(1, 3))
                    current_price = get_current_price(product.url)
                    if current_price is None:
                        continue
                    if abs(current_price - product.price) > (product.price * PRICE_CHANGE_THRESHOLD):
                        notify_price_change(product, current_price)
                except Exception as e:
                    logging.error(f"Error checking product {product.id}: {str(e)}")
        except Exception as e:
            logging.error(f"Price check job failed: {str(e)}", exc_info=True)
        finally:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logging.info(f"Price check completed in {duration:.2f} seconds")

def parse_amazon_price(price_whole, price_fraction):
    try:
        whole_cleaned = clean_price_text(price_whole.text if price_whole else "")
        fraction_cleaned = clean_price_text(price_fraction.text if price_fraction else "")
        if not whole_cleaned:
            return None
        price_str = whole_cleaned + (f".{fraction_cleaned[:2]}" if fraction_cleaned else "")
        return float(price_str) if re.match(r'^\d+\.?\d*$', price_str) else None
    except (AttributeError, ValueError, TypeError) as e:
        logging.error(f"Price parsing error: {str(e)}")
        return None

def create_scheduler():
    jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')}
    scheduler = BackgroundScheduler(jobstores=jobstores, timezone="UTC", job_defaults={'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 60})
    scheduler.add_job(func=check_price_drops, trigger='interval', minutes=30, id='price_check_job', replace_existing=True)
    return scheduler

def job_listener(event):
    if event.code == EVENT_JOB_ADDED:
        logging.info(f"Job added: {event.job_id}")
    elif event.code == EVENT_JOB_REMOVED:
        logging.info(f"Job removed: {event.job_id}")

scheduler = create_scheduler()
scheduler.add_listener(job_listener, EVENT_JOB_ADDED | EVENT_JOB_REMOVED)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.FileHandler('scheduler.log'), logging.StreamHandler()])
        scheduler = create_scheduler()
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            scheduler.start()
            logging.info("Scheduler started with jobs: %s", scheduler.get_jobs())
            try:
                app.run(debug=True, use_reloader=True)
            finally:
                scheduler.shutdown()
                logging.info("Scheduler shut down")
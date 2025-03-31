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
from functools import lru_cache
from threading import Timer
import sqlite3
import logging
import secrets
import sys
import traceback
import os
os.environ['TZ'] = 'UTC'

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = secrets.token_hex(32)
jwt = JWTManager(app)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

REQUEST_TIMEOUT = 15 
PRICE_CHANGE_THRESHOLD = 0.01
CHECK_INTERVAL_SECONDS = 60

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
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    old_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
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
@jwt_required()
def add_to_wishlist():
    data = request.json
    print("Received Wishlist Request:", data)

    if not data or "product_id" not in data:
        return jsonify({"error": "Invalid product data"}), 400

    user_id = get_jwt_identity() 

    existing_product = Wishlist.query.filter_by(user_id=user_id, product_id=data["product_id"]).first()
    if existing_product:
        return jsonify({"message": "Product already in wishlist"}), 400

    new_wishlist_item = Wishlist(
        user_id=user_id,
        product_id=data["product_id"],
        name=data["name"],
        price=data["price"],
        image_url=data["image_url"]
    )
    db.session.add(new_wishlist_item)
    db.session.commit()
    return jsonify({"message": "Product added to wishlist"}), 201
    product = Product.query.get(data["product_id"])
    if product:
        new_price = get_current_price(product.url)
        if new_price and new_price < product.price * (1 - PRICE_CHANGE_THRESHOLD):
            notification = Notification(
                user_id=new_wishlist_item.user_id,
                product_id=product.id,
                product_name=product.name,
                old_price=product.price,
                new_price=new_price,
                image_url=product.image_url
            )
            db.session.add(notification)
            product.price = new_price
            db.session.commit()

    Timer(5, check_price_drops).start()

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
    return jsonify({"message": "Notifications fetched successfully"}), 200
    notifications = Notification.query.order_by(Notification.timestamp.desc()).all()
    
    return jsonify([
        {
            "id": n.id,
            "user_id": n.user_id,
            "product_id": n.product_id,
            "product_name": n.product_name,
            "old_price": n.old_price,
            "new_price": n.new_price,
            "timestamp": n.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "image_url": n.image_url or "/placeholder-product.png"
        }
        for n in notifications
    ])


@app.route("/notifications", methods=["POST"])
def add_notification():
    try:
        data = request.json
        if not all(key in data for key in ["user_id", "product_id", "product_name", "old_price", "new_price"]):
            return jsonify({"error": "Missing required fields"}), 400

        new_notification = Notification(
            user_id=data["user_id"],
            product_id=data["product_id"],
            product_name=data["product_name"],
            old_price=data["old_price"],
            new_price=data["new_price"],
            image_url=data.get("image_url", "/placeholder-product.png"),
        )

        db.session.add(new_notification)
        db.session.commit()

        return jsonify({
            "id": new_notification.id,
            "user_id": new_notification.user_id,
            "product_id": new_notification.product_id,
            "product_name": new_notification.product_name,
            "old_price": new_notification.old_price,
            "new_price": new_notification.new_price,
            "timestamp": new_notification.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "image_url": new_notification.image_url
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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


@lru_cache(maxsize=100)
def get_current_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        price_element = soup.select_one("span.a-price-whole")
        return float(price_element.text.replace(",", "").strip()) if price_element else None
    except Exception as e:
        logging.error(f"Error fetching price: {e}")
        return None

def check_price_drops():
    with app.app_context():
        wishlist_items = Wishlist.query.all()
        for item in wishlist_items:
            product = Product.query.get(item.product_id)
            if product:
                new_price = get_current_price(product.url)
                if new_price and new_price < product.price * (1 - PRICE_CHANGE_THRESHOLD):
                    notification = Notification(
                        user_id=item.user_id,
                        product_id=product.id,
                        product_name=product.name,
                        old_price=product.price,
                        new_price=new_price,
                        image_url=product.image_url
                    )
                    db.session.add(notification)
                    product.price = new_price
                    db.session.commit()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_price_drops, 'interval', seconds=CHECK_INTERVAL_SECONDS, id='price_check_job')
    scheduler.start()

@app.before_request
def startup_function():
    db.create_all()
    start_scheduler()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, use_reloader=False)
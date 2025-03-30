from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import logging
from functools import lru_cache
import os

os.environ['TZ'] = 'UTC'

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = "super_secret_key"

jwt = JWTManager(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

PRICE_DROP_THRESHOLD = 0.10 
CHECK_INTERVAL_SECONDS = 10

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
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    last_checked = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    old_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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

@app.route('/wishlist', methods=['POST'])
@jwt_required()
def add_to_wishlist():
    data = request.json
    user_id = get_jwt_identity()
    
    if not data or "product_id" not in data:
        return jsonify({"error": "Invalid product data"}), 400

    existing_product = Wishlist.query.filter_by(user_id=user_id, product_id=data["product_id"]).first()
    if existing_product:
        return jsonify({"message": "Product already in wishlist"}), 400

    new_wishlist_item = Wishlist(user_id=user_id, product_id=data["product_id"], last_checked=datetime.utcnow())
    db.session.add(new_wishlist_item)
    db.session.commit()
    return jsonify({"message": "Product added to wishlist"}), 201

@app.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    notifications = Notification.query.filter_by(user_id=user_id).all()
    return jsonify([
        {
            "product_name": n.product_name,
            "old_price": n.old_price,
            "new_price": n.new_price,
            "timestamp": n.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        for n in notifications
    ]), 200

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
            current_time = datetime.utcnow()
            if (current_time - item.last_checked) >= timedelta(seconds=CHECK_INTERVAL_SECONDS):
                product = Product.query.get(item.product_id)
                if product:
                    new_price = get_current_price(product.url)
                    if new_price and new_price < product.price * (1 - PRICE_DROP_THRESHOLD):
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
                        item.last_checked = current_time
                        db.session.commit()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_price_drops, 'interval', seconds=CHECK_INTERVAL_SECONDS, id='price_check_job')
    scheduler.start()

@app.before_first_request
def initialize():
    db.create_all()
    start_scheduler()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, use_reloader=False)

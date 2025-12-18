from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt

db = SQLAlchemy()

wishlist_table = db.Table('wishlist',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'))
)

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    recovery_email = db.Column(db.String(200), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(30), default='student')
    profile_pic = db.Column(db.String(200), default='default.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', back_populates='user')
    wishlist = db.relationship('Book', secondary=wishlist_table, back_populates='wishlisted_by')

    def set_password(self, password: str):
        if isinstance(password, str):
            password = password.encode('utf-8')
        self.password_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str) -> bool:
        if isinstance(password, str):
            password = password.encode('utf-8')
        try:
            return bcrypt.checkpw(password, self.password_hash.encode('utf-8'))
        except Exception:
            return False

class Book(db.Model):
    __tablename__ = 'book'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    genre = db.Column(db.String(80), default='General')
    isbn = db.Column(db.String(80), nullable=True)
    price = db.Column(db.Float, default=0.0)
    total_copies = db.Column(db.Integer, default=0)
    available_copies = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', back_populates='book')
    wishlisted_by = db.relationship('User', secondary=wishlist_table, back_populates='wishlist')

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(30), default='pending')  # possible values: pending, approved, canceled, returned, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    returned_at = db.Column(db.DateTime, nullable=True)
    fine = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(50), nullable=True)  # e.g., 'stripe', 'paypal'
    payment_id = db.Column(db.String(255), nullable=True)  # Stripe session ID or PayPal transaction ID
    payment_status = db.Column(db.String(30), default='unpaid')  # unpaid, paid, failed

    user = db.relationship('User', back_populates='orders')
    book = db.relationship('Book', back_populates='orders')

class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='cart_items')
    book = db.relationship('Book', backref='cart_items')

class BookRequest(db.Model):
    __tablename__ = 'book_request'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(250), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    genre = db.Column(db.String(80), default='General')
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='book_requests')

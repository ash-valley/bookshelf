from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# ----------------------
# USER MODEL
# ----------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # relationships
    books = db.relationship('Book', backref='owner', lazy=True)
    quotes = db.relationship('Quote', backref='user', lazy=True)


# ----------------------
# BOOK MODEL
# ----------------------
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    author = db.Column(db.String(250))
    cover_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    status = db.Column(db.String(20))   # possible values: read / reading / to-read

    # relationship back to the owner (User)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # quotes that belong to this book
    quotes = db.relationship('Quote', backref='book', lazy=True)


# ----------------------
# QUOTE MODEL
# ----------------------
class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250))

    # which book the quote came from
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))

    # which user saved the quote
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
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

    theme = db.Column(db.String(20), default="spring")

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
    notes = db.Column(db.Text)
    status = db.Column(db.String(20))   # possible values: read / reading / to-read
    year = db.Column(db.String(10))
    genres = db.Column(db.String(500))

    position = db.Column(db.Integer, default=0)

    # relationship back to the owner (User)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # quotes that belong to this book
    quotes = db.relationship('Quote', backref='book', lazy=True)

    collections = db.relationship(
        "Collection",
        secondary="collection_book",
        backref="books_list",
        lazy="dynamic"
    )


# ----------------------
# COLLECTION MODEL
# ----------------------

class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    collection_entries = db.relationship(
        "CollectionBook",
        backref="collection",
        cascade="all, delete-orphan",
        order_by="CollectionBook.position"
    )

    @property
    def books(self):
        return [entry.book for entry in self.collection_entries]

class CollectionBook(db.Model):
    __tablename__ = "collection_book"   # NOTE: different from "collection_books"!

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey("collection.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    position = db.Column(db.Integer, nullable=True)

    # Relationship to Book
    book = db.relationship("Book", backref="collection_entries")


# ----------------------
# QUOTE MODEL
# ----------------------
class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    text = db.Column(db.Text, nullable=False)
    page = db.Column(db.String(50))
    tags = db.Column(db.String(250))      # comma-separated
    comment = db.Column(db.Text)          # your personal note

    # which book the quote came from
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))

    # which user saved the quote
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)




from flask import Flask, render_template
from dotenv import load_dotenv
import os

from models import db  # import your database object

load_dotenv()  # Load variables from .env


app = Flask(__name__)


# Read environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Initialize the database ---
db.init_app(app)

# --- Create tables (User, Book, Quote) ---
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/books')
def bookshelf():
    return render_template('bookshelf.html')


@app.route('/quotes')
def quotes():
    return render_template('quotes.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/register')
def register():
    return render_template('register.html')


if __name__ == '__main__':
    app.run(debug=True)
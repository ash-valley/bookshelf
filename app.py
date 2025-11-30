from flask import Flask, render_template, request, flash, redirect, url_for
from dotenv import load_dotenv
import os

from forms import RegistrationForm
from models import db, User  # import your database object
from werkzeug.security import generate_password_hash

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


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Check if username exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        
        # Check if email exists
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('register'))
        
        # Hash password
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        
        # Create new user object
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        
        # Save to database
        db.session.add(new_user)
        db.session.commit()
        
        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for('login'))


    return render_template('register.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, flash, redirect, url_for, get_flashed_messages, session
from flask_login import login_user, logout_user, login_required, LoginManager, current_user
from dotenv import load_dotenv
import os

from forms import RegistrationForm, LoginForm
from models import db, User, Book, Quote  # import your database object
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import date
import random

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

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:

        # --- Book & Quote counts ---
        book_count = len(current_user.books)
        quote_count = len(current_user.quotes)

        # --- Daily Quote (random from user) ---
        if current_user.quotes:
            # Seed randomness with today's date so it stays the same all day
            random.seed(date.today().toordinal())

            selected_quote = random.choice(current_user.quotes)
            daily_quote = selected_quote.text
        else:
            daily_quote = "Reading is dreaming with open eyes."

        # --- Featured Book (random) ---
        featured_book = None
        if current_user.books:
            featured_book = random.choice(current_user.books)

        # --- Recent Books (latest 3) ---
        recent_books = (
            Book.query.filter_by(user_id=current_user.id)
            .order_by(Book.id.desc())
            .limit(3)
            .all()
        )

        return render_template(
            'home.html',
            book_count=book_count,
            quote_count=quote_count,
            daily_quote=daily_quote,
            featured_book=featured_book,
            recent_books=recent_books
        )

    # not logged in
    return render_template('home.html')


@app.route('/library')
def library():
    books = Book.query.filter_by(user_id=current_user.id).all()

    return render_template('library.html', books=books)


@app.route('/quotes')
def quotes():
    return render_template('quotes.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    
    form = LoginForm()

    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("home"))  # Redirect to the main page
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


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
        hashed_password = generate_password_hash(form.password.data)

        # Create new user object
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        
        # Save to database
        db.session.add(new_user)
        db.session.commit()
        
        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for('login'))


    return render_template('register.html', form=form)


@app.route("/themes")
@login_required
def themes():
    return render_template("themes.html")


@app.route("/set-theme/<theme>", methods=["POST"])
@login_required
def set_theme(theme):
    if theme in ["spring", "midnight", "fireplace"]:
        current_user.theme = theme
        db.session.commit()        
    return ("", 204)


if __name__ == '__main__':
    app.run(debug=True)
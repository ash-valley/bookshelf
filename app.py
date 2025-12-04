from flask import Flask, render_template, request, flash, redirect, url_for, get_flashed_messages, session
from flask_login import login_user, logout_user, login_required, LoginManager, current_user
from dotenv import load_dotenv
import os

from forms import RegistrationForm, LoginForm
from models import db, User, Book, Quote  # import your database object
from werkzeug.security import generate_password_hash, check_password_hash
import requests 

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


@app.route('/search-books')
@login_required
def search_books():
    query = request.args.get('q')

    # If no search term given, just show an empty page
    if not query:
        return render_template('search_results.html', books=[])

    # Google Books API endpoint
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query, "maxResults": 10}

    response = requests.get(url, params=params)

    if response.status_code != 200:
        flash("Something went wrong while searching for books.", "danger")
        return render_template('search_results.html', books=[])

    data = response.json()

    books = []

    if "items" in data:
        for item in data["items"]:
            info = item.get("volumeInfo", {})

            published = info.get("publishedDate", "")
            year = published[:4] if len(published) >= 4 and published[:4].isdigit() else ""

            categories = info.get("categories", [])
            genres = ", ".join(categories) if categories else ""

            books.append({
                "id": item.get("id"),
                "title": info.get("title"),
                "authors": ", ".join(info.get("authors", [])),
                "description": info.get("description", ""),
                "thumbnail": info.get("imageLinks", {}).get("thumbnail"),
                "year": year,
                "genres": genres
            })


    return render_template("search_results.html", books=books, query=query)


@app.route('/add-to-library', methods=['POST'])
@login_required
def add_to_library():
    title = request.form.get("title")
    author = request.form.get("author")
    cover_url = request.form.get("cover_url")
    description = request.form.get("description")
    year = request.form.get("year")
    genres = request.form.get("genres")

    # Quick validation
    if not title:
        flash("Book must have a title.", "danger")
        return redirect(url_for('library'))

    # Create new Book object
    new_book = Book(
        title=title,
        author=author,
        cover_url=cover_url,
        description=description,
        year=year,
        genres=genres,
        status="to-read",  # Default status
        user_id=current_user.id
    )

    # Save to DB
    db.session.add(new_book)
    db.session.commit()

    flash(f'"{title}" added to your library!', "success")
    return redirect(url_for('library'))


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
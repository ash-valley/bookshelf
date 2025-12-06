from flask import Flask, render_template, request, flash, redirect, url_for, get_flashed_messages, session, jsonify
from flask_login import login_user, logout_user, login_required, LoginManager, current_user
from search_service import BookSearchService
from dotenv import load_dotenv
import os

from forms import RegistrationForm, LoginForm
from models import db, User, Book, Collection, Quote  
from werkzeug.security import generate_password_hash, check_password_hash
import requests 

from datetime import date
import random

load_dotenv()  


app = Flask(__name__)

BOOKS_PER_PAGE = 12


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
    # which "page" we are on (1, 2, 3...)
    page = request.args.get("page", 1, type=int)
    per_page = BOOKS_PER_PAGE

    # base query: all this user's books, newest first or whatever order you prefer
    base_query = Book.query.filter_by(user_id=current_user.id).order_by(Book.position.asc(), Book.id.asc())

    total_books = base_query.count()

    # we want to show *all books up to this page*, not just one page slice
    limit = per_page * page
    books = base_query.limit(limit).all()

    has_more = total_books > limit  # is there anything left beyond what we show now?

    user_cols = Collection.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "library.html",
        books=books,
        page=page,
        has_more=has_more,
        collections=user_cols
    )    


@app.route('/search-books')
@login_required
def search_books():
    query = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'relevance')
    page = request.args.get('page', 1, type=int)

    service = BookSearchService(query, sort)
    all_books = service.process()
    books_page = service.get_page(all_books, page)

    has_more = len(all_books) > page * service.per_page

    return render_template(
        "search_results.html",
        books=books_page,
        query=query,
        sort=sort,
        page=page,
        has_more=has_more
    )


@app.route('/search-books-json')
@login_required
def search_books_json():
    query = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'relevance')
    page = request.args.get('page', type=int)

    service = BookSearchService(query, sort)
    all_books = service.process()
    chunk = service.get_page(all_books, page)

    return jsonify(chunk)


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


@app.route('/update-status/<int:book_id>', methods=['POST'])
@login_required
def update_status(book_id):
    new_status = request.form.get("status")

    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first()

    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for('library'))

    book.status = new_status
    db.session.commit()

    flash(f"Status updated to '{new_status}'.", "success")
    return redirect(url_for('library'))


@app.route("/delete-book/<int:book_id>", methods=["POST"])
@login_required
def delete_book(book_id):
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for("library"))


@app.route("/filter-books")
@login_required
def filter_books():
    status = request.args.get("status")
    genre = request.args.get("genre")
    author = request.args.get("author")

    # Start with current user's books
    query = Book.query.filter_by(user_id=current_user.id)

    # Apply filters if present
    if status:
        query = query.filter(Book.status == status)

    if genre:
        query = query.filter(Book.genres.ilike(f"%{genre}%"))

    if author:
        query = query.filter(Book.author == author)

    books = query.order_by(Book.id.asc()).all()

    # Generate dropdown lists
    genres_set = {
        g.strip()
        for b in current_user.books if b.genres
        for g in b.genres.split(",")
    }

    authors_set = {b.author for b in current_user.books if b.author}

    return render_template(
        "library.html",
        books=books,
        page=1,
        has_more=False,
        genres=sorted(genres_set),
        authors=sorted(authors_set)
    )


@app.route("/collections", methods=["GET", "POST"])
@login_required
def collections():
    if request.method == "POST":
        name = request.form.get("name").strip()

        if not name:
            flash("Collection must have a name.", "danger")
            return redirect(url_for("collections"))

        new_col = Collection(name=name, user_id=current_user.id)
        db.session.add(new_col)
        db.session.commit()

        flash(f'Collection "{name}" created!', "success")
        return redirect(url_for("collections"))

    # GET → show list of collections
    user_cols = Collection.query.filter_by(user_id=current_user.id).all()
    return render_template("collections.html", collections=user_cols)


@app.route("/collection/<int:col_id>")
@login_required
def view_collection(col_id):
    col = Collection.query.filter_by(id=col_id, user_id=current_user.id).first_or_404()
    return render_template("collection_view.html", collection=col)


@app.route("/add-to-collection/<int:book_id>", methods=["POST"])
@login_required
def add_to_collection(book_id):
    collection_id = request.form.get("collection_id")

    col = Collection.query.filter_by(id=collection_id, user_id=current_user.id).first()
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first()

    if not col or not book:
        flash("Invalid collection or book.", "danger")
        return redirect(url_for("library"))

    if book not in col.books:
        col.books.append(book)
        db.session.commit()

    flash("Book added to collection!", "success")
    return redirect(request.referrer or url_for("library"))


@app.route("/remove-from-collection/<int:col_id>/<int:book_id>", methods=["POST"])
@login_required
def remove_from_collection(col_id, book_id):
    col = Collection.query.filter_by(id=col_id, user_id=current_user.id).first_or_404()
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()

    if book in col.books:
        col.books.remove(book)
        db.session.commit()

    flash("Book removed from collection.", "info")
    return redirect(request.referrer or url_for("view_collection", col_id=col_id))


@app.route("/delete-collection/<int:col_id>", methods=["POST"])
@login_required
def delete_collection(col_id):
    col = Collection.query.filter_by(id=col_id, user_id=current_user.id).first_or_404()

    # Remove all book links, but keep the books themselves
    col.books.clear()

    db.session.delete(col)
    db.session.commit()

    flash("Collection deleted.", "info")
    return redirect(url_for("collections"))


@app.route("/rename-collection/<int:col_id>", methods=["POST"])
@login_required
def rename_collection(col_id):
    col = Collection.query.filter_by(id=col_id, user_id=current_user.id).first_or_404()

    new_name = request.form.get("new_name", "").strip()
    if not new_name:
        flash("Collection name cannot be empty.", "danger")
        return redirect(url_for("collections"))

    col.name = new_name
    db.session.commit()

    flash("Collection renamed.", "success")
    return redirect(url_for("collections"))


@app.route('/book/<int:book_id>')
@login_required
def book_detail(book_id):
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first()

    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for('library'))
    
    user_cols = Collection.query.filter_by(user_id=current_user.id).all()

    return render_template("book_detail.html", book=book, collections=user_cols)


@app.route("/update-notes/<int:book_id>", methods=["POST"])
@login_required
def update_notes(book_id):
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()

    book.notes = request.form.get("notes", "").strip()
    db.session.commit()

    flash("Notes updated.", "success")
    return redirect(url_for("book_detail", book_id=book.id))


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


@app.route("/update-order", methods=["POST"])
@login_required
def update_order():
    data = request.get_json()
    order = data.get("order", [])

    for idx, book_id in enumerate(order):
        book = Book.query.filter_by(id=book_id, user_id=current_user.id).first()
        if book:
            book.position = idx

    db.session.commit()
    return jsonify({"status": "ok"})



if __name__ == '__main__':
    app.run(debug=True)
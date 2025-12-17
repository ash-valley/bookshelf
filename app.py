from flask import Flask, render_template, request, flash, redirect, url_for, get_flashed_messages, session, jsonify
from flask_login import login_user, logout_user, login_required, LoginManager, current_user
from flask_migrate import Migrate
from search_service import BookSearchService
from dotenv import load_dotenv
import os

from forms import RegistrationForm, LoginForm
from models import db, User, Book, Collection, Quote, CollectionBook  
from werkzeug.security import generate_password_hash, check_password_hash
import requests 

from datetime import date
import random

load_dotenv()  


app = Flask(__name__)

BOOKS_PER_PAGE = 20

migrate = Migrate(app, db)

# Read environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Initialize the database ---
db.init_app(app)

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
@login_required
def library():
    page = request.args.get("page", 1, type=int)
    per_page = BOOKS_PER_PAGE

    # --- read filters from query params ---
    status = request.args.get("status", "").strip()
    genre = request.args.get("genre", "").strip()
    author = request.args.get("author", "").strip()

    # --- base query ---
    query = Book.query.filter_by(user_id=current_user.id)

    # --- apply filters ---
    if status:
        query = query.filter(Book.status == status)

    if genre:
        query = query.filter(Book.genres.ilike(f"%{genre}%"))

    if author:
        query = query.filter(Book.author == author)

    # --- ordering (SHELF IS THE SOURCE OF TRUTH) ---
    query = query.order_by(Book.position.asc(), Book.id.asc())

    total_books = query.count()

    limit = per_page * page
    books = query.limit(limit).all()

    has_more = total_books > limit

    # --- collections for dropdown ---
    user_cols = Collection.query.filter_by(user_id=current_user.id).all()

    # --- filter dropdown values ---
    genres_set = {
        g.strip()
        for b in current_user.books if b.genres
        for g in b.genres.split(",")
    }

    authors_set = {b.author for b in current_user.books if b.author}

    return render_template(
        "library.html",
        books=books,
        page=page,
        has_more=has_more,
        collections=user_cols,
        genres=sorted(genres_set),
        authors=sorted(authors_set),
        selected_status=status,
        selected_genre=genre,
        selected_author=author
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
    
    max_pos = db.session.query(db.func.max(Book.position))\
        .filter_by(user_id=current_user.id).scalar()
    next_pos = (max_pos + 1) if max_pos is not None else 0

    # Create new Book object
    new_book = Book(
        title=title,
        author=author,
        cover_url=cover_url,
        description=description,
        year=year,
        genres=genres,
        status="to-read",  # Default status
        user_id=current_user.id,
        position=next_pos
    )

    # Save to DB
    db.session.add(new_book)
    db.session.commit()

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

    return redirect(url_for('library'))


@app.route("/delete-book/<int:book_id>", methods=["POST"])
@login_required
def delete_book(book_id):
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()

    # delete dependent rows first 
    CollectionBook.query.filter_by(book_id=book.id).delete()
    Quote.query.filter_by(book_id=book.id, user_id=current_user.id).delete()

    db.session.delete(book)
    db.session.commit()
    return redirect(url_for("library"))


@app.route("/collections", methods=["GET", "POST"])
@login_required
def collections():
    if request.method == "POST":
        name = request.form.get("name").strip()

        if not name:
            flash("Collection must have a name.", "danger")
            return redirect(url_for("collections"))
        
        max_pos = db.session.query(db.func.max(Collection.position))\
            .filter_by(user_id=current_user.id).scalar()

        new_col = Collection(
            name=name,
            user_id=current_user.id,
            position=(max_pos + 1) if max_pos is not None else 0
        )
        db.session.add(new_col)
        db.session.commit()

        return redirect(url_for("collections"))

    # GET → show list of collections
    user_cols = (
        Collection.query
        .filter_by(user_id=current_user.id)
        .order_by(Collection.position.asc(), Collection.id.asc())
        .all()
    )
    return render_template("collections.html", collections=user_cols)


@app.route("/collection/<int:col_id>")
@login_required
def view_collection(col_id):
    col = Collection.query.filter_by(id=col_id, user_id=current_user.id).first_or_404()

    # Load entries in correct order
    entries = (
        CollectionBook.query
        .filter_by(collection_id=col.id)
        .order_by(CollectionBook.position.asc())
        .all()
    )

    return render_template("collection_view.html", collection=col, entries=entries)


@app.route("/add-to-collection/<int:book_id>", methods=["POST"])
@login_required
def add_to_collection(book_id):
    collection_id = request.form.get("collection_id")

    col = Collection.query.filter_by(id=collection_id, user_id=current_user.id).first()
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first()

    if not col or not book:
        flash("Invalid collection or book.", "danger")
        return redirect(url_for("library"))

    # Prevent duplicates
    existing = CollectionBook.query.filter_by(collection_id=col.id, book_id=book.id).first()
    if existing:
        flash("Book is already in the collection.", "info")
        return redirect(request.referrer or url_for("library"))

    # Determine next position
    max_position = db.session.query(db.func.max(CollectionBook.position))\
                     .filter_by(collection_id=col.id).scalar()
    next_position = (max_position + 1) if max_position is not None else 0

    # Create new entry
    entry = CollectionBook(
        collection_id=col.id,
        book_id=book.id,
        position=next_position
    )
    db.session.add(entry)
    db.session.commit()

    return redirect(request.referrer or url_for("library"))


@app.route("/remove-from-collection/<int:col_id>/<int:book_id>", methods=["POST"])
@login_required
def remove_from_collection(col_id, book_id):
    col = Collection.query.filter_by(id=col_id, user_id=current_user.id).first_or_404()
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()

    entry = CollectionBook.query.filter_by(collection_id=col.id, book_id=book.id).first()

    if entry:
        db.session.delete(entry)
        db.session.commit()

    return redirect(request.referrer or url_for("view_collection", col_id=col_id))


@app.route("/delete-collection/<int:col_id>", methods=["POST"])
@login_required
def delete_collection(col_id):
    col = Collection.query.filter_by(id=col_id, user_id=current_user.id).first_or_404()
    db.session.delete(col)
    db.session.commit()

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

    return redirect(url_for("collections"))


@app.route("/update-collections-order", methods=["POST"])
@login_required
def update_collections_order():
    data = request.get_json(force=True) or {}
    raw_order = data.get("order") or []

    order = []
    for value in raw_order:
        try:
            order.append(int(value))
        except (TypeError, ValueError):
            continue

    for idx, col_id in enumerate(order):
        col = Collection.query.filter_by(
            id=col_id,
            user_id=current_user.id
        ).first()
        if col:
            col.position = idx

    db.session.commit()
    return jsonify({"status": "ok"})


@app.route("/update-collection-order/<int:col_id>", methods=["POST"])
@login_required
def update_collection_order(col_id):
    col = Collection.query.filter_by(id=col_id, user_id=current_user.id).first_or_404()

    data = request.get_json(force=True) or {}
    raw_order = data.get("order") or []

    # Normalize to a clean list of ints
    order = []
    for value in raw_order:
        try:
            order.append(int(value))
        except (TypeError, ValueError):
            continue

    # Update positions based on this order
    for idx, book_id in enumerate(order):
        entry = CollectionBook.query.filter_by(
            collection_id=col.id,
            book_id=book_id
        ).first()
        if entry:
            entry.position = idx

    db.session.commit()
    return jsonify({"status": "ok"})


@app.route('/book/<int:book_id>')
@login_required
def book_detail(book_id):
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first()

    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for('library'))
    
    q = request.args.get("q", "").strip()

    if q:
        filtered_quotes = [
            quote for quote in book.quotes
            if q.lower() in quote.text.lower() or
               q.lower() in (quote.tags or "").lower() or
               q.lower() in (quote.comment or "").lower()
        ]
    else:
        filtered_quotes = book.quotes

    user_cols = Collection.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "book_detail.html",
        book=book,
        collections=user_cols,
        quotes=filtered_quotes,
        quote_filter=q
    )


@app.route("/update-notes/<int:book_id>", methods=["POST"])
@login_required
def update_notes(book_id):
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()

    book.notes = request.form.get("notes", "").strip()
    db.session.commit()

    return redirect(url_for("book_detail", book_id=book.id))


@app.route('/quotes')
@login_required
def quotes():
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "newest")

    # Base query
    query = Quote.query.filter_by(user_id=current_user.id)

    # Filter by search
    if search:
        query = query.filter(
            Quote.text.ilike(f"%{search}%") |
            Quote.tags.ilike(f"%{search}%") |
            Quote.comment.ilike(f"%{search}%")
        )

    # Sorting options
    if sort == "newest":
        query = query.order_by(Quote.id.desc())
    elif sort == "oldest":
        query = query.order_by(Quote.id.asc())
    elif sort == "book":
        query = query.join(Book).order_by(Book.title.asc())
    elif sort == "page":
        query = query.order_by(Quote.page.asc().nullslast())

    quotes = query.all()

    return render_template(
        "quotes.html",
        quotes=quotes,
        search=search,
        sort=sort
    )


@app.route("/add-quote/<int:book_id>", methods=["POST"])
@login_required
def add_quote(book_id):
    book = Book.query.filter_by(id=book_id, user_id=current_user.id).first_or_404()

    text = request.form.get("text", "").strip()
    page = request.form.get("page", "").strip()
    tags = request.form.get("tags", "").strip()
    comment = request.form.get("comment", "").strip()

    if not text:
        flash("Quote cannot be empty.", "danger")
        return redirect(url_for("book_detail", book_id=book_id))

    quote = Quote(
        text=text,
        page=page,
        tags=tags,
        comment=comment,
        book_id=book.id,
        user_id=current_user.id
    )

    db.session.add(quote)
    db.session.commit()

    return redirect(url_for("book_detail", book_id=book.id))


@app.route("/delete-quote/<int:quote_id>", methods=["POST"])
@login_required
def delete_quote(quote_id):
    quote = Quote.query.filter_by(id=quote_id, user_id=current_user.id).first_or_404()

    book_id = quote.book_id
    db.session.delete(quote)
    db.session.commit()

    return redirect(url_for("book_detail", book_id=book_id))


@app.route("/edit-quote/<int:quote_id>", methods=["POST"])
@login_required
def edit_quote(quote_id):
    quote = Quote.query.filter_by(id=quote_id, user_id=current_user.id).first_or_404()

    quote.text = request.form.get("text", "").strip()
    quote.page = request.form.get("page", "").strip()
    quote.tags = request.form.get("tags", "").strip()
    quote.comment = request.form.get("comment", "").strip()

    db.session.commit()

    return redirect(url_for("book_detail", book_id=quote.book_id))


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
    data = request.get_json(force=True) or {}
    raw_order = data.get("order") or []

    order = []
    for value in raw_order:
        try:
            order.append(int(value))
        except (TypeError, ValueError):
            continue

    for idx, book_id in enumerate(order):
        book = Book.query.filter_by(id=book_id, user_id=current_user.id).first()
        if book:
            book.position = idx

    db.session.commit()
    return jsonify({"status": "ok"})


@app.route("/profile")
@login_required
def profile():
    total_books = Book.query.filter_by(user_id=current_user.id).count()
    total_collections = Collection.query.filter_by(user_id=current_user.id).count()
    total_quotes = Quote.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "profile.html",
        total_books=total_books,
        total_collections=total_collections,
        total_quotes=total_quotes
    )


@app.post("/profile/edit")
@login_required
def edit_profile():
    new_username = request.form.get("username")
    new_email = request.form.get("email")

    if not new_username or not new_email:
        flash("All fields must be filled.", "error")
        return redirect("/profile")

    # Check if email already exists
    existing_email = User.query.filter(
        User.email == new_email,
        User.id != current_user.id
    ).first()

    if existing_email:
        flash("Email already in use.", "error")
        return redirect("/profile")

    current_user.username = new_username
    current_user.email = new_email
    db.session.commit()

    return redirect("/profile")


@app.post("/profile/change-password")
@login_required
def change_password():
    old_pw = request.form.get("old_password")
    new_pw = request.form.get("new_password")
    confirm_pw = request.form.get("confirm_password")

    if not old_pw or not new_pw or not confirm_pw:
        flash("All fields must be filled.", "error")
        return redirect("/profile")

    if not check_password_hash(current_user.password, old_pw):
        flash("Incorrect current password.", "error")
        return redirect("/profile")

    if new_pw != confirm_pw:
        flash("New passwords do not match.", "error")
        return redirect("/profile")

    current_user.password = generate_password_hash(new_pw)
    db.session.commit()

    return redirect("/profile")


@app.post("/profile/delete")
@login_required
def delete_account():
    confirmation = request.form.get("confirm_text")

    if confirmation != "DELETE":
        flash("You must type DELETE to confirm.", "error")
        return redirect("/profile")

    # Delete all user-related data
    # delete join rows for user's collections
    user_collection_ids = [c.id for c in Collection.query.filter_by(user_id=current_user.id).all()]
    if user_collection_ids:
        CollectionBook.query.filter(CollectionBook.collection_id.in_(user_collection_ids)).delete(synchronize_session=False)

    # delete join rows for user's books (belt & suspenders)
    user_book_ids = [b.id for b in Book.query.filter_by(user_id=current_user.id).all()]
    if user_book_ids:
        CollectionBook.query.filter(CollectionBook.book_id.in_(user_book_ids)).delete(synchronize_session=False)

    Book.query.filter_by(user_id=current_user.id).delete()
    Quote.query.filter_by(user_id=current_user.id).delete()
    Collection.query.filter_by(user_id=current_user.id).delete()

    user_id = current_user.id

    logout_user()  # Safely end session
    User.query.filter_by(id=user_id).delete()

    db.session.commit()

    flash("Your account has been deleted.", "success")
    return redirect("/")


if __name__ == '__main__':
    app.run(debug=True)
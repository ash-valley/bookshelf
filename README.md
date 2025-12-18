# Bookshelf

#### Video Demo: <URL HERE>

#### Description:
Bookshelf is a personal web application that allows you to create/manage your own virtual library of books, view books' summaries and write down personal notes, organize books into custom collections, and save memorable quotes. The project was developed as the final submission for CS50 Harvard course. The main focus was to create a place where users would be able to catalogue their books. As Bookshelf grew it acquired additional features to supplement core functionality and make for an overall cozy and enjoyable experience.  

The application supports user registration and authentication, allowing each user to store/maintain a private library/catalogue of books. Users can add books (in English and Ukrainian languages), change their reading status, group them into collections (also allowing to create reading lists here), re-order books and collections using drag-and-drop, and view detailed book pages containing personal notes and related quotes (you can add notes/comments to each quote too). There is also a separate Quotes section that allows you to search, sort, and manage quotes independently from books, making it easy, for example, to pull up a quote by a specific tag.

As the project grew in complexity, database schema changes became necessary. Instead of deleting/recreating the database, Flask-Migrate (Alembic) was introduced to handle database migration safely. This allowed new features, such as persistent ordering of collections, to be added without losing existing data. Introducing Flask-Migrate happened at the stage when implementing many-to-many relationships in database became necessary, Specifically, between books and collections, as one book can belong to many collections and one collection can contain multiple books.

After finalizing desktop view, particular attention was paid to ensuring responsive behavior across devices. Mobile support for phones/tablets was tested and refined in the same way as for desktop. Several design decisions had to be made, such as disabling drag-and-drop reordering on phone screens to prevent accidental undesirable interactions, while preserving it on tablets and desktops where this ordering mechanic feels natural.

Visual styling and customization make for a significant part of the app. Introduction of several background themes has been an intentional design choice from the beginning, as core functionality and supplementary visuals create an organic combined experience for users. Color palettes had to be adjusted for each specific theme, button styles, spacing and modals had to be unified and made consistent across all pages. Features were implemented incrementally and refined after testing, rather than attempting to finalize everything in a single pass. This approach helped tremendously in identifying and resolving all issues appearing over the course of development. 

One of the more challenging aspects of the project was refining the book search functionality, which relies on the Google Books API. The API provides a large amount of data, but it has practical limitations when using it in a specific project code to create a predictable search functionality. 
A key issue encountered during development was how Google Books represents book series and multiple editions. The API frequently returns several entries for what is effectively the same book, including hardcover, paperback, ebook, special editions, reprints, and sometimes regional variations. Additionally, books that belong to a series are not always consistently grouped or labeled in the metadata. 
As a result, a single search query can produce many visually similar results that differ only slightly in formatting or edition details, or, on the other hand, do not return some results when querying only by book title. 
Due to this behavior a decision was made not to treat search results as a one-to-one representation of distinct books. Rather than attempting to aggressively remove duplicate results based on unreliable metadata, search results are presented transparently, allowing users to choose the edition that best matches what they are looking for. The goal is to avoid projecting developer's assumptions on to users about which entries should be merged and prevents the accidental loss of valid data. As for some results not being searchable by title only, queries by title and author catch that missing data. 

Special consideration was also given to how search results integrate with the rest of the application. Once a book is added to the user’s library, it becomes a distinct entity managed internally by the application, independent of how many similar entries may exist in the Google Books API. This prevents future changes in external API data from affecting stored records.

---

## Project Structure and Files

### `app.py`
This is the main entry point of the application. It defines the Flask app, configures extensions, and contains all route definitions. Routes in `app.py` handle user authentication, library management, collections, quotes, book detail, home, profile and themes pages. It also contains backend logic for features such as drag-and-drop ordering, pagination, and form handling. The file coordinates interactions between the database models and the templates rendered for the user.

### `models.py`
This file defines all database models using SQLAlchemy. Models include `User`, `Book`, `Collection`, `Quote`, and the association tables required for many-to-many relationships. It also defines ordering fields used for drag-and-drop persistence. 

### `forms.py`
This files contains Login and Registration forms. 

### `search_service.py`
This is a helper file, that defines the book search function and all it's components: configuration, fetching, filtering, scoring & sorting, converting raw Google Books data into dictionaries for templates, preparing full pipeline, pagination helper and synthetic genres definition

### `templates/`
This directory contains all HTML templates rendered by Flask using Jinja. Templates include:
- `base.html`: the base layout shared by all pages, including navigation, global styles, and scripts.
- `home.html`: the homepage, which displays different content depending on whether a user is logged in.
- `library.html`: displays the user’s book library, including search, filters, pagination, and drag-and-drop ordering.
- `collections.html`: shows all user-created collections and supports persistent reordering.
- `collection_view.html`: displays the contents of a single collection, allows drag-and-drop ordering.
- `book_detail.html`: shows detailed information about a book, including notes and quotes.
- `quotes.html`: displays all saved quotes with search and sorting options.
- `profile.html`, `login.html`, and `register.html`: handle user account management and authentication.

### `static/`
The `static` directory contains CSS and static assets used by the application.
- `css/style.css` defines custom styles applied to templates.
- `img` folder contains three themed versions of logo used as part of app branding.
- `textures` contains optional versions of background texture used in default "Spring" theme.
- JavaScript is embedded directly in templates. The `js` folder was created for possible future project development. 

### `migrations/`
This directory was generated and managed by Flask-Migrate (Alembic). It contains migration scripts that track database schema changes over time. This allows further project development without resetting the database every time. 

---

## Features

- User registration and authentication
- Personal book library with search using Google Books API, search allowed for EN and UA languages
- Drag-and-drop persistent ordering of books and collections, stored in the database
- Server-side pagination 
- Custom book collections
- Book detail pages with notes and quotes
- Quotes system with search, sorting, tags, and comments
- Modal-based editing and deletion flows 
- Responsive design for desktop, phone, tablet
- Three background themes available for user preference

---

## Technology Stack

- Python with Flask
- SQLite database
- SQLAlchemy ORM
- Flask-Login for authentication
- Flask-Migrate (Alembic) for database migrations
- Tailwind CSS for styling
- Vanilla JavaScript for client-side interactions

---

## Installation and Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd bookshelf

2. Create and activate a virtual environment:
   python -m venv venv
   source venv/bin/activate

3. Install dependencies:
   pip install -r requirements.txt

4. Apply database migrations:
   flask db upgrade

5. Run the application:
   flask run

---

## Future Improvements

Possible future improvements include a reorder mode tailored specifically for phone screens, advanced filtering options, import/export functionality, and sharing of collections/other social options. 

## Acknowledgements

This project was completed as part of CS50: Introduction to Computer Science (Harvard University). Additional resources include the Flask and SQLAlchemy documentation, Tailwind CSS, and the Google Books API.
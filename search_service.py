# search_service.py

import requests
from difflib import get_close_matches


class BookSearchService:
    def __init__(self, query, sort="relevance"):
        self.query = query.strip()
        self.sort = sort
        self.url = "https://www.googleapis.com/books/v1/volumes"

        # Configuration
        self.per_page = 12
        self.banned = {
            "geology", "sediment", "ecology", "vegetation",
            "analysis", "report", "basin", "reservoir",
            "gas", "management", "erosion", "university",
            "survey", "research", "study"
        }

        self.literary_clues = {
            "fiction", "fantasy", "novel", "science fiction", "sci-fi",
            "epic", "adventure", "romance", "thriller", "space",
            "galactic", "hero", "saga", "chronicles", "series"
        }


    # ----------------------------------------------------------
    # Fetching
    # ----------------------------------------------------------
    def fetch_raw_results(self):
        queries = [
            f'intitle:"{self.query}"',
            f'intitle:{self.query}',
            self.query
        ]

        seen = set()
        results = []

        for q in queries:
            params = {
                "q": q,
                "maxResults": 40,
                "printType": "books",
                "langRestrict": "en"
            }
            resp = requests.get(self.url, params=params).json()
            items = resp.get("items", []) or []

            for item in items:
                bid = item.get("id")
                if bid and bid not in seen:
                    seen.add(bid)
                    results.append(item)

        return results


    # ----------------------------------------------------------
    # Filtering
    # ----------------------------------------------------------
    def is_literary(self, item):
        info = item.get("volumeInfo", {})

        # Require cover
        if not info.get("imageLinks"):
            return False

        title = (info.get("title") or "").lower()
        desc = (info.get("description") or "").lower()
        authors = " ".join(info.get("authors", [])).lower()
        categories = [c.lower() for c in info.get("categories", []) or []]

        combined_text = title + " " + desc

        # Remove scientific texts
        for w in self.banned:
            if w in combined_text:
                return False

        # Accept if title contains query
        if self.query.lower() in title:
            return True

        # Accept if categories show fiction
        for c in categories:
            if any(k in c for k in self.literary_clues):
                return True

        return False


    def filter_results(self, raw_results):
        return [r for r in raw_results if self.is_literary(r)]


    # ----------------------------------------------------------
    # Synthetic genres
    # ----------------------------------------------------------
    def extract_genres(self, info):
        genres = set()

        # API categories
        for c in info.get("categories", []) or []:
            if c.lower() not in self.banned:
                genres.add(c)

        # Keyword mapping
        text = (info.get("title", "") + " " +
                (info.get("description") or "")).lower()

        mapping = {
            "fantasy": "Fantasy",
            "epic": "Epic",
            "science fiction": "Science Fiction",
            "sci-fi": "Science Fiction",
            "space": "Science Fiction",
            "galactic": "Science Fiction",
            "magic": "Fantasy",
            "hero": "Fantasy",
            "adventure": "Adventure",
            "dystopian": "Dystopian",
        }

        for word, label in mapping.items():
            if word in text:
                genres.add(label)

        if not genres:
            return "Unknown"

        return ", ".join(sorted(genres))


    # ----------------------------------------------------------
    # Scoring & sorting
    # ----------------------------------------------------------
    def fuzzy_score(self, title):
        t = title.lower()
        q = self.query.lower()

        exact = 1 if t == q else 0
        contains = 1 if q in t else 0
        fuzzy = 1 if get_close_matches(q, [t], cutoff=0.6) else 0

        return exact * 10 + contains * 6 + fuzzy * 3


    def sort_results(self, results):
        def key(item):
            info = item.get("volumeInfo", {})
            title = info.get("title", "") or ""
            authors = info.get("authors", [""])[0]
            pub = info.get("publishedDate", "")
            year = int(pub[:4]) if len(pub) >= 4 and pub[:4].isdigit() else 0

            if self.sort == "year":
                return (-year, title.lower())
            if self.sort == "author":
                return (authors.lower(), title.lower())

            score = self.fuzzy_score(title)
            return (-score, title.lower())

        results.sort(key=key)
        return results


    # ----------------------------------------------------------
    # Convert raw Google Books item → dictionary for templates
    # ----------------------------------------------------------
    def convert(self, item):
        info = item.get("volumeInfo", {})
        pub = info.get("publishedDate", "")
        year = pub[:4] if len(pub) >= 4 and pub[:4].isdigit() else ""

        return {
            "id": item.get("id"),
            "title": info.get("title"),
            "authors": ", ".join(info.get("authors", [])),
            "thumbnail": info.get("imageLinks", {}).get("thumbnail"),
            "description": info.get("description", ""),
            "year": year,
            "genres": self.extract_genres(info),
        }


    # ----------------------------------------------------------
    # Full pipeline
    # ----------------------------------------------------------
    def process(self):
        raw = self.fetch_raw_results()
        filtered = self.filter_results(raw)
        sorted_results = self.sort_results(filtered)
        return [self.convert(r) for r in sorted_results]


    # ----------------------------------------------------------
    # Pagination helper
    # ----------------------------------------------------------
    def get_page(self, all_results, page):
        start = (page - 1) * self.per_page
        end = page * self.per_page
        return all_results[start:end]
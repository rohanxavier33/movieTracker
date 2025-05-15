import sqlite3
import logging
from datetime import datetime

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_NAME = 'movies.db'

def create_database():
    """Creates the SQLite database and the movies table if they don't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Create the movies table
        # imdb_id is used as a unique identifier from the API
        # We use INSERT OR IGNORE later to prevent duplicates based on imdb_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imdb_id TEXT UNIQUE,
                title TEXT,
                year TEXT,
                director TEXT,
                genre TEXT,
                poster_url TEXT,
                date_added TEXT
            );
        ''')
        conn.commit()
        logging.info(f"Database '{DATABASE_NAME}' and table 'movies' ensured.")

    except sqlite3.Error as e:
        logging.error(f"Database error during setup: {e}")
    finally:
        if conn:
            conn.close()

def add_movie(movie_data):
    """Inserts a movie record into the database.
    Uses INSERT OR IGNORE based on imdb_id to avoid duplicates.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Use INSERT OR IGNORE based on imdb_id
        # This means if a movie with the same imdb_id already exists,
        # the insert operation is simply skipped without error.
        cursor.execute('''
            INSERT OR IGNORE INTO movies (imdb_id, title, year, director, genre, poster_url, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            movie_data.get('imdbID'),
            movie_data.get('Title'),
            movie_data.get('Year'),
            movie_data.get('Director'),
            movie_data.get('Genre'),
            movie_data.get('Poster'),
            datetime.now().isoformat() # Store current timestamp
        ))
        conn.commit()

        if cursor.rowcount > 0:
            logging.info(f"Successfully added or ignored movie: {movie_data.get('Title')} ({movie_data.get('imdbID')})")
            # Log an 'event' of data being added
            logging.info(f"EVENT: MovieAdded - Title: {movie_data.get('Title')}, IMDbID: {movie_data.get('imdbID')}")
        else:
             logging.info(f"Movie already exists in database (ignored): {movie_data.get('Title')} ({movie_data.get('imdbID')})")
             # Log an 'event' of data being ignored (already exists)
             logging.info(f"EVENT: MovieIgnored - Title: {movie_data.get('Title')}, IMDbID: {movie_data.get('imdbID')}")


    except sqlite3.Error as e:
        logging.error(f"Database error adding movie {movie_data.get('Title')}: {e}")
    except Exception as e:
         logging.error(f"Unexpected error adding movie {movie_data.get('Title')}: {e}")
    finally:
        if conn:
            conn.close()

def get_all_movies():
    """Fetches all movie records from the database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT imdb_id, title, year, director, genre, poster_url, date_added FROM movies;')
        rows = cursor.fetchall()
        # You might want to return data in a more structured format,
        # but for a basic fetch, list of tuples is fine.
        logging.info(f"Fetched {len(rows)} movies from the database.")
        return rows
    except sqlite3.Error as e:
        logging.error(f"Database error fetching movies: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Optional: Add a function to get a single movie by imdb_id for testing/checking
def get_movie_by_imdb_id(imdb_id):
     conn = None
     try:
         conn = sqlite3.connect(DATABASE_NAME)
         cursor = conn.cursor()
         cursor.execute('SELECT imdb_id, title, year, director, genre, poster_url, date_added FROM movies WHERE imdb_id = ?;', (imdb_id,))
         row = cursor.fetchone()
         return row
     except sqlite3.Error as e:
         logging.error(f"Database error fetching movie by IMDb ID {imdb_id}: {e}")
         return None
     finally:
         if conn:
             conn.close()
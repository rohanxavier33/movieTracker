import sqlite3
import logging
from datetime import datetime
# For basic password hashing
from passlib.hash import bcrypt

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_NAME = 'movies.db'

def create_database():
    """Creates the SQLite database and the users/movies tables if they don't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Create the users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            );
        ''')

        # Create the movies table (add user_id column)
        # We'll add a basic index on user_id for faster filtering
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, -- Link to the user
                imdb_id TEXT UNIQUE, -- Keep IMDb ID unique across ALL movies (could change this)
                                     -- If you want same movie for different users, remove UNIQUE
                                     -- and add UNIQUE(user_id, imdb_id) constraint.
                                     -- For simplicity, let's keep UNIQUE on imdb_id for now.
                title TEXT,
                year TEXT,
                director TEXT,
                genre TEXT,
                poster_url TEXT,
                date_added TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) -- Basic foreign key constraint
            );
        ''')

        # Add index on user_id for performance on filtering
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_user_id ON movies (user_id);')

        conn.commit()
        logging.info(f"Database '{DATABASE_NAME}' and tables 'users', 'movies' ensured.")

    except sqlite3.Error as e:
        logging.error(f"Database error during setup: {e}")
    except Exception as e:
         logging.error(f"Unexpected error during database setup: {e}")
    finally:
        if conn:
            conn.close()

# --- User Management Functions ---

def add_user(username, password):
    """Adds a new user to the database with a hashed password."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Hash the password
        hashed_password = bcrypt.hash(password)

        cursor.execute('''
            INSERT INTO users (username, hashed_password)
            VALUES (?, ?)
        ''', (username, hashed_password))
        conn.commit()
        user_id = cursor.lastrowid # Get the ID of the newly inserted user
        logging.info(f"Successfully added user: {username} with ID: {user_id}")
        logging.info(f"EVENT: UserCreated - Username: {username}, UserID: {user_id}")
        return user_id

    except sqlite3.IntegrityError:
        logging.warning(f"Attempted to add existing username: {username}")
        logging.info(f"EVENT: UserCreationFailed - Username: {username}, Reason: AlreadyExists")
        return None # Username already exists
    except sqlite3.Error as e:
        logging.error(f"Database error adding user {username}: {e}")
        return None
    except Exception as e:
         logging.error(f"Unexpected error adding user {username}: {e}")
         return None
    finally:
        if conn:
            conn.close()

def find_user_by_username(username):
    """Finds a user by username and returns their ID and hashed password."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, hashed_password FROM users WHERE username = ?
        ''', (username,))
        user_data = cursor.fetchone()

        if user_data:
            user_id, hashed_password = user_data
            logging.info(f"Found user by username: {username}")
            return user_id, hashed_password
        else:
            logging.info(f"User not found: {username}")
            return None, None

    except sqlite3.Error as e:
        logging.error(f"Database error finding user {username}: {e}")
        return None, None
    except Exception as e:
         logging.error(f"Unexpected error finding user {username}: {e}")
         return None, None
    finally:
        if conn:
            conn.close()

# --- Movie Management Functions (Updated to include user_id) ---

def add_movie(user_id, movie_data):
    """Inserts a movie record for a specific user into the database.
    Uses INSERT OR IGNORE based on imdb_id to avoid duplicates across all users
    (or needs adjustment if unique per user).
    """
    if user_id is None:
        logging.error("Cannot add movie without a valid user_id.")
        return False # Or raise an error
        logging.info(f"EVENT: MovieAddFailed - Reason: NoUserIDProvided, Title: {movie_data.get('Title')}")


    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Using INSERT OR IGNORE on imdb_id globally.
        # If you want unique per user: change table schema to UNIQUE(user_id, imdb_id)
        # and modify the INSERT statement here.
        cursor.execute('''
            INSERT OR IGNORE INTO movies (user_id, imdb_id, title, year, director, genre, poster_url, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
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
            logging.info(f"Successfully added movie for user {user_id}: {movie_data.get('Title')} ({movie_data.get('imdbID')})")
            # Log an 'event' of data being added for a user
            logging.info(f"EVENT: MovieAdded - UserID: {user_id}, Title: {movie_data.get('Title')}, IMDbID: {movie_data.get('imdbID')}")
            return True # Successfully added

        else:
             logging.info(f"Movie already exists globally (ignored) for user {user_id}: {movie_data.get('Title')} ({movie_data.get('imdbID')})")
             # Log an 'event' of data being ignored
             logging.info(f"EVENT: MovieIgnored - UserID: {user_id}, Title: {movie_data.get('Title')}, IMDbID: {movie_data.get('imdbID')}")
             return False # Was ignored because it already exists

    except sqlite3.Error as e:
        logging.error(f"Database error adding movie {movie_data.get('Title')} for user {user_id}: {e}")
        logging.info(f"EVENT: MovieAddFailed - UserID: {user_id}, Title: {movie_data.get('Title')}, Reason: DBError - {e}")
        return False
    except Exception as e:
         logging.error(f"Unexpected error adding movie {movie_data.get('Title')} for user {user_id}: {e}")
         logging.info(f"EVENT: MovieAddFailed - UserID: {user_id}, Title: {movie_data.get('Title')}, Reason: Unexpected - {e}")
         return False
    finally:
        if conn:
            conn.close()

def get_all_movies(user_id):
    """Fetches all movie records for a specific user from the database."""
    if user_id is None:
        logging.error("Cannot get movies without a valid user_id.")
        return []
        logging.info(f"EVENT: MoviesGetFailed - Reason: NoUserIDProvided")


    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT imdb_id, title, year, director, genre, poster_url, date_added FROM movies WHERE user_id = ?;', (user_id,))
        rows = cursor.fetchall()
        logging.info(f"Fetched {len(rows)} movies for user {user_id}.")
        # Log the event of fetching movies
        logging.info(f"EVENT: MoviesFetched - UserID: {user_id}, Count: {len(rows)}")
        return rows
    except sqlite3.Error as e:
        logging.error(f"Database error fetching movies for user {user_id}: {e}")
        logging.info(f"EVENT: MoviesGetFailed - UserID: {user_id}, Reason: DBError - {e}")
        return []
    except Exception as e:
         logging.error(f"Unexpected error fetching movies for user {user_id}: {e}")
         logging.info(f"EVENT: MoviesGetFailed - UserID: {user_id}, Reason: Unexpected - {e}")
         return []
    finally:
        if conn:
            conn.close()

# --- New Function to Clear User's List ---

def delete_all_movies_for_user(user_id):
    """Deletes all movie records for a specific user."""
    if user_id is None:
        logging.error("Cannot delete movies without a valid user_id.")
        return 0
        logging.info(f"EVENT: MoviesDeleteFailed - Reason: NoUserIDProvided")

    conn = None
    deleted_count = 0
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM movies WHERE user_id = ?;', (user_id,))
        deleted_count = cursor.rowcount
        conn.commit()

        logging.info(f"Successfully deleted {deleted_count} movies for user {user_id}.")
        # Log the event of deleting movies
        logging.info(f"EVENT: MoviesDeleted - UserID: {user_id}, Count: {deleted_count}")

        return deleted_count

    except sqlite3.Error as e:
        logging.error(f"Database error deleting movies for user {user_id}: {e}")
        logging.info(f"EVENT: MoviesDeleteFailed - UserID: {user_id}, Reason: DBError - {e}")
        return 0
    except Exception as e:
         logging.error(f"Unexpected error deleting movies for user {user_id}: {e}")
         logging.info(f"EVENT: MoviesDeleteFailed - UserID: {user_id}, Reason: Unexpected - {e}")
         return 0
    finally:
        if conn:
            conn.close()
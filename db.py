# db.py
import sqlite3
import logging
from datetime import datetime
from passlib.hash import bcrypt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DATABASE_NAME = 'movies.db'

def create_database():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                imdb_id TEXT NOT NULL,
                title TEXT,
                year TEXT,
                director TEXT,
                genre TEXT,
                poster_url TEXT,
                status TEXT,
                user_rating INTEGER, 
                date_added TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT user_movie_unique UNIQUE (user_id, imdb_id)
            );
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_user_id ON movies (user_id);')
        conn.commit()
        logging.info(f"Database '{DATABASE_NAME}' and tables 'users', 'movies' ensured (with user_rating column).")
    except sqlite3.Error as e:
        logging.error(f"Database error during setup: {e}")
    finally:
        if conn:
            conn.close()

# --- User Management Functions ---
def add_user(username, password):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        hashed_password = bcrypt.hash(password)
        cursor.execute('INSERT INTO users (username, hashed_password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        user_id = cursor.lastrowid 
        logging.info(f"Successfully added user: {username} with ID: {user_id}")
        logging.info(f"EVENT: UserCreated - Username: {username}, UserID: {user_id}")
        return user_id
    except sqlite3.IntegrityError: 
        logging.warning(f"Attempted to add existing username: {username}")
        logging.info(f"EVENT: UserCreationFailed - Username: {username}, Reason: AlreadyExists")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error adding user {username}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def find_user_by_username(username):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT id, hashed_password FROM users WHERE username = ?', (username,))
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
    finally:
        if conn:
            conn.close()

# --- Movie Management Functions ---
def add_movie(user_id, movie_data, status):
    if user_id is None:
        logging.info(f"EVENT: MovieAddFailed - Reason: NoUserIDProvided, Title: {movie_data.get('Title')}, Status: {status}")
        logging.error("Cannot add movie without a valid user_id.")
        return False
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO movies (user_id, imdb_id, title, year, director, genre, poster_url, status, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, movie_data.get('imdbID'), movie_data.get('Title'),
            movie_data.get('Year'), movie_data.get('Director'), movie_data.get('Genre'),
            movie_data.get('Poster'), status, datetime.now().isoformat()
        ))
        conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Successfully added movie for user {user_id}: {movie_data.get('Title')} ({movie_data.get('imdbID')}) with status '{status}'")
            logging.info(f"EVENT: MovieAdded - UserID: {user_id}, Title: {movie_data.get('Title')}, IMDbID: {movie_data.get('imdbID')}, Status: {status}")
            return True
        else:
            logging.info(f"Movie already exists for user {user_id}: {movie_data.get('Title')} ({movie_data.get('imdbID')}). Insert ignored.")
            logging.info(f"EVENT: MovieIgnoredDuplicateForUser - UserID: {user_id}, Title: {movie_data.get('Title')}, IMDbID: {movie_data.get('imdbID')}")
            return False
    except sqlite3.Error as e:
        logging.error(f"Database error adding movie {movie_data.get('Title')} for user {user_id}: {e}")
        logging.info(f"EVENT: MovieAddFailed - UserID: {user_id}, Title: {movie_data.get('Title')}, Status: {status}, Reason: DBError - {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_all_movies(user_id):
    if user_id is None:
        logging.info(f"EVENT: MoviesGetFailed - Reason: NoUserIDProvided")
        logging.error("Cannot get movies without a valid user_id.")
        return []
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, imdb_id, title, year, director, genre, poster_url, status, user_rating, date_added 
            FROM movies 
            WHERE user_id = ? 
            ORDER BY date_added DESC;
        ''', (user_id,))
        rows = cursor.fetchall()
        logging.info(f"Fetched {len(rows)} movies for user {user_id}.")
        logging.info(f"EVENT: MoviesFetched - UserID: {user_id}, Count: {len(rows)}")
        return rows
    except sqlite3.Error as e:
        logging.error(f"Database error fetching movies for user {user_id}: {e}")
        logging.info(f"EVENT: MoviesGetFailed - UserID: {user_id}, Reason: DBError - {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_movie_rating(movie_db_id, user_rating):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE movies SET user_rating = ? WHERE id = ?', (user_rating, movie_db_id))
        conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Successfully updated rating for movie_db_id {movie_db_id} to {user_rating}.")
            logging.info(f"EVENT: MovieRatingUpdated - MovieDBID: {movie_db_id}, Rating: {user_rating}")
            return True
        return False 
    except sqlite3.Error as e:
        logging.error(f"Database error updating rating for movie_db_id {movie_db_id}: {e}")
        logging.info(f"EVENT: MovieRatingUpdateFailed - MovieDBID: {movie_db_id}, Rating: {user_rating}, Reason: DBError - {e}")
        return False
    finally:
        if conn:
            conn.close()

def update_movie_status(movie_db_id, new_status):
    """Updates the status of a specific movie entry."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE movies SET status = ? WHERE id = ?;', (new_status, movie_db_id))
        conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Successfully updated status for movie DB ID {movie_db_id} to '{new_status}'.")
            logging.info(f"EVENT: MovieStatusUpdated - MovieDBID: {movie_db_id}, NewStatus: {new_status}")
            return True
        logging.warning(f"No movie found with DB ID {movie_db_id} to update status or status was the same.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error updating status for movie DB ID {movie_db_id}: {e}")
        logging.info(f"EVENT: MovieStatusUpdateFailed - MovieDBID: {movie_db_id}, NewStatus: {new_status}, Reason: DBError - {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_movie_by_db_id(movie_db_id):
    """Deletes a single movie entry by its database primary key."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM movies WHERE id = ?;', (movie_db_id,))
        conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Successfully deleted movie with DB ID: {movie_db_id}")
            logging.info(f"EVENT: MovieDeletedByDBID - MovieDBID: {movie_db_id}")
            return True
        logging.warning(f"No movie found with DB ID: {movie_db_id} to delete.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error deleting movie DB ID {movie_db_id}: {e}")
        logging.info(f"EVENT: MovieDeleteByDBIDFailed - MovieDBID: {movie_db_id}, Reason: DBError - {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_all_movies_for_user(user_id):
    if user_id is None:
        logging.info(f"EVENT: MoviesDeleteFailed - Reason: NoUserIDProvided")
        logging.error("Cannot delete movies without a valid user_id.")
        return 0 
    conn = None
    deleted_count = 0
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM movies WHERE user_id = ?;', (user_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        logging.info(f"Successfully deleted {deleted_count} movies for user {user_id}.")
        logging.info(f"EVENT: MoviesDeleted - UserID: {user_id}, Count: {deleted_count}")
        return deleted_count
    except sqlite3.Error as e:
        logging.error(f"Database error deleting movies for user {user_id}: {e}")
        logging.info(f"EVENT: MoviesDeleteFailed - UserID: {user_id}, Reason: DBError - {e}")
        return 0 
    finally:
        if conn:
            conn.close()
import sqlite3
import pytest
import os
from .. import db 
from passlib.hash import bcrypt # For verifying hashed passwords in tests

# Use an in-memory database for testing, it's faster and cleaner
TEST_DATABASE_NAME = ':memory:'

# Override the database name in the db module for testing
@pytest.fixture(autouse=True)
def set_test_database(monkeypatch):
    monkeypatch.setattr(db, 'DATABASE_NAME', TEST_DATABASE_NAME)
    # Ensure the table is created for each test that needs it
    db.create_database()
    # Add a default user for tests that need user_id
    # Hashing a known password for tests
    test_hashed_password = bcrypt.hash("testpass")
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", ("testuser", test_hashed_password))
    conn.commit()
    conn.close()


def test_create_database_tables_exist():
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movies';")
    movie_table_exists = cursor.fetchone() is not None
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    user_table_exists = cursor.fetchone() is not None
    conn.close()
    assert movie_table_exists
    assert user_table_exists

# --- User Tests ---
def test_add_user():
    user_id = db.add_user("newuser", "newpass")
    assert user_id is not None

    user_data = db.find_user_by_username("newuser")
    assert user_data is not None
    found_user_id, hashed_pass = user_data
    assert found_user_id == user_id
    assert bcrypt.verify("newpass", hashed_pass) # Verify the hashed password

def test_add_user_duplicate_username():
    user_id_1 = db.add_user("duplicateuser", "pass1")
    assert user_id_1 is not None
    user_id_2 = db.add_user("duplicateuser", "pass2") # Should fail
    assert user_id_2 is None # Should return None on failure

def test_find_user_by_username_exists():
    # 'testuser' is added by the set_test_database fixture
    user_id, hashed_pass = db.find_user_by_username("testuser")
    assert user_id is not None
    assert hashed_pass is not None
    assert bcrypt.verify("testpass", hashed_pass) # Verify the password

def test_find_user_by_username_not_exists():
    user_id, hashed_pass = db.find_user_by_username("nonexistentuser")
    assert user_id is None
    assert hashed_pass is None

# --- Movie Tests (Updated for user_id) ---

# Helper function to get the default test user ID
def get_test_user_id():
    user_id, _ = db.find_user_by_username("testuser")
    return user_id

def test_add_movie():
    user_id = get_test_user_id()
    movie_data = {
        'imdbID': 'tt0133093',
        'Title': 'The Matrix',
        'Year': '1999',
        'Director': 'Lana Wachowski, Lilly Wachowski',
        'Genre': 'Action, Sci-Fi',
        'Poster': 'N/A',
    }
    success = db.add_movie(user_id, movie_data) # Pass user_id
    assert success is True # Check if insert was successful

    # Verify it was added for the correct user
    retrieved_movie = db.get_movie_by_imdb_id(movie_data['imdbID'])
    assert retrieved_movie is not None
    # In the db, row is (id, user_id, imdb_id, title, year, director, genre, poster_url, date_added)
    # get_movie_by_imdb_id returns (imdb_id, title, year, director, genre, poster_url, date_added)
    # We need a way to check user_id or assume it's correct if retrieved via user_id query
    # Let's add a helper to query by imdb_id AND user_id for verification
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, title FROM movies WHERE imdb_id = ?;", (movie_data['imdbID'],))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == user_id # Check if the stored user_id is correct
    assert row[1] == movie_data['Title']

def test_add_movie_ignore_duplicate_global():
    user_id_1 = get_test_user_id()
    user_id_2 = db.add_user("anotheruser", "pass2") # Create a second user
    assert user_id_2 is not None

    movie_data_1 = {
        'imdbID': 'tt0133093',
        'Title': 'The Matrix',
        'Year': '1999', 'Director': '...', 'Genre': '...', 'Poster': '...',
    }
    movie_data_2 = {
        'imdbID': 'tt0133093', # Same IMDb ID
        'Title': 'The Matrix Reloaded', # Different title
        'Year': '2003', 'Director': '...', 'Genre': '...', 'Poster': '...',
    }

    success1 = db.add_movie(user_id_1, movie_data_1) # Add for user 1
    assert success1 is True

    success2 = db.add_movie(user_id_2, movie_data_2) # Try to add same movie for user 2
    # This will be False if IMDb ID is globally unique
    # This would be True if unique constraint was (user_id, imdb_id)
    # Based on current schema (UNIQUE imdb_id), it should be False/Ignored
    assert success2 is False

    # Verify only one record exists globally for this IMDb ID
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies WHERE imdb_id = ?;", ('tt0133093',))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 1

    # Verify the record is associated with user_id_1 (the one that succeeded)
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, title FROM movies WHERE imdb_id = ?;", ('tt0133093',))
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == user_id_1 # Should be user 1's ID
    assert row[1] == movie_data_1['Title'] # Should be user 1's title


def test_get_all_movies_empty_for_user():
    user_id = get_test_user_id()
    movies = db.get_all_movies(user_id) # Pass user_id
    assert len(movies) == 0

def test_get_all_movies_with_data_for_user():
    user_id = get_test_user_id()
    user_id_other = db.add_user("user2", "pass2") # Another user

    movie_data_user1_1 = {'imdbID': 'tt1', 'Title': 'Movie 1 User 1', 'Year': '2000', 'Director': 'A', 'Genre': 'SF', 'Poster': 'P1'}
    movie_data_user1_2 = {'imdbID': 'tt2', 'Title': 'Movie 2 User 1', 'Year': '2001', 'Director': 'B', 'Genre': 'Drama', 'Poster': 'P2'}
    movie_data_user2_1 = {'imdbID': 'tt3', 'Title': 'Movie 1 User 2', 'Year': '2002', 'Director': 'C', 'Genre': 'Comedy', 'Poster': 'P3'}

    db.add_movie(user_id, movie_data_user1_1)
    db.add_movie(user_id, movie_data_user1_2)
    db.add_movie(user_id_other, movie_data_user2_1) # Add movie for the other user

    all_movies_user1 = db.get_all_movies(user_id) # Get movies only for user 1
    assert len(all_movies_user1) == 2
    titles_user1 = [m[1] for m in all_movies_user1]
    assert 'Movie 1 User 1' in titles_user1
    assert 'Movie 2 User 1' in titles_user1
    assert 'Movie 1 User 2' not in titles_user1 # Should not include other user's movies

    all_movies_user2 = db.get_all_movies(user_id_other) # Get movies only for user 2
    assert len(all_movies_user2) == 1
    titles_user2 = [m[1] for m in all_movies_user2]
    assert 'Movie 1 User 2' in titles_user2
    assert 'Movie 1 User 1' not in titles_user2


# --- Delete Tests ---
def test_delete_all_movies_for_user():
    user_id = get_test_user_id()
    user_id_other = db.add_user("user3", "pass3") # Another user

    movie_data_user1_1 = {'imdbID': 'tt10', 'Title': 'U1 M1', 'Year': '2010', 'Director': 'A', 'Genre': 'SF', 'Poster': 'P1'}
    movie_data_user1_2 = {'imdbID': 'tt11', 'Title': 'U1 M2', 'Year': '2011', 'Director': 'B', 'Genre': 'Drama', 'Poster': 'P2'}
    movie_data_user2_1 = {'imdbID': 'tt12', 'Title': 'U2 M1', 'Year': '2012', 'Director': 'C', 'Genre': 'Comedy', 'Poster': 'P3'}

    db.add_movie(user_id, movie_data_user1_1)
    db.add_movie(user_id, movie_data_user1_2)
    db.add_movie(user_id_other, movie_data_user2_1) # Add movie for the other user

    # Verify initial state
    assert len(db.get_all_movies(user_id)) == 2
    assert len(db.get_all_movies(user_id_other)) == 1

    # Delete movies for user 1
    deleted_count = db.delete_all_movies_for_user(user_id)
    assert deleted_count == 2 # Should report deleting 2 movies

    # Verify user 1's list is empty
    assert len(db.get_all_movies(user_id)) == 0

    # Verify other user's list is NOT empty
    assert len(db.get_all_movies(user_id_other)) == 1
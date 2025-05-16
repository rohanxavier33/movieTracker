import sqlite3
import pytest
import os
import tempfile # For temporary database file
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db
from passlib.hash import bcrypt

DEFAULT_STATUS = "Want to Watch"

@pytest.fixture(autouse=True)
def setup_test_db_with_user(monkeypatch):
    """
    Creates a temporary database file for each test, initializes the schema,
    and adds a default user. Cleans up the temp file after the test.
    """
    # Create a temporary database file
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    TEST_DB_PATH = temp_db_file.name
    temp_db_file.close() # Close the file handle so sqlite3 can open/manage it

    # Monkeypatch db.DATABASE_NAME to use this temporary file
    monkeypatch.setattr(db, 'DATABASE_NAME', TEST_DB_PATH)

    # Initialize the database schema in the temporary file
    db.create_database()

    # Add a default user using the db module's function
    test_username = "testuser"
    test_password = "testpass"
    user_id = db.add_user(test_username, test_password)
    if not user_id:
        # Fail test explicitly if default user creation fails, as tests depend on it
        pytest.fail(f"Failed to create default user '{test_username}' in test setup.")

    yield # Test runs here

    # Teardown: remove the temporary database file
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

# Helper to get the ID of the default test user, ensuring it exists
def get_test_user_id():
    user_id, _ = db.find_user_by_username("testuser")
    if not user_id:
        pytest.fail("Default test user 'testuser' not found. Fixture setup might have issues.")
    return user_id


def test_create_database_tables_exist():
    # Fixture setup_test_db_with_user ensures db.DATABASE_NAME is set and db.create_database() ran.
    # We connect to the same temporary DB file to verify.
    conn = sqlite3.connect(db.DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movies';")
        movie_table_exists = cursor.fetchone() is not None
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        user_table_exists = cursor.fetchone() is not None
    finally:
        conn.close()
    assert movie_table_exists, "Movies table should exist"
    assert user_table_exists, "Users table should exist"

# --- User Tests ---
def test_add_user():
    user_id = db.add_user("newuser", "newpass")
    assert user_id is not None

    retrieved_id, hashed_pass = db.find_user_by_username("newuser")
    assert retrieved_id == user_id
    assert bcrypt.verify("newpass", hashed_pass)

def test_add_user_duplicate_username():
    # 'testuser' is added by the fixture. Attempting to add again should fail.
    user_id_2 = db.add_user("testuser", "anotherpass")
    assert user_id_2 is None, "Adding a duplicate username should return None"

    # Also test adding a new duplicate user
    db.add_user("duplicate_me", "pass1")
    user_id_dup = db.add_user("duplicate_me", "pass2")
    assert user_id_dup is None

def test_find_user_by_username_exists():
    # 'testuser' is added by the setup_test_db_with_user fixture
    user_id, hashed_pass = db.find_user_by_username("testuser")
    assert user_id is not None
    assert hashed_pass is not None
    assert bcrypt.verify("testpass", hashed_pass)

def test_find_user_by_username_not_exists():
    user_id, hashed_pass = db.find_user_by_username("nonexistentuser")
    assert user_id is None
    assert hashed_pass is None

# --- Movie Tests ---

def test_add_movie_for_user():
    user_id = get_test_user_id()
    movie_data = {
        'imdbID': 'tt0111161', 'Title': 'The Shawshank Redemption', 'Year': '1994',
        'Director': 'Frank Darabont', 'Genre': 'Drama', 'Poster': 'N/A'
    }
    success = db.add_movie(user_id, movie_data, DEFAULT_STATUS)
    assert success is True

    movies = db.get_all_movies(user_id)
    assert len(movies) == 1
    # Order of columns in get_all_movies: imdb_id, title, year, director, genre, poster_url, status, date_added
    assert movies[0][0] == movie_data['imdbID'] # imdb_id
    assert movies[0][1] == movie_data['Title']  # title
    assert movies[0][6] == DEFAULT_STATUS     # status

def test_add_movie_duplicate_for_same_user():
    user_id = get_test_user_id()
    movie_data = {'imdbID': 'tt0137523', 'Title': 'Fight Club', 'Year': '1999', 'Director': 'David Fincher', 'Poster': 'N/A', 'Genre': 'Drama'}

    success1 = db.add_movie(user_id, movie_data, "Watched")
    assert success1 is True
    # Try adding the same movie again for the same user, even with a different status
    success2 = db.add_movie(user_id, movie_data, "Want to Watch")
    assert success2 is False, "Adding a duplicate movie for the same user should fail/be ignored"

    movies = db.get_all_movies(user_id)
    assert len(movies) == 1 # Still only one entry for this movie for this user
    assert movies[0][6] == "Watched", "Original status should persist on duplicate attempt"

def test_add_same_movie_for_different_users():
    user_id1 = get_test_user_id() # "testuser"
    user_id2 = db.add_user("anotheruser", "anotherpass")
    assert user_id2 is not None, "Failed to create a second user for the test"

    movie_data = {'imdbID': 'tt0068646', 'Title': 'The Godfather', 'Year': '1972', 'Director': 'Francis Ford Coppola', 'Poster': 'N/A', 'Genre': 'Crime'}

    success_user1 = db.add_movie(user_id1, movie_data, "Watched")
    assert success_user1 is True
    success_user2 = db.add_movie(user_id2, movie_data, "Want to Watch")
    assert success_user2 is True, "Adding the same movie for a different user should succeed"

    movies_user1 = db.get_all_movies(user_id1)
    assert len(movies_user1) == 1
    assert movies_user1[0][1] == movie_data['Title']
    assert movies_user1[0][6] == "Watched"

    movies_user2 = db.get_all_movies(user_id2)
    assert len(movies_user2) == 1
    assert movies_user2[0][1] == movie_data['Title']
    assert movies_user2[0][6] == "Want to Watch"

def test_get_all_movies_empty_for_new_user():
    new_user_id = db.add_user("emptyuser", "emptypass")
    assert new_user_id is not None
    movies = db.get_all_movies(new_user_id)
    assert len(movies) == 0

def test_get_all_movies_with_data_for_user():
    user_id = get_test_user_id()
    other_user_id = db.add_user("othermovielistuser", "pass")
    db.add_movie(other_user_id, {'imdbID': 'tt999', 'Title': 'Other User Movie', 'Poster': 'N/A', 'Genre': 'Other', 'Year': '2000', 'Director': 'Dir'}, "Watched")

    movie1_data = {'imdbID': 'tt0120338', 'Title': 'Titanic', 'Year': '1997', 'Director': 'James Cameron', 'Poster': 'N/A', 'Genre': 'Drama'}
    movie2_data = {'imdbID': 'tt0109830', 'Title': 'Forrest Gump', 'Year': '1994', 'Director': 'Robert Zemeckis', 'Poster': 'N/A', 'Genre': 'Drama'}
    db.add_movie(user_id, movie1_data, "Watched")
    db.add_movie(user_id, movie2_data, "Want to Watch")

    movies = db.get_all_movies(user_id)
    assert len(movies) == 2
    # Movie order is by date_added DESC. For consistent testing, check for presence or sort.
    titles_in_list = {m[1] for m in movies} # Get a set of titles
    assert movie1_data['Title'] in titles_in_list
    assert movie2_data['Title'] in titles_in_list
    assert "Other User Movie" not in titles_in_list

# --- Delete Tests ---
def test_delete_all_movies_for_user():
    user_id = get_test_user_id()
    other_user_id = db.add_user("anotherdeleter", "pass")

    db.add_movie(user_id, {'imdbID': 'tt001', 'Title': 'User1 Movie1', 'Year': 'Y', 'Director': 'D', 'Genre': 'G', 'Poster': 'P'}, "Watched")
    db.add_movie(user_id, {'imdbID': 'tt002', 'Title': 'User1 Movie2', 'Year': 'Y', 'Director': 'D', 'Genre': 'G', 'Poster': 'P'}, "Want to Watch")
    db.add_movie(other_user_id, {'imdbID': 'tt003', 'Title': 'OtherUser Movie1', 'Year': 'Y', 'Director': 'D', 'Genre': 'G', 'Poster': 'P'}, "Watched")

    assert len(db.get_all_movies(user_id)) == 2
    assert len(db.get_all_movies(other_user_id)) == 1

    deleted_count = db.delete_all_movies_for_user(user_id)
    assert deleted_count == 2

    assert len(db.get_all_movies(user_id)) == 0
    assert len(db.get_all_movies(other_user_id)) == 1

def test_delete_all_movies_for_user_with_no_movies():
    user_id = get_test_user_id()
    # Ensure user's list is empty first
    db.delete_all_movies_for_user(user_id)
    assert len(db.get_all_movies(user_id)) == 0

    deleted_count = db.delete_all_movies_for_user(user_id)
    assert deleted_count == 0
    assert len(db.get_all_movies(user_id)) == 0
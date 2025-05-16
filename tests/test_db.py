import sqlite3
import pytest
import os
from .. import db

# Use an in-memory database for testing, it's faster and cleaner
TEST_DATABASE_NAME = ':memory:'

# Override the database name in the db module for testing
@pytest.fixture(autouse=True)
def set_test_database(monkeypatch):
    monkeypatch.setattr(db, 'DATABASE_NAME', TEST_DATABASE_NAME)
    # Ensure the table is created for each test that needs it
    db.create_database()

def test_create_database():
    # Since set_test_database fixture runs automatically and calls create_database,
    # we just need to verify the table exists in the in-memory db.
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movies';")
    table_exists = cursor.fetchone() is not None
    conn.close()
    assert table_exists

def test_add_movie():
    movie_data = {
        'imdbID': 'tt0133093',
        'Title': 'The Matrix',
        'Year': '1999',
        'Director': 'Lana Wachowski, Lilly Wachowski',
        'Genre': 'Action, Sci-Fi',
        'Poster': 'N/A',
        # date_added is generated in the function, no need to include here
    }
    db.add_movie(movie_data) # Add the movie

    # Verify it was added
    retrieved_movie = db.get_movie_by_imdb_id(movie_data['imdbID'])
    assert retrieved_movie is not None
    assert retrieved_movie[1] == movie_data['Title'] # Check title

def test_add_movie_ignore_duplicate():
    movie_data_1 = {
        'imdbID': 'tt0133093',
        'Title': 'The Matrix',
        'Year': '1999',
        'Director': '...',
        'Genre': '...',
        'Poster': '...',
    }
    movie_data_2 = {
        'imdbID': 'tt0133093', # Same IMDb ID
        'Title': 'The Matrix Reloaded', # Different title, but should be ignored
        'Year': '2003',
        'Director': '...',
        'Genre': '...',
        'Poster': '...',
    }

    db.add_movie(movie_data_1) # Add the first version
    db.add_movie(movie_data_2) # Try to add the duplicate

    # Verify only one record exists for this IMDb ID
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies WHERE imdb_id = ?;", ('tt0133093',))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1 # Only the first insert should have counted

    # Verify the data is from the first insert (due to IGNORE)
    retrieved_movie = db.get_movie_by_imdb_id(movie_data_1['imdbID'])
    assert retrieved_movie is not None
    assert retrieved_movie[1] == movie_data_1['Title'] # Title should be 'The Matrix', not 'The Matrix Reloaded'

def test_get_all_movies_empty():
    movies = db.get_all_movies()
    assert len(movies) == 0

def test_get_all_movies_with_data():
    movie_data_1 = {'imdbID': 'tt0133093', 'Title': 'Matrix 1', 'Year': '1999', 'Director': 'A', 'Genre': 'SF', 'Poster': 'P1'}
    movie_data_2 = {'imdbID': 'tt0234215', 'Title': 'Matrix 2', 'Year': '2003', 'Director': 'A', 'Genre': 'SF', 'Poster': 'P2'}

    db.add_movie(movie_data_1)
    db.add_movie(movie_data_2)

    all_movies = db.get_all_movies()
    assert len(all_movies) == 2

    # Basic check if data looks correct
    titles = [m[1] for m in all_movies]
    assert 'Matrix 1' in titles
    assert 'Matrix 2' in titles
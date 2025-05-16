import pytest
from unittest.mock import patch, MagicMock
import sqlite3 # Not strictly needed if only using db.py functions
import os
import tempfile # For temporary database file
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db
import api_client
from passlib.hash import bcrypt # For setting up test user password

DEFAULT_TEST_MOVIE_STATUS = "Want to Watch"

# Sample successful API response (simplified for brevity if full details not needed for every field)
SUCCESS_RESPONSE_JSON = {
    "Title": "Inception", "Year": "2010", "Director": "Christopher Nolan",
    "Genre": "Action, Adventure, Sci-Fi", "imdbID": "tt1375666", "Poster": "N/A",
    "Response": "True"
}

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Sets up a temporary file database, mocks API key, and creates a default user.
    Yields the user_id for use in tests. Cleans up after tests.
    """
    # Mock api_client.OMDB_API_KEY directly
    monkeypatch.setattr(api_client, 'OMDB_API_KEY', 'fake_integration_test_key')

    # Setup temporary database file
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    TEST_DB_PATH = temp_db_file.name
    temp_db_file.close()

    monkeypatch.setattr(db, 'DATABASE_NAME', TEST_DB_PATH)
    db.create_database() # Initialize schema in the temp file

    # Add a default user for integration tests
    test_username = "integration_test_user"
    test_password = "testpass" # Not strictly needed for this test if user_id is yielded
    user_id = db.add_user(test_username, test_password)
    if not user_id:
        pytest.fail(f"Failed to create user '{test_username}' in integration test setup.")
    
    yield user_id # Provide user_id to the test

    # Teardown: remove the temporary database file
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@patch('requests.get') # Mock the external API call
def test_fetch_and_save_workflow_for_user(mock_get, setup_test_environment):
    # setup_test_environment fixture provides the test user_id
    test_user_id = setup_test_environment

    # Configure the mock API response
    mock_api_response = MagicMock()
    mock_api_response.status_code = 200
    mock_api_response.json.return_value = SUCCESS_RESPONSE_JSON
    mock_api_response.raise_for_status.return_value = None
    mock_get.return_value = mock_api_response

    movie_title_to_fetch = "Inception"

    # 1. Fetch movie details from API
    fetched_movie_data = api_client.get_movie_details(movie_title_to_fetch)

    assert fetched_movie_data is not None
    assert fetched_movie_data['imdbID'] == SUCCESS_RESPONSE_JSON['imdbID']
    mock_get.assert_called_once_with(
        'https://www.omdbapi.com/',
        params={'t': movie_title_to_fetch, 'apikey': 'fake_integration_test_key', 'plot': 'short', 'r': 'json'}
    )

    # 2. Save the fetched movie data to the DB for the test user with a status
    add_success = db.add_movie(test_user_id, fetched_movie_data, DEFAULT_TEST_MOVIE_STATUS)
    assert add_success is True

    # 3. Verify data is in the DB for the test user
    user_movies = db.get_all_movies(test_user_id)
    assert len(user_movies) == 1
    
    saved_movie = user_movies[0]
    # Tuple structure from db.get_all_movies:
    # (imdb_id, title, year, director, genre, poster_url, status, date_added)
    assert saved_movie[0] == SUCCESS_RESPONSE_JSON['imdbID']    # imdb_id
    assert saved_movie[1] == SUCCESS_RESPONSE_JSON['Title']     # title
    assert saved_movie[6] == DEFAULT_TEST_MOVIE_STATUS        # status

    # Try adding the same movie again for the same user - should be ignored
    add_again_success = db.add_movie(test_user_id, fetched_movie_data, "Watched") # different status
    assert add_again_success is False, "Adding a duplicate movie for the same user should be ignored"

    user_movies_after_reattempt = db.get_all_movies(test_user_id)
    assert len(user_movies_after_reattempt) == 1 # Still only one movie
    # The status should remain as it was when first added, as duplicates are ignored
    assert user_movies_after_reattempt[0][6] == DEFAULT_TEST_MOVIE_STATUS
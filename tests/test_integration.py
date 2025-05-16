import pytest
from unittest.mock import patch, MagicMock
import sqlite3
from .. import db # Assuming db.py is in the parent directory
from .. import api_client # Assuming api_client.py is in the parent directory
import os
from passlib.hash import bcrypt # For setting up test user password

# Use an in-memory database for testing db interactions
TEST_DATABASE_NAME = ':memory:'

# Sample successful API response (same as test_api_client)
SUCCESS_RESPONSE_JSON = {
    "Title": "Inception",
    "Year": "2010",
    "Rated": "PG-13",
    "Released": "16 Jul 2010",
    "Runtime": "148 min",
    "Genre": "Action, Adventure, Sci-Fi",
    "Director": "Christopher Nolan",
    "Writer": "Christopher Nolan",
    "Actors": "Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page",
    "Plot": "A thief who steals corporate secrets...",
    "Language": "English, Japanese, French",
    "Country": "United States, United Kingdom",
    "Awards": "Won 4 Oscars. 157 other wins.",
    "Poster": "https://m.media-amazon.com/images/M/...",
    "Ratings": [{"Source": "Internet Movie Database", "Value": "8.8/10"}],
    "Metascore": "74",
    "imdbRating": "8.8",
    "imdbVotes": "2,500,000",
    "imdbID": "tt1375666",
    "Type": "movie",
    "DVD": "07 Dec 2010",
    "BoxOffice": "$292,576,195",
    "Production": "N/A",
    "Website": "N/A",
    "Response": "True" # IMPORTANT for OMDb success
}


# Fixture to setup the test environment: in-memory database, mock API key, add a test user
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    # Set test database name for db module
    monkeypatch.setattr(db, 'DATABASE_NAME', TEST_DATABASE_NAME)
    # Create the table
    db.create_database()

    # Set fake API key for api_client module
    monkeypatch.setattr(api_client, 'OMDB_API_KEY', 'fake_test_key')
    # Mock st.secrets.get as api_client tries to use it
    monkeypatch.setattr(api_client.st, 'secrets', MagicMock())
    api_client.st.secrets.get.return_value = 'fake_test_key'

    # Add a default user for integration tests
    test_hashed_password = bcrypt.hash("testpass")
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", ("testuser", test_hashed_password))
    conn.commit()
    conn.close()

    # Return the test user ID for the test function if needed
    user_id, _ = db.find_user_by_username("testuser")
    yield user_id # Use yield to make it a teardown fixture if needed, though in-memory clears automatically


@patch('requests.get') # Mock the external API call
def test_fetch_and_save_workflow_for_user(mock_get, setup_test_environment):
    # The setup_test_environment fixture provides the test user ID
    test_user_id = setup_test_environment

    # Configure the mock API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SUCCESS_RESPONSE_JSON
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    movie_title = "Inception"

    # Simulate the core logic flow that Streamlit app would trigger:
    # 1. Fetch from API
    movie_data = api_client.get_movie_details(movie_title)

    # Ensure API call was successful in test setup
    assert movie_data is not None
    mock_get.assert_called_once() # Verify API was called

    # 2. Save to DB FOR THE TEST USER
    success = db.add_movie(test_user_id, movie_data) # Pass user_id
    assert success is True

    # 3. Verify data is in the DB FOR THE TEST USER
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    # Select by both user_id and imdb_id
    cursor.execute("SELECT COUNT(*) FROM movies WHERE user_id = ? AND imdb_id = ?;",
                   (test_user_id, SUCCESS_RESPONSE_JSON['imdbID']))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1 # Ensure one record was inserted for this user

    # Verify retrieval using the db function
    user_movies = db.get_all_movies(test_user_id) # Get movies for the test user
    assert len(user_movies) == 1 # Should be one movie for this user
    assert user_movies[0][1] == SUCCESS_RESPONSE_JSON['Title'] # Verify title of the retrieved movie
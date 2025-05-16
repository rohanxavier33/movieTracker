import pytest
from unittest.mock import patch, MagicMock
import sqlite3
from .. import db
from .. import api_client
import os

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


# Fixture to setup the in-memory database and mock API key for tests
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


@patch('requests.get') # Mock the external API call
def test_fetch_and_save_workflow(mock_get):
    # Configure the mock API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SUCCESS_RESPONSE_JSON
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    movie_title = "Inception"

    # Simulate the core logic flow that Streamlit app would trigger:
    # Fetch from API
    movie_data = api_client.get_movie_details(movie_title)

    # Ensure API call was successful in test setup
    assert movie_data is not None
    mock_get.assert_called_once() # Verify API was called

    # Save to DB
    db.add_movie(movie_data)

    # Verify data is in the DB
    conn = sqlite3.connect(TEST_DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies WHERE imdb_id = ?;", (SUCCESS_RESPONSE_JSON['imdbID'],))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1 # Ensure one record was inserted

    retrieved_movie = db.get_movie_by_imdb_id(SUCCESS_RESPONSE_JSON['imdbID'])
    assert retrieved_movie is not None
    assert retrieved_movie[1] == SUCCESS_RESPONSE_JSON['Title'] # Verify title
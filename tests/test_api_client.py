import pytest
import requests
from unittest.mock import patch, MagicMock
import sys
import os # Required for sys.path modification
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import api_client

# Sample successful API response
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

# Sample 'Movie not found' API response
NOT_FOUND_RESPONSE_JSON = {
    "Response": "False",
    "Error": "Movie not found!"
}

@pytest.fixture
def mock_api_key_present(monkeypatch):
    """Mocks api_client.OMDB_API_KEY to simulate a key being present."""
    monkeypatch.setattr(api_client, 'OMDB_API_KEY', 'fake_test_key')

@pytest.fixture
def mock_api_key_missing(monkeypatch):
    """Mocks api_client.OMDB_API_KEY to simulate a key being missing."""
    monkeypatch.setattr(api_client, 'OMDB_API_KEY', None)


@patch('requests.get')
def test_get_movie_details_success(mock_get, mock_api_key_present):
    # mock_api_key_present fixture ensures api_client.OMDB_API_KEY is set
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SUCCESS_RESPONSE_JSON
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    title = "Inception"
    movie_data = api_client.get_movie_details(title)

    mock_get.assert_called_once_with(
        'https://www.omdbapi.com/', # Using the HTTPS URL from api_client.py
        params={'t': title, 'apikey': 'fake_test_key', 'plot': 'short', 'r': 'json'}
    )

    assert movie_data is not None
    assert movie_data['Title'] == "Inception"
    assert movie_data['imdbID'] == "tt1375666"
    assert movie_data['Director'] == "Christopher Nolan"


@patch('requests.get')
def test_get_movie_details_not_found(mock_get, mock_api_key_present):
    # mock_api_key_present fixture ensures api_client.OMDB_API_KEY is set
    mock_response = MagicMock()
    mock_response.status_code = 200 # OMDb API returns 200 even for "Movie not found"
    mock_response.json.return_value = NOT_FOUND_RESPONSE_JSON
    mock_response.raise_for_status.return_value = None # No HTTPError raised by response.raise_for_status()
    mock_get.return_value = mock_response

    title = "Movie That Does Not Exist 12345"
    movie_data = api_client.get_movie_details(title)

    mock_get.assert_called_once_with(
        'https://www.omdbapi.com/',
        params={'t': title, 'apikey': 'fake_test_key', 'plot': 'short', 'r': 'json'}
    )
    assert movie_data is None

@patch('requests.get')
def test_get_movie_details_http_error(mock_get, mock_api_key_present):
    # mock_api_key_present fixture ensures api_client.OMDB_API_KEY is set
    mock_get.side_effect = requests.exceptions.RequestException("Simulated HTTP error")

    title = "Any Movie"
    movie_data = api_client.get_movie_details(title)

    mock_get.assert_called_once_with(
        'https://www.omdbapi.com/',
        params={'t': title, 'apikey': 'fake_test_key', 'plot': 'short', 'r': 'json'}
    )
    assert movie_data is None

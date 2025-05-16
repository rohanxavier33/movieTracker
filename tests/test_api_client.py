import pytest
import requests
from unittest.mock import patch, MagicMock
from .. import api_client 

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

# Fixture to ensure API key is set for tests that need it
@pytest.fixture(autouse=True)
def set_api_key_for_tests(monkeypatch):
     monkeypatch.setattr(api_client, 'OMDB_API_KEY', 'fake_test_key')
     # Mock st.secrets.get to return the fake key when needed by api_client
     monkeypatch.setattr(api_client.st, 'secrets', MagicMock())
     api_client.st.secrets.get.return_value = 'fake_test_key'


@patch('requests.get') # Mock the requests.get function
def test_get_movie_details_success(mock_get):
    # Configure the mock to return a successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SUCCESS_RESPONSE_JSON
    mock_response.raise_for_status.return_value = None # requests.get.raise_for_status returns None on success
    mock_get.return_value = mock_response

    title = "Inception"
    movie_data = api_client.get_movie_details(title)

    # Assert that requests.get was called with the correct URL and params
    mock_get.assert_called_once_with(
        api_client.OMDB_BASE_URL,
        params={'t': title, 'apikey': 'fake_test_key', 'plot': 'short', 'r': 'json'}
    )

    # Assert the function returned the expected data (or at least its structure/key fields)
    assert movie_data is not None
    assert movie_data['Title'] == "Inception"
    assert movie_data['imdbID'] == "tt1375666"
    assert movie_data['Director'] == "Christopher Nolan" # Check a few fields


@patch('requests.get')
def test_get_movie_details_not_found(mock_get):
    # Configure the mock to return a 'not found' response from OMDb
    mock_response = MagicMock()
    mock_response.status_code = 200 # Still a 200 HTTP status, but OMDb reports not found
    mock_response.json.return_value = NOT_FOUND_RESPONSE_JSON
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    title = "Movie That Does Not Exist 12345"
    movie_data = api_client.get_movie_details(title)

    # Assert that requests.get was called
    mock_get.assert_called_once()

    # Assert the function returned None because the movie was not found
    assert movie_data is None

@patch('requests.get')
def test_get_movie_details_http_error(mock_get):
    # Configure the mock to raise an HTTPError
    mock_get.side_effect = requests.exceptions.RequestException("Simulated HTTP error")

    title = "Any Movie"
    movie_data = api_client.get_movie_details(title)

    # Assert that requests.get was called
    mock_get.assert_called_once()

    # Assert the function returned None due to the error
    assert movie_data is None

def test_get_movie_details_no_api_key(monkeypatch):
     # Temporarily remove the API key for this test
     monkeypatch.setattr(api_client, 'OMDB_API_KEY', None)
     api_client.st.secrets.get.return_value = None # Ensure st.secrets also reports no key

     title = "Any Movie"
     movie_data = api_client.get_movie_details(title)

     # Assert the function returned None immediately
     assert movie_data is None
     # Assert requests.get was NOT called
     with pytest.raises(AssertionError): # Check that assert_called_once fails
         requests.get.assert_called_once() # Use the original requests.get to assert it wasn't called
import requests
import logging
import os
from dotenv import load_dotenv

# Configure basic logging (can be shared or configured in main script)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

OMDB_API_KEY = os.getenv('OMDB_KEY')

OMDB_BASE_URL = 'https://www.omdbapi.com/'

def get_movie_details(title):
    """Fetches movie details from OMDb API by title."""

    params = {
        't': title,     # Search by title
        'apikey': OMDB_API_KEY,
        'plot': 'short', # Get short plot description (optional)
        'r': 'json'      # Response format
    }

    logging.info(f"Attempting to fetch movie details for: {title} from OMDb API")
    # Log an 'event' of an API call attempt
    logging.info(f"EVENT: OMDbAPICall - Query: {title}")

    try:
        response = requests.get(OMDB_BASE_URL, params=params)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        data = response.json()

        # OMDb API returns 'Response': 'True' on success, 'False' on failure (e.g., movie not found)
        if data.get('Response') == 'True':
            logging.info(f"Successfully fetched details for: {data.get('Title')}")
            # Log an 'event' of a successful API fetch
            logging.info(f"EVENT: OMDbAPISuccess - Title: {data.get('Title')}, IMDbID: {data.get('imdbID')}")
            return data # Return the dictionary containing movie data
        else:
            logging.warning(f"OMDb API did not find movie '{title}' or returned error: {data.get('Error')}")
            # Log an 'event' of an API fetch failure
            logging.info(f"EVENT: OMDbAPIFailure - Query: {title}, Error: {data.get('Error', 'Unknown')}")
            return None # Movie not found or API error reported in the response

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching movie '{title}' from OMDb API: {e}")
        # Log an 'event' of a network/request error
        logging.info(f"EVENT: OMDbAPIRequestError - Query: {title}, Error: {e}")
        return None # Handle request errors (network issues, etc.)
    except Exception as e:
         logging.error(f"Unexpected error processing OMDb API response for '{title}': {e}")
         # Log an 'event' of an unexpected error
         logging.info(f"EVENT: OMDbAPIUnexpectedError - Query: {title}, Error: {e}")
         return None
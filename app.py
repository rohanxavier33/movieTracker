import streamlit as st
import pandas as pd
import db 
import api_client
import logging # Python's built-in logging

# --- Database Initialization ---
# Ensure the database and table exist when the app starts
db.create_database()

# --- Streamlit UI ---
st.set_page_config(page_title="Movie Tracker", layout="wide")

st.title("Movie Tracker")

# --- Add Movie Form ---
st.header("Add a New Movie")

with st.form("add_movie_form", clear_on_submit=True):
    movie_title = st.text_input("Enter Movie Title", help="Type the full title, e.g., 'Inception'")
    submitted = st.form_submit_button("Fetch & Add Movie")

    if submitted:
        if movie_title:
            # Fetch data from API
            movie_data = api_client.get_movie_details(movie_title)

            if movie_data:
                # API call successful, now extract and add to DB
                # We'll add a default status for new entries
                movie_data['status'] = 'Want to Watch' # Default status
                db.add_movie(movie_data) # Save data via db.py

                st.success(f"Successfully added '{movie_data.get('Title')}' to your tracker!")
                # Log the Streamlit UI action as an event
                logging.info(f"EVENT: UIMovieAdded - Title: {movie_data.get('Title')}")

            else:
                # API call failed or movie not found (api_client handles logging errors)
                st.warning(f"Could not find details for '{movie_title}'. Please check the title.")
                logging.warning(f"UI Action: Failed to add movie '{movie_title}' - API lookup failed.")
                # Log the UI action failure
                logging.info(f"EVENT: UIMovieAddFailed - Title: {movie_title}, Reason: API Lookup Failed")

        else:
            st.warning("Please enter a movie title.")
            logging.warning("UI Action: Attempted to add movie with empty title.")
            logging.info(f"EVENT: UIMovieAddFailed - Title: [Empty], Reason: No Title Input")


# --- Movie List and Reporting ---
st.header("My Movie List")

# Fetch all movies from the database
# db.get_all_movies() returns a list of tuples:
# (imdb_id, title, year, director, genre, poster_url, date_added)
all_movies_data = db.get_all_movies()

if all_movies_data:
    # Convert list of tuples to pandas DataFrame for easier display and filtering
    df = pd.DataFrame(all_movies_data, columns=["IMDb ID", "Title", "Year", "Director", "Genre", "Poster URL", "Date Added"])

    # Basic Data Analyzer / Reporting
    st.subheader(f"Tracking {len(df)} Movies Total")

    # Simple Filter
    search_query = st.text_input("Filter movies", help="Search by title, director, or genre")
    if search_query:
        df_filtered = df[
            df.apply(lambda row: search_query.lower() in row.astype(str).str.lower().str.cat(), axis=1)
        ]
        st.dataframe(df_filtered)
        logging.info(f"UI Action: Filtered movie list with query '{search_query}'. Displayed {len(df_filtered)} movies.")
        logging.info(f"EVENT: UIFilterApplied - Query: {search_query}")
    else:
        # Display the full DataFrame if no filter
        st.dataframe(df)
        logging.info("UI Action: Displayed full movie list.")

else:
    st.info("Your movie list is empty. Add movies using the form above!")
    logging.info("UI Action: Displayed empty movie list message.")

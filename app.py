import streamlit as st
import pandas as pd
import db  # Import your database functions
import api_client  # Import your API client functions
import logging  # Python's built-in logging
from passlib.hash import bcrypt  # Import bcrypt for password verification

# Configure logging for the app - this will be the primary config
# if app.py is the entry point.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

# Ensure database is set up when the app starts
db.create_database()

# --- Session State Management ---
# Initialize session state variables if they don't exist
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'auth_error' not in st.session_state:
    st.session_state.auth_error = False # To display auth errors once

# --- Authentication Functions ---

def authenticate(username, password):
    """Basic authentication against the database."""
    user_id, hashed_password = db.find_user_by_username(username)

    if user_id and hashed_password:
        # Verify the provided password against the hashed password from the DB
        try:
            if bcrypt.verify(password, hashed_password):
                logging.info(f"Authentication successful for user: {username}")
                logging.info(f"EVENT: AuthenticationSuccess - Username: {username}, UserID: {user_id}")
                return user_id, username
            else:
                logging.warning(f"Authentication failed: Incorrect password for user: {username}")
                logging.info(f"EVENT: AuthenticationFailure - Username: {username}, Reason: IncorrectPassword")
                return None, None
        except ValueError: # Handles issues like "not a valid bcrypt hash"
            logging.warning(f"Authentication failed: Invalid hash for user: {username}")
            logging.info(f"EVENT: AuthenticationFailure - Username: {username}, Reason: InvalidHash")
            return None, None
    else:
        logging.warning(f"Authentication failed: User not found: {username}")
        logging.info(f"EVENT: AuthenticationFailure - Username: {username}, Reason: UserNotFound")
        return None, None

def create_account(username, password):
    """Attempts to create a new user account."""
    if not username or not password:
        st.error("Username and password cannot be empty.")
        return False

    # Add basic validation (avoid spaces, etc. - enhance as needed)
    if " " in username:
        st.error("Username cannot contain spaces.")
        return False
    if len(password) < 4: # Basic password length
        st.error("Password must be at least 4 characters long.")
        return False

    user_id = db.add_user(username, password) # db.add_user handles duplicates

    if user_id:
        st.success(f"Account created successfully for {username}! Please log in.")
        return True
    else:
        # db.add_user logs the warning for duplicate username
        st.error(f"Could not create account for {username}. Username might already exist.")
        return False

def logout():
    """Logs out the current user."""
    logging.info(f"Logging out user: {st.session_state.username} (ID: {st.session_state.user_id})")
    logging.info(f"EVENT: Logout - Username: {st.session_state.username}, UserID: {st.session_state.user_id}")
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.auth_error = False # Clear any previous error
    st.rerun() # Rerun the app to show the login screen

# --- Streamlit UI ---
st.set_page_config(page_title="Movie Tracker", layout="wide")

st.title("Movie Tracker")

# --- Login/Logout Logic and UI ---

if st.session_state.user_id is None:
    # --- Show Login/Create Account Forms ---
    st.header("Login or Create Account")

    # Use columns to potentially place forms side-by-side
    col1, col2 = st.columns(2)

    with col1:
        with st.form("login_form"):
            st.subheader("Existing User Login")
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            login_button = st.form_submit_button("Login")

            if login_button:
                user_id, username = authenticate(login_username, login_password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.auth_error = False # Clear error on successful login
                    st.rerun() # Rerun the app to show the main content
                else:
                    st.session_state.auth_error = True # Set error flag
                    # Error displayed below form

        # Display auth error outside the form so it persists until next submission
        if st.session_state.auth_error:
            st.error("Login failed. Please check your username and password.")


    with col2:
        with st.form("create_account_form"):
            st.subheader("Create New Account")
            create_username = st.text_input("Choose Username", key="create_username")
            create_password = st.text_input("Choose Password", type="password", key="create_password")
            create_button = st.form_submit_button("Create Account")

            if create_button:
                # create_account function handles validation and messages
                create_account(create_username, create_password)


else:
    # --- User is Logged In - Show Main App Content ---
    st.sidebar.write(f"Logged in as **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        logout()

    # --- Add Movie Form ---
    st.header("Add a New Movie to Your List")

    with st.form("add_movie_form", clear_on_submit=True):
        movie_title = st.text_input("Enter Movie Title", help="Type the full title, e.g., 'Inception'")
        movie_status = st.selectbox("Status", ("Want to Watch", "Watched"), key="movie_status_select")
        submitted = st.form_submit_button("Fetch & Add Movie")

        if submitted:
            if movie_title:
                # 1. Fetch data from API
                movie_data_from_api = api_client.get_movie_details(movie_title)

                if movie_data_from_api:
                    # API call successful, now extract and add to DB
                    success = db.add_movie(st.session_state.user_id, movie_data_from_api, movie_status)

                    if success:
                        st.success(f"Successfully added '{movie_data_from_api.get('Title')}' as '{movie_status}' to your list!")
                        # Log the Streamlit UI action as an event
                        logging.info(f"EVENT: UIMovieAdded - UserID: {st.session_state.user_id}, Title: {movie_data_from_api.get('Title')}, Status: {movie_status}")
                    else:
                        # db.add_movie logs the reason (e.g., ignored duplicate for this user)
                        st.info(f"'{movie_data_from_api.get('Title')}' is already in your list.")
                        logging.warning(f"UI Action: Could not add movie '{movie_data_from_api.get('Title')}' for user {st.session_state.user_id} - db.add_movie failed/ignored (likely duplicate for user).")
                        # Specific event logged inside db.add_movie

                else:
                    # API call failed or movie not found (api_client handles logging errors)
                    st.warning(f"Could not find details for '{movie_title}'. Please check the title.")
                    logging.warning(f"UI Action: Failed to add movie '{movie_title}' for user {st.session_state.user_id} - API lookup failed.")
                    logging.info(f"EVENT: UIMovieAddFailed - UserID: {st.session_state.user_id}, Title: {movie_title}, Reason: API Lookup Failed")

            else:
                st.warning("Please enter a movie title.")
                logging.warning(f"UI Action: Attempted to add movie with empty title for user {st.session_state.user_id}.")
                logging.info(f"EVENT: UIMovieAddFailed - UserID: {st.session_state.user_id}, Title: [Empty], Reason: No Title Input")


    # --- Movie List and Reporting ---
    st.header("Your Movie List")

    # Fetch movies only for the logged-in user
    # db.get_all_movies() returns a list of tuples:
    # (imdb_id, title, year, director, genre, poster_url, status, date_added)
    user_movies_data = db.get_all_movies(st.session_state.user_id) # Pass the user_id!

    if user_movies_data:
        # Convert list of tuples to pandas DataFrame for easier display and filtering
        df = pd.DataFrame(user_movies_data, columns=["IMDb ID", "Title", "Year", "Director", "Genre", "Poster URL", "Status", "Date Added"])

        # Basic Data Analyzer / Reporting
        st.subheader(f"Tracking {len(df)} Movies Total for {st.session_state.username}")

        # Simple Filter
        search_query = st.text_input("Filter movies", help="Search by title, director, genre, or status", key="movie_filter_input")
        if search_query:
            df_filtered = df[
                df.apply(lambda row: search_query.lower() in row.astype(str).str.lower().str.cat(sep='|'), axis=1)
            ]
            st.dataframe(df_filtered, use_container_width=True, hide_index=True)
            logging.info(f"UI Action: Filtered movie list with query '{search_query}' for user {st.session_state.user_id}. Displayed {len(df_filtered)} movies.")
            logging.info(f"EVENT: UIFilterApplied - UserID: {st.session_state.user_id}, Query: {search_query}")
        else:
            # Display the full DataFrame if no filter
            st.dataframe(df, use_container_width=True, hide_index=True)
            logging.info(f"UI Action: Displayed full movie list for user {st.session_state.user_id}.")


        # --- Clear List Button ---
        st.subheader("Manage Your List")
        # Add a confirmation checkbox before showing the button
        confirm_clear = st.checkbox("Yes, I want to clear my entire movie list.")
        if confirm_clear:
            if st.button("Clear My Entire List", type="secondary"): # type="secondary" gives it a different color
                deleted_count = db.delete_all_movies_for_user(st.session_state.user_id) # Pass the user_id!
                if deleted_count >= 0: # delete_all_movies_for_user returns count or -1 on error (changed to 0 for simplicity)
                    st.success(f"Successfully cleared {deleted_count} movies from your list.")
                    # Log the UI action as an event
                    logging.info(f"EVENT: UIClearList - UserID: {st.session_state.user_id}, DeletedCount: {deleted_count}")
                    st.rerun() # Rerun to update the displayed list
                else: # Should ideally not happen if delete_all_movies_for_user returns 0 on SQL error
                    st.error("An error occurred while trying to clear your list.")
                    logging.error(f"UI Action: Failed to clear list for user {st.session_state.user_id}.")
                    # Specific event logged inside db.delete_all_movies_for_user


    else:
        st.info("Your movie list is empty. Add movies using the form above!")
        logging.info(f"UI Action: Displayed empty movie list message for user {st.session_state.user_id}.")

    st.sidebar.header("About")
    st.sidebar.info(
        "This is a Movie Tracker app. "
        "You can add movies you've watched or want to watch. "
        "Movie details are fetched from OMDb API."
    )
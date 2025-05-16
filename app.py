# app.py
import streamlit as st
import pandas as pd
import db
import api_client
import logging
from passlib.hash import bcrypt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
db.create_database() # Ensures DB is created with the new user_rating column

# --- Session State Management & Auth Functions (authenticate, create_account, logout) ---
# ... (These functions remain largely unchanged from your previous version) ...
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'auth_error' not in st.session_state:
    st.session_state.auth_error = False 

def authenticate(username, password):
    user_id, hashed_password = db.find_user_by_username(username)
    if user_id and hashed_password:
        try:
            if bcrypt.verify(password, hashed_password):
                logging.info(f"Authentication successful for user: {username}")
                logging.info(f"EVENT: AuthenticationSuccess - Username: {username}, UserID: {user_id}")
                return user_id, username
            else:
                logging.warning(f"Authentication failed: Incorrect password for user: {username}")
                logging.info(f"EVENT: AuthenticationFailure - Username: {username}, Reason: IncorrectPassword")
                return None, None
        except ValueError: 
            logging.warning(f"Authentication failed: Invalid hash for user: {username}")
            logging.info(f"EVENT: AuthenticationFailure - Username: {username}, Reason: InvalidHash")
            return None, None
    else:
        logging.warning(f"Authentication failed: User not found: {username}")
        logging.info(f"EVENT: AuthenticationFailure - Username: {username}, Reason: UserNotFound")
        return None, None

def create_account(username, password):
    if not username or not password:
        st.error("Username and password cannot be empty.")
        return False
    if " " in username:
        st.error("Username cannot contain spaces.")
        return False
    if len(password) < 4: 
        st.error("Password must be at least 4 characters long.")
        return False
    user_id = db.add_user(username, password)
    if user_id:
        st.success(f"Account created successfully for {username}! Please log in.")
        return True
    else:
        st.error(f"Could not create account for {username}. Username might already exist.")
        return False

def logout():
    logging.info(f"Logging out user: {st.session_state.username} (ID: {st.session_state.user_id})")
    logging.info(f"EVENT: Logout - Username: {st.session_state.username}, UserID: {st.session_state.user_id}")
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.auth_error = False
    # Clear editor states if they exist
    if "watched_movies_editor" in st.session_state:
        del st.session_state.watched_movies_editor
    st.rerun()

st.set_page_config(page_title="Simple Movie Tracker", layout="wide")
st.title("🎬 Simple Movie Tracker")

if st.session_state.user_id is None:
    # --- Login/Create Account Forms ---
    st.header("Login or Create Account")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("login_form"):
            st.subheader("Existing User Login")
            login_username = st.text_input("Username", key="login_username_main") # Changed key
            login_password = st.text_input("Password", type="password", key="login_password_main") # Changed key
            login_button = st.form_submit_button("Login")
            if login_button:
                user_id, username = authenticate(login_username, login_password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.auth_error = False
                    st.rerun()
                else:
                    st.session_state.auth_error = True
        if st.session_state.auth_error:
            st.error("Login failed. Please check your username and password.")
    with col2:
        with st.form("create_account_form"):
            st.subheader("Create New Account")
            create_username = st.text_input("Choose Username", key="create_username_main") # Changed key
            create_password = st.text_input("Choose Password", type="password", key="create_password_main") # Changed key
            create_button = st.form_submit_button("Create Account")
            if create_button:
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
                movie_data_from_api = api_client.get_movie_details(movie_title)
                if movie_data_from_api:
                    success = db.add_movie(st.session_state.user_id, movie_data_from_api, movie_status)
                    if success:
                        st.success(f"Successfully added '{movie_data_from_api.get('Title')}' as '{movie_status}' to your list!")
                        logging.info(f"EVENT: UIMovieAdded - UserID: {st.session_state.user_id}, Title: {movie_data_from_api.get('Title')}, Status: {movie_status}")
                        st.rerun() # Rerun to update lists immediately
                    else:
                        st.info(f"'{movie_data_from_api.get('Title')}' is already in your '{movie_status}' list or another list.")
                else:
                    st.warning(f"Could not find details for '{movie_title}'. Please check the title.")
            else:
                st.warning("Please enter a movie title.")

    # --- Movie Lists ---
    st.divider()
    user_movies_data = db.get_all_movies(st.session_state.user_id)
    
    # Define column names based on what db.get_all_movies returns
    # Order: id, imdb_id, title, year, director, genre, poster_url, status, user_rating, date_added
    df_columns = ["DB ID", "IMDb ID", "Title", "Year", "Director", "Genre", "Poster URL", "Status", "User Rating", "Date Added"]
    
    if user_movies_data:
        df_all_movies = pd.DataFrame(user_movies_data, columns=df_columns)
        
        # Convert User Rating to numeric, coercing errors for robust handling (e.g. if None/NULL)
        df_all_movies["User Rating"] = pd.to_numeric(df_all_movies["User Rating"], errors='coerce')


        df_want_to_watch = df_all_movies[df_all_movies["Status"] == "Want to Watch"].copy()
        df_watched = df_all_movies[df_all_movies["Status"] == "Watched"].copy()

        # --- Filter Input (common for both lists if desired, or separate) ---
        # For simplicity, let's assume a general filter for now, or apply to both
        # search_query = st.text_input("Filter movies in lists", help="Search by title, director, or genre", key="list_filter_input")
        # If implementing search, apply it to df_want_to_watch and df_watched before displaying

    else: # No movies at all
        df_all_movies = pd.DataFrame(columns=df_columns) # Empty DF
        df_want_to_watch = pd.DataFrame(columns=df_columns)
        df_watched = pd.DataFrame(columns=df_columns)

    # --- "Want to Watch" List ---
    st.header("🍿 Want to Watch")
    if not df_want_to_watch.empty:
        config_want_to_watch = {
            "DB ID": None, # Hide DB ID
            "IMDb ID": st.column_config.TextColumn(label="IMDb ID", width="small"),
            "Title": st.column_config.TextColumn(label="Title", width="medium"),
            "Year": st.column_config.TextColumn(label="Year", width="small"),
            "Poster URL": st.column_config.ImageColumn(label="Poster", width="small"),
            "Status": None, # Hide status as it's implied by the list
            "User Rating": None, # Hide rating for "Want to Watch"
            "Date Added": st.column_config.DateColumn(label="Date Added", format="YYYY-MM-DD")
        }
        # Select and reorder columns for display
        display_cols_want = ["Poster URL", "Title", "Year", "Director", "Genre", "IMDb ID", "Date Added"]
        st.dataframe(
            df_want_to_watch[display_cols_want],
            use_container_width=True,
            hide_index=True,
            column_config=config_want_to_watch
        )
    else:
        st.info("No movies in your 'Want to Watch' list yet!")

    st.divider()

    # --- "Watched" List ---
    st.header("✅ Watched Movies")
    if not df_watched.empty:
        config_watched = {
            "DB ID": None, # Hide DB ID
            "IMDb ID": st.column_config.TextColumn(label="IMDb ID", width="small"),
            "Title": st.column_config.TextColumn(label="Title", width="medium"),
            "Year": st.column_config.TextColumn(label="Year", width="small"),
            "Poster URL": st.column_config.ImageColumn(label="Poster", width="small"),
            "Status": None, # Hide status
            "User Rating": st.column_config.NumberColumn(
                label="Your Rating",
                help="Rate 1-5 stars. Click outside cell or press Enter to register edit.",
                min_value=1,
                max_value=5,
                step=1,
                format="%d ⭐" # Displays number with a star; underlying data is int or None
            ),
            "Date Added": st.column_config.DateColumn(label="Date Added", format="YYYY-MM-DD")
        }
        # Select and reorder columns for display
        display_cols_watched = ["Poster URL", "Title", "Year", "User Rating", "Director", "Genre", "IMDb ID", "Date Added"]
        
        # Key for st.data_editor to track its state
        editor_key = "watched_movies_editor"

        # Store the original df_watched in session state to compare against edits if needed
        if 'original_df_watched' not in st.session_state or not st.session_state.original_df_watched.equals(df_watched):
            st.session_state.original_df_watched = df_watched.copy()

        edited_df = st.data_editor(
            df_watched[display_cols_watched], # Pass the subset of columns to display/edit
            column_config=config_watched,
            use_container_width=True,
            hide_index=True,
            key=editor_key,
            num_rows="fixed" # User cannot add/delete rows from this table
        )
        
        # Check for edits using st.session_state and the editor's key
        if editor_key in st.session_state and "edited_rows" in st.session_state[editor_key]:
            edited_rows_info = st.session_state[editor_key]["edited_rows"]
            if edited_rows_info: # If there are actual edits
                # The "Save Ratings" button is one way to confirm changes.
                # For a more immediate feel, we could process on each edit, but that can be chatty.
                # A button is explicit.
                if st.button("Save Rating Changes"):
                    for row_idx_str, changes in edited_rows_info.items():
                        row_idx = int(row_idx_str) # Index in the displayed `edited_df`
                        
                        # To get the DB ID, we need to map this `row_idx` back to the original `df_watched`
                        # or ensure `edited_df` (which is `df_watched[display_cols_watched]`)
                        # still allows access to 'DB ID' even if not displayed.
                        # Better: get DB ID from the full `df_watched` using the index `row_idx`
                        # which corresponds to the row in the dataframe passed to data_editor.
                        movie_db_id = int(df_watched.iloc[row_idx]["DB ID"])

                        if "User Rating" in changes:
                            new_rating = changes["User Rating"]
                            # `st.data_editor` with NumberColumn should provide numeric or None
                            if new_rating is None or pd.isna(new_rating):
                                db.update_movie_rating(movie_db_id, None)
                            else:
                                try:
                                    db.update_movie_rating(movie_db_id, int(new_rating))
                                except ValueError:
                                    logging.error(f"Invalid rating value '{new_rating}' for movie_db_id {movie_db_id}")
                                    st.warning(f"Could not save invalid rating for a movie.")
                                    
                    st.success("Ratings updated!")
                    # Clear the edit state by removing the key from session_state or rerunning
                    del st.session_state[editor_key]["edited_rows"] # Attempt to clear edits
                    st.rerun()
    else:
        st.info("No movies in your 'Watched' list yet!")


    st.divider()
    # --- Clear List Button ---
    if user_movies_data: # Only show if there's any data
        st.subheader("Manage Your Full List")
        confirm_clear = st.checkbox("Yes, I want to clear my entire movie list (Watched and Want to Watch).")
        if confirm_clear:
            if st.button("Clear My Entire List", type="secondary"):
                deleted_count = db.delete_all_movies_for_user(st.session_state.user_id)
                st.success(f"Successfully cleared {deleted_count} movies from your list.")
                logging.info(f"EVENT: UIClearList - UserID: {st.session_state.user_id}, DeletedCount: {deleted_count}")
                st.rerun()

    st.sidebar.header("About")
    st.sidebar.info(
        "This is a Simple Movie Tracker app. Track movies, rate them, and enjoy!"
    )
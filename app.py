# app.py
import streamlit as st
import pandas as pd
import db
import api_client
import logging
from passlib.hash import bcrypt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
db.create_database()

# --- Session State & Auth ---
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
                return user_id, username
            return None, None # Incorrect password
        except ValueError: return None, None # Invalid hash
    return None, None # User not found

def create_account(username, password):
    if not username or not password or len(password) < 4 or " " in username:
        if not username or not password : st.error("Username and password cannot be empty.")
        if " " in username: st.error("Username cannot contain spaces.")
        if len(password) < 4 and password: st.error("Password must be at least 4 characters long.")
        return False
    # db.add_user now returns user_id or None
    user_id = db.add_user(username, password)
    if user_id:
        # st.success is handled by the calling code in this version
        return True 
    else:
        # st.error is handled by the calling code in this version
        return False


def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.auth_error = False
    # Clear editor states
    if "want_to_watch_editor" in st.session_state: del st.session_state.want_to_watch_editor
    if "watched_movies_editor" in st.session_state: del st.session_state.watched_movies_editor
    st.rerun()

st.set_page_config(page_title="Movie Tracker", layout="wide")
st.title("Movie Tracker")

if st.session_state.user_id is None:
    st.header("Login or Create Account")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("login_form"):
            st.subheader("Login")
            login_user = st.text_input("Username", key="login_u") # User's key
            login_pass = st.text_input("Password", type="password", key="login_p") # User's key
            if st.form_submit_button("Login"):
                uid, uname = authenticate(login_user, login_pass)
                if uid:
                    st.session_state.user_id, st.session_state.username = uid, uname
                    st.session_state.auth_error = False
                    st.rerun()
                else:
                    st.session_state.auth_error = True
        if st.session_state.auth_error: st.error("Login failed.")
    with col2:
        with st.form("create_account_form"):
            st.subheader("Create Account")
            create_user = st.text_input("Username", key="create_u") # User's key
            create_pass = st.text_input("Password", type="password", key="create_p") # User's key
            if st.form_submit_button("Create Account"):
                if create_account(create_user, create_pass): # create_account now shows its own messages
                    st.success("Account created! Please log in.") # Keep success message here
                # Errors are handled by create_account or it fails silently if st.error is only in create_account
else:
    # --- LOGGED IN VIEW ---
    st.sidebar.write(f"Logged in as **{st.session_state.username}**")
    if st.sidebar.button("Logout"): logout()

    # --- Add Movie Form ---
    with st.expander("Add a New Movie", expanded=True):
        with st.form("add_movie_form", clear_on_submit=True):
            movie_title = st.text_input("Movie Title")
            movie_status = st.selectbox("Initial Status", ("Want to Watch", "Watched"))
            if st.form_submit_button("Fetch & Add Movie"):
                if movie_title:
                    api_data = api_client.get_movie_details(movie_title)
                    if api_data:
                        if db.add_movie(st.session_state.user_id, api_data, movie_status):
                            st.success(f"Added '{api_data.get('Title')}' to '{movie_status}'.")
                            st.rerun()
                        else:
                            st.warning(f"'{api_data.get('Title')}' might already be in your lists.")
                    else:
                        st.warning(f"Could not find details for '{movie_title}'.")
                else:
                    st.warning("Please enter a movie title.")
    
    st.divider()
    all_movie_data_from_db = db.get_all_movies(st.session_state.user_id)
    df_cols = ["DB ID", "IMDb ID", "Title", "Year", "Director", "Genre", "Poster URL", "Status", "User Rating", "Date Added"]
    
    # FIX: Ensure df_all is always defined
    if all_movie_data_from_db:
        df_all = pd.DataFrame(all_movie_data_from_db, columns=df_cols)
        df_all["Date Added"] = pd.to_datetime(df_all["Date Added"], errors='coerce') # Bug fix for DateColumn
        df_all["User Rating"] = pd.to_numeric(df_all["User Rating"], errors='coerce')
    else:
        df_all = pd.DataFrame(columns=df_cols) # Initialize df_all as empty with correct columns

    # Prepare df_want_to_watch with action columns
    df_want_to_watch_base = df_all[df_all["Status"] == "Want to Watch"].copy()
    df_want_to_watch = df_want_to_watch_base.copy() # Use .copy()
    df_want_to_watch["Mark Watched"] = False
    df_want_to_watch["Delete"] = False
    
    # Prepare df_watched with action columns
    df_watched_base = df_all[df_all["Status"] == "Watched"].copy()
    df_watched = df_watched_base.copy() # Use .copy()
    df_watched["Mark Unwatched"] = False
    df_watched["Delete"] = False


    # --- "Want to Watch" List ---
    st.header("Want to Watch")
    if not df_want_to_watch.empty:
        editor_key_want = "want_to_watch_editor"
        # User's desired display order
        cols_display_want = ["Mark Watched", "Poster URL", "Title", "Year", "Genre", "Director", "Delete"]
        
        config_want = {
            "DB ID": None, "IMDb ID": None, "Status": None, "User Rating": None, "Date Added": None,
            "Mark Watched": st.column_config.CheckboxColumn("Mark Watched?",default=False, width="small"), # Label added
            "Delete": st.column_config.CheckboxColumn("Delete?",default=False, width="small"), # Label added
            "Poster URL": st.column_config.ImageColumn("Poster", width="small"),
            "Title": st.column_config.TextColumn(width="medium", disabled=True),
            "Year": st.column_config.TextColumn(width="small", disabled=True),
            "Genre": st.column_config.TextColumn(disabled=True),
            "Director": st.column_config.TextColumn(disabled=True),
        }
        
        st.caption("Select actions and click 'Confirm Selections' below.")
        # Pass a DataFrame that includes "DB ID" for processing, even if hidden by config.
        # And ensure all columns in cols_display_want are present.
        df_for_editor_want = df_want_to_watch[cols_display_want + ["DB ID"]].copy()

        edited_df_want = st.data_editor(
            df_for_editor_want,
            key=editor_key_want,
            column_config=config_want,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )

        if st.button("Confirm Selections", key="confirm_want_to_watch"): # User's button text, added key
            actions_taken_want = False
            # Iterate through the DataFrame returned by data_editor
            for _index, row_from_editor in edited_df_want.iterrows():
                movie_db_id = int(row_from_editor["DB ID"])
                original_title_for_toast = row_from_editor["Title"]

                # Prioritize Delete action
                if row_from_editor["Delete"]:
                    if db.delete_movie_by_db_id(movie_db_id):
                        st.toast(f"Deleted '{original_title_for_toast}'.")
                        actions_taken_want = True
                    continue # If deleted, no other action for this movie in this pass
                
                if row_from_editor["Mark Watched"]:
                    if db.update_movie_status(movie_db_id, "Watched"):
                        # Rating will be set to NULL by default or can be edited in Watched list
                        db.update_movie_rating(movie_db_id, None) # Explicitly clear rating
                        st.toast(f"Moved '{original_title_for_toast}' to Watched list.")
                        actions_taken_want = True
            
            if actions_taken_want:
                # Clear session state for this editor's edits if necessary
                if editor_key_want in st.session_state and "edited_rows" in st.session_state[editor_key_want]:
                    del st.session_state[editor_key_want]["edited_rows"]
                st.rerun()
            else: st.info("No selections made in 'Want to Watch' list to process.")
    else:
        st.info("Your 'Want to Watch' list is empty!")

    st.divider()

    # --- "Watched" List ---
    st.header("Watched Movies")
    if not df_watched.empty:
        editor_key_watched = "watched_movies_editor"
        # User's desired display order
        cols_display_watched = ["User Rating", "Poster URL", "Title", "Year",
                                "Genre", "Director", "Mark Unwatched", "Delete"]
        
        config_watched = {
            "DB ID": None, "IMDb ID": None, "Status": None, "Date Added": None,
            "Mark Unwatched": st.column_config.CheckboxColumn("Move to 'Want to Watch'?", default=False, width="small"), # Label added
            "Delete": st.column_config.CheckboxColumn("Delete?", default=False, width="small"), # Label added
            "Poster URL": st.column_config.ImageColumn("Poster", width="small"),
            "Title": st.column_config.TextColumn(width="medium", disabled=True),
            "Year": st.column_config.TextColumn(width="small", disabled=True),
            "User Rating": st.column_config.NumberColumn("Your Rating (1-5)", min_value=1, max_value=5, step=1, format="%d ⭐"),
            "Genre": st.column_config.TextColumn(disabled=True),
            "Director": st.column_config.TextColumn(disabled=True),
        }
        
        st.caption("Select actions or edit ratings, then click 'Confirm Selections'.")
        # Pass a DataFrame that includes "DB ID" for processing.
        df_for_editor_watched = df_watched[cols_display_watched + ["DB ID"]].copy()
        
        # Note: st.data_editor returns the current state of the data in the editor.
        # However, for processing edits, st.session_state[editor_key]["edited_rows"] is often more precise.
        # The variable edited_df_watched_state isn't strictly necessary if using session_state for processing.
        st.data_editor( 
            df_for_editor_watched,
            key=editor_key_watched,
            column_config=config_watched,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )

        if st.button("Confirm Selections", key="confirm_watched"): # User's button text, added key
            actions_taken_watched = False
            if editor_key_watched in st.session_state and "edited_rows" in st.session_state[editor_key_watched]:
                edited_rows_info = st.session_state[editor_key_watched]["edited_rows"]
                # Iterate through the original df_watched indices that were edited
                for row_idx_str, changes in edited_rows_info.items():
                    row_idx = int(row_idx_str)
                    
                    # Get DB ID and original title from the DataFrame that was passed to the editor
                    # using iloc because row_idx is the positional index in that DataFrame.
                    movie_db_id = int(df_watched.iloc[row_idx]["DB ID"]) 
                    original_title = df_watched.iloc[row_idx]["Title"]

                    # Prioritize Delete
                    if changes.get("Delete"): # Check if "Delete" was changed to True
                        if db.delete_movie_by_db_id(movie_db_id):
                            st.toast(f"Deleted '{original_title}'.")
                            actions_taken_watched = True
                        continue # If deleted, skip other actions for this movie

                    if changes.get("Mark Unwatched"): # Check if "Mark Unwatched" was changed to True
                        if db.update_movie_status(movie_db_id, "Want to Watch"):
                            db.update_movie_rating(movie_db_id, None) # Clear rating
                            st.toast(f"Moved '{original_title}' to Want to Watch.")
                            actions_taken_watched = True
                        # If moved, rating change for this row (if any in `changes`) might be irrelevant or could be processed.
                        # For simplicity, if moved, we assume its rating is now None.
                        # If "User Rating" was also in `changes` for this row, it will be for the movie *before* it was moved.
                        # The current logic is: delete > move > rate. This is fine.
                        continue 

                    if "User Rating" in changes:
                        new_rating = changes["User Rating"]
                        if pd.isna(new_rating) or new_rating is None:
                            if db.update_movie_rating(movie_db_id, None):
                                st.toast(f"Rating cleared for '{original_title}'.")
                                actions_taken_watched = True
                        else:
                            try:
                                if db.update_movie_rating(movie_db_id, int(new_rating)):
                                    st.toast(f"Rating updated for '{original_title}'.")
                                    actions_taken_watched = True
                            except ValueError:
                                logging.warning(f"Invalid rating '{new_rating}' for DB ID {movie_db_id}")
            
            if actions_taken_watched:
                if editor_key_watched in st.session_state and "edited_rows" in st.session_state[editor_key_watched]:
                     del st.session_state[editor_key_watched]["edited_rows"] # Clear processed edits
                st.rerun()
            else:
                st.info("No changes made in 'Watched' list to process.")
    else:
        st.info("Your 'Watched' list is empty!")

    st.divider()
    # --- Clear ALL Movies Button ---
    # df_all is now guaranteed to be defined
    if not df_all.empty: 
        st.subheader("Danger Zone")
        if st.checkbox("Show Clear All Movies Option"):
            # Use a unique key for the button to avoid conflict if same label used elsewhere
            if st.button("⚠️ Clear My Entire Movie List", type="secondary", key="clear_all_movies_button"):
                # Extra confirmation for safety
                if st.checkbox("Are you absolutely sure? This cannot be undone.", key="confirm_clear_all_checkbox"): 
                    deleted_count = db.delete_all_movies_for_user(st.session_state.user_id)
                    st.success(f"Successfully cleared {deleted_count} movies.")
                    logging.info(f"EVENT: UIClearList - UserID: {st.session_state.user_id}, DeletedCount: {deleted_count}")
                    st.rerun()
                else:
                    st.warning("Clear all operation cancelled (final confirmation not given).")
            elif st.session_state.get("clear_all_movies_button"): # If button was pressed but checkbox not
                 st.warning("Clear all operation cancelled (final confirmation not given).")


    st.sidebar.header("About")
    st.sidebar.info("Movie Tracker: Track, rate, and manage your movie experiences!")
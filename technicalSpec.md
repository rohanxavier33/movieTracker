build out a technical spec for this

Show thinking

Okay, here is a technical specification for the Simple Movie Tracker with API Integration, built with Streamlit, keeping it as basic as possible while covering all your requirements.

**Technical Specification: Simple Movie Tracker**

**1\. Introduction**

This document outlines the technical design for a basic web application allowing users to track movies they have watched or wish to watch. The application will be built using Streamlit, store data persistently, and integrate with a free external API to fetch movie details. It will include core software engineering practices such as testing, continuous integration, continuous delivery, basic monitoring, and simplified event logging.

**2\. Architecture**

The application will follow a simple, mostly monolithic architecture centered around the Streamlit application.

-   **Streamlit Frontend/Backend:** Streamlit handles both the user interface (forms, display) and the core application logic in Python.
-   **Data Access Layer:** A module/set of functions to interact with the data persistence layer (SQLite).
-   **Data Store:** An SQLite database file to store movie data.
-   **API Client:** A module/set of functions to interact with the external Movie API (OMDb).
-   **External Movie API:** OMDb API (or similar free alternative) for fetching movie details.
-   **Cross-cutting Concerns:** Testing, CI/CD, Monitoring, and Event Messaging will be integrated across the codebase using appropriate tools and patterns.

<!-- end list -->

```
+-----------------+     +-------------------+     +---------------+
|                 |     | Data Access Layer |     |   Data Store  |
| Streamlit App   | <-> | (Read/Write Logic)| <-> |   (SQLite)    |
| (UI & Logic)    |     +-------------------+     +---------------+
|                 |
|                 |     +---------------+     +-------------------+
|                 | <-> |  API Client   | <-> | External Movie API|
|                 |     | (OMDb Calls)  |     |      (OMDb)       |
+-----------------+     +---------------+     +-------------------+

+-------------------------------------------------------------------+
| Testing (Unit, Integration, Mocks) | CI/CD | Monitoring | Events |
+-------------------------------------------------------------------+

```

**3\. Components**

-   **Web Application (Streamlit UI):**
    -   A main page displaying the tracked movies.
    -   A section or separate page for adding new movies.
    -   Utilize Streamlit widgets (`st.form`, `st.text_input`, `st.selectbox`, `st.button`, `st.dataframe`, etc.).
-   **Basic Form (Add Movie):**
    -   Input fields for:
        -   Movie Title (required)
        -   Status (Dropdown: "Watched", "Want to Watch")
        -   An optional input field (e.g., text input) to trigger API lookup by Title or IMDb ID.
    -   A "Add Movie" button within a `st.form`.
-   **Data Collection:**
    -   Capture user input directly from the `st.form`.
    -   If the API lookup field is used, call the API and integrate fetched data (like director, genre, IMDb ID, poster URL) into the data before saving.
-   **Data Persistence Layer:**
    -   Python functions/classes responsible for connecting to the SQLite database.
    -   Functions for: `add_movie(movie_data)`, `get_all_movies()`, `update_movie_status(movie_id, new_status)`, `delete_movie(movie_id)` (optional for basic scope), `get_movies_by_status(status)`.
-   **Data Store:**
    -   An SQLite database file (e.g., `movies.db`).
    -   A simple table schema, e.g., `movies` with columns: `id` (INTEGER PRIMARY KEY AUTOINCREMENT), `title` (TEXT), `director` (TEXT), `genre` (TEXT), `status` (TEXT), `imdb_id` (TEXT, optional), `poster_url` (TEXT, optional), `date_added` (TEXT/DATETIME).
-   **REST Collaboration (API Client):**
    -   A Python module (e.g., `api_client.py`) using the `requests` library.
    -   A function like `search_and_get_movie_details(query)` that takes a title or ID, calls the OMDb API, and returns relevant movie data in a structured format (e.g., a dictionary).
    -   Requires an OMDb API key (needs to be handled securely, e.g., via environment variables).
-   **Data Analyzer/Reporting:**
    -   Functions to query the Data Persistence Layer (`get_all_movies`, `get_movies_by_status`).
    -   Basic aggregation (e.g., counting movies per status).
    -   Displaying the data using `st.dataframe` or iterating through results and displaying using `st.write` or `st.info`. Filtering/sorting can be handled using pandas if `st.dataframe` is used or simple Python list comprehensions.
-   **Unit Tests:**
    -   Using the `pytest` framework.
    -   Tests for isolated functions: data validation (e.g., checking required fields), data access layer functions (testing SQL queries or file operations), API client function (testing response parsing, error handling).
-   **Integration Tests:**
    -   Using `pytest`.
    -   Tests covering the interaction between components: Form submission logic calls Data Persistence Layer correctly. API Client successfully fetches data and the Data Persistence Layer saves it. Data Persistence Layer correctly provides data to the Data Analyzer for display.
-   **Mock Objects or any Test Doubles:**
    -   Using `unittest.mock` (built-in) or `pytest-mock`.
    -   Mock the `requests` library calls in the API Client tests to avoid making actual HTTP requests.
    -   Mock the Data Persistence Layer functions in tests for the Streamlit logic or Data Analyzer to isolate their testing from the database.
-   **Continuous Integration:**
    -   Tool: GitHub Actions.
    -   A `.github/workflows/ci.yml` file.
    -   Triggered on `push` to `main` branch and `pull_request` events.
    -   Steps: Checkout code, Set up Python, Install dependencies (`pip install -r requirements.txt`), Run `pytest`.
-   **Production Monitoring (Instrumenting):**
    -   Use Python's built-in `logging` module.
    -   Configure logging to output to standard output (which hosting platforms capture).
    -   Log key events: application start, movie added (log title), movie status updated (log title and new status), API call initiated (log query), API call successful (log title returned), API call failed (log error), database operation (add, get, update, error).
-   **Event Collaboration Messaging:**
    -   For this *basic* project, this will be implemented by leveraging the logging mechanism. Key application state changes or actions (e.g., movie added, status updated) will be logged with specific log levels or markers, effectively acting as a stream of application "events" that can be reviewed in the monitoring logs. No separate messaging queue system will be used to keep it simple.
-   **Continuous Delivery:**
    -   Platform: Streamlit Cloud (recommended for simplicity and free tier).
    -   Link the GitHub repository to Streamlit Cloud.
    -   Configure Streamlit Cloud to deploy automatically from the `main` branch upon successful pushes. This makes the latest successful build immediately available.
    -   Alternatively, use a deployment script in the GitHub Actions CI workflow to deploy to a free hosting platform like Render or Heroku (check free tier availability and suitability for Streamlit).

**4\. API Integration Details (OMDb)**

-   **API Endpoint:** `http://www.omdbapi.com/`
-   **Authentication:** Requires an API Key (obtainable from the OMDb website for free for non-commercial use).
-   **Key Queries:**
    -   Search by Title: `?s={title}&apikey={your_key}` (returns a list of potential matches)
    -   Get by ID: `?i={imdb_id}&apikey={your_key}` (returns detailed information for a specific movie)
-   **Data Mapping:** Map relevant fields from the OMDb JSON response (e.g., `Title`, `Year`, `Director`, `Genre`, `imdbID`, `Poster`) to the application's movie data model. Handle potential missing fields gracefully.

**5\. Technology Stack**

-   **Language:** Python 3.8+
-   **Web Framework:** Streamlit
-   **Data Persistence:** SQLite3 (Python's built-in `sqlite3` module)
-   **API Calls:** `requests` library
-   **Testing:** `pytest`, `unittest.mock` (or `pytest-mock`)
-   **Dependency Management:** `pip` and `requirements.txt`
-   **CI:** GitHub Actions
-   **CD:** Streamlit Cloud
-   **Monitoring/Events:** Python `logging` module
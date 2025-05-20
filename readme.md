##Movie Tracker

1\. Introduction

1.1. Purpose of the Application: This application - Movie Tracker - is a web based tool that's meant for users to create, manage, and track lists of movies they want to watch as well as movies that they have already watched. For movies that users have already watched, they have the option to rate it between 1 and 5 stars.

 It has a simple and intuitive interface for people to track movies as well as rate movies that they've watched. It serves as a very lightweight method to track movies digitally.

1.2. Key Features: 

-   User account creation and secure login (with password hashing)

-   Uses OMDb API to fetch movie details, like title, year, genre, poster, director

-   Want to Watch and Watched lists for each user

-   Functionality to move movies between lists as well as delete from list

-   Option to clear all movies from lists for the user

2\. Justification for Design Decisions 

2.1. Technology Stack Rationale: 

-   Python: I chose it for its ease of use and suitability for web development

-   Streamlit: I selected streamlit because of its ability to create interactive web UIs purely in Python and its free community cloud hosting.

-   SQLite: Used for data persistence due to its simplicity, serverless nature (file-based), and ease of setup for the kind of data that the application fetches.

-   OMDb API: Chosen as a free and comprehensive source for external movie metadata.

2.2. Architectural & Core Design Choices: 

-   Modular Structure: Code separated into app.py (UI and main logic), db.py (database interactions), and api_client.py (external API communication).

-   User-Specific Data: Designed as a multi-user application where each user has their own user_id and private movie lists and ratings.

-   Per-User Movie Uniqueness: Movies are unique per user's list (via UNIQUE(user_id, imdb_id) constraint). This means that multiple users can select the same movies to their lists.

-   Environment Variables for API Key: API keys are managed via .env files (for local development, excluded from Git) and environment variables (secrets.toml) on the deployment platform.

3\. System Requirements

3.1. For End Users (Accessing the Deployed Application):

-   A modern web browser (e.g., Chrome, Firefox, Safari, Edge) to access URL: https://movietracker.streamlit.app/.

-   An active internet connection 

3.2. For Development Environment / Self-Hosting: 

-   Software: 

-   Python. 

-   pip for package installation.

-   All Python packages listed in requirements.txt (Streamlit, Pandas, Requests, Passlib, python-dotenv, etc.).

-   API Access: 

-   A OMDb API Key (you can get one for free from[  http://www.omdbapi.com/apikey.aspx](http://www.omdbapi.com/apikey.aspx)). 

-   Operating System: 

-   Compatible with common OS like Windows, macOS, or Linux.

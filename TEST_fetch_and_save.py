import db
import api_client
import logging

if __name__ == "__main__":
    logging.info("Starting movie data fetching and saving process.")

    # Set up the database (creates file and table if needed)
    db.create_database()

    # List of movies to fetch and save
    movie_titles_to_fetch = [
        "Inception",
        "The Matrix",
        "Interstellar",
        "Pulp Fiction",
        "The Dark Knight",
        "Movie That Does Not Exist 12345" # Example of a movie that won't be found
    ]

    # Fetch data from API and save to database
    logging.info(f"Attempting to fetch and save {len(movie_titles_to_fetch)} movies...")
    for title in movie_titles_to_fetch:
        movie_data = api_client.get_movie_details(title) # Fetch data from API

        if movie_data:
            # Data was fetched successfully, now add it to the database
            # The add_movie function handles potential duplicates
            db.add_movie(movie_data)
        else:
            logging.warning(f"Skipping saving for '{title}' as details could not be fetched.")

    logging.info("Finished attempting to fetch and save movies.")

    # Verify data by fetching all records and printing (optional)
    logging.info("\nFetching all movies from the database to verify:")
    all_movies = db.get_all_movies()
    if all_movies:
        # Print header
        print("-" * 80)
        print(f"{'IMDb ID':<10} | {'Title':<30} | {'Year':<6} | {'Director':<20}")
        print("-" * 80)
        for movie in all_movies:
             # movie is a tuple: (imdb_id, title, year, director, genre, poster_url, date_added)
             print(f"{movie[0]:<10} | {movie[1]:<30} | {movie[2]:<6} | {movie[3]:<20}")
        print("-" * 80)
        logging.info(f"Displayed {len(all_movies)} records.")
    else:
        logging.info("No movies found in the database.")

    logging.info("Process completed.")
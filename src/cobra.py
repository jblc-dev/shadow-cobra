from utils import DbHelper
from utils import FilterController
from utils import GraphController


def main():
    gc = GraphController()
    db = DbHelper()
    genres = gc.get_genres()
    print(genres)
    filters = FilterController(genre=genres)
    db.filter_tracks(filters)

    track = db.get_track_random()
    if track is None:
        print(f"No tracks found for genres {genres}.")
        return

    print(
        f"{track['artist_name']} - {track['track_name']} "
        f"({track['year']}) [{track['genre']}]"
    )


if __name__ == "__main__":
    main()

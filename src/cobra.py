from utils import DbHelper
from utils import FilterController
from utils import GraphController


def main():
    gc = GraphController()
    db = DbHelper()
    filters = FilterController(genre=gc.get_genre())
    db.filter_tracks(filters)

    track = db.get_track_random()
    if track is None:
        print(f"No tracks found for genre '{gc.get_genre()}'.")
        return

    print(
        f"{track['artist_name']} - {track['track_name']} "
        f"({track['year']}) [{track['genre']}]"
    )


if __name__ == "__main__":
    main()

from utils import DbHelper, FilterController, GraphController, StreamController


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

    query = f"{track['artist_name']} {track['track_name']} ({track['year']}) [{track['genre']}]"
    print(f"Searching for ... {query}")
    sc = StreamController
    sc.stream_audio(query)


if __name__ == "__main__":
    main()

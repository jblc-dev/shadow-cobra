class FilterController:
    def __init__(
        self,
        popularity: list = None,
        danceability: list = None,
        energy: list = None,
        tempo: list = None,
        year: list = None,
        genre="acoustic",
        bpm: list = None,
    ):
        self.popularity = popularity if popularity else [0, 100]
        self.danceability = danceability if danceability else [0.0, 1.0]
        self.energy = energy if energy else [0.0, 1.0]
        self.tempo = tempo if tempo else [0.0, 100.0]
        self.year = year if year else [1999, 2020]
        self.genre = genre
        self.bpm = bpm if bpm else [0, 100]

    def set_property(self, property_name: str, min: float = -1, max: float = -1):
        if not hasattr(self, property_name):
            return
        if property_name == "genre":
            if isinstance(min, (str, list, tuple, set)):
                self.genre = min
            return

        current_range = getattr(self, property_name)

        if min >= 0 and max >= 0:
            if min > max:
                min, max = max, min
            setattr(self, property_name, [min, max])
            return

        low, high = current_range[0], current_range[1]

        if min >= 0:
            low = min
            if low > high:
                high = low

        if max >= 0:
            high = max
            if high < low:
                low = high
        setattr(self, property_name, [low, high])

    def matches(self, track: dict) -> bool:
        for key, value in track.items():
            if not hasattr(self, key):
                continue
            filter_val = getattr(self, key)
            if key == "genre":
                track_genres = (
                    value if isinstance(value, (list, tuple, set)) else [value]
                )
                if not any(genre in filter_val for genre in track_genres):
                    return False
            else:
                min_val, max_val = filter_val
                if not (min_val <= value <= max_val):
                    return False
        return True

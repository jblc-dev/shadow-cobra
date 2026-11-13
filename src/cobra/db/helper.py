import csv
import random
import os

from cobra.filters.controller import FilterController
from cobra.paths import DATA_DIR

DEFAULT_DB = DATA_DIR / "spotify_data.csv"

class DbHelper:

    def __init__(self, filename=None):
        self.filename = filename or DEFAULT_DB
        self.tracks = {}
        self.filtered_tracks = {}
        self._load_from_csv()

    def _load_from_csv(self):
        if not os.path.exists(self.filename):
            print(f"File '{self.filename}' not found. Starting with an empty database.")
            return

        with open(self.filename, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            for row in reader:
            
                track_id = row.get("track_id")
                if not track_id:
                    continue  
                self.tracks[track_id] = {
                    "artist_name": row.get("artist_name"),
                    "track_name": row.get("track_name"),
                    "track_id": track_id,
                    "popularity": int(row.get("popularity") or 0),
                    "year": int(row.get("year") or 0),
                    "genre": row.get("genre"),
                    "danceability": float(row.get("danceability") or 0.0),
                    "energy": float(row.get("energy") or 0.0),
                    "tempo": float(row.get("tempo") or 0.0),
                    "duration_ms": int(row.get("duration_ms") or 0)
                }
        print("Data loaded...")
    def filter_tracks(self, filter_: FilterController):
        self.filtered_tracks = {}
        
        for track_id, track_data in self.tracks.items():
            if filter_.matches(track_data):
                self.filtered_tracks[track_id] = track_data

    def get_track_random(self):
        matching_tracks = list(self.filtered_tracks.values())
        if not matching_tracks:
            return None
        return random.choice(matching_tracks)
             

  
   




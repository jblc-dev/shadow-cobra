"""Simple local web GUI for testing the music utilities.

Run with:
    .venv/bin/python src/gui.py

The frontend lives in src/web/ (index.html, style.css, app.js).
Existing utility code is not modified.
"""

import argparse
import json
import shutil
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from utils import DbHelper, FilterController, GraphController, StreamController


WEB_DIR = Path(__file__).resolve().parent / "web"

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class MusicApp:
    def __init__(self):
        print("Loading graph...")
        self.graph = GraphController()
        print("Loading track database...")
        self.db = DbHelper()
        self.stream = StreamController()
        self.lock = threading.Lock()
        self.genres = []
        self.count = 0
        self.default_genre = self.graph.get_genre() or "CHICAGO HOUSE & GARAGE HOUSE"

    def all_genre_labels(self):
        labels = {
            str(data.get("genre", "")).strip()
            for _, data in self.graph.G.nodes(data=True)
            if str(data.get("genre", "")).strip()
        }
        return sorted(labels, key=str.lower)

    def apply_filters(self, payload):
        genre_name = str(payload.get("genre", "")).strip()
        if not genre_name:
            return {"ok": False, "error": "Choose a Musicmap genre first."}

        with self.lock:
            previous = self.graph.genre
            self.graph.set_genre(genre_name)
            genres = self.graph.get_genres()
            if not genres:
                self.graph.genre = previous
                return {"ok": False, "error": f"Unknown genre: {genre_name!r}"}

            filters = FilterController(
                genre=genres,
                popularity=self._range(payload.get("popularity"), 0, 100),
                danceability=self._range(payload.get("danceability"), 0.0, 1.0),
                energy=self._range(payload.get("energy"), 0.0, 1.0),
                tempo=self._range(payload.get("tempo"), 0.0, 300.0),
                year=self._range(payload.get("year"), 1900, 2100),
            )
            self.db.filter_tracks(filters)
            self.genres = genres
            self.count = len(self.db.filtered_tracks)

        return {"ok": True, "count": self.count, "genres": genres}

    def random_track(self):
        with self.lock:
            track = self.db.get_track_random()
            count = len(self.db.filtered_tracks)
        if track is None:
            return {"ok": False, "error": "No tracks match the current filters."}

        result = dict(track)
        result["stream_url"] = f"/api/stream/{track['track_id']}"
        return {"ok": True, "track": result, "count": count}

    def stream_url(self, track_id):
        track = self.db.tracks.get(track_id)
        if track is None:
            return None
        return self._resolve_stream_url(track)

    def _resolve_stream_url(self, track):
        # Use the project's StreamController when it exposes a resolver.
        resolver = getattr(self.stream, "get_stream_url", None)
        if callable(resolver):
            try:
                return resolver(track)
            except Exception:
                pass

        # Fallback: resolve a direct audio URL with yt-dlp ourselves.
        yt_dlp = Path(sys.executable).parent / "yt-dlp"
        if not yt_dlp.exists():
            yt_dlp = shutil.which("yt-dlp") or "yt-dlp"

        query = " ".join(
            part for part in (track.get("artist_name"), track.get("track_name")) if part
        )
        result = subprocess.run(
            [
                str(yt_dlp),
                "--no-playlist",
                "--quiet",
                "--no-warnings",
                "-f",
                "bestaudio/best",
                "-g",
                f"ytsearch1:{query}",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "yt-dlp failed")
        urls = [line for line in result.stdout.splitlines() if line.strip()]
        if not urls:
            raise RuntimeError("yt-dlp did not return an audio URL")
        return urls[0]

    @staticmethod
    def _range(value, low, high):
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return [low, high]
        start = max(low, min(high, float(value[0])))
        end = max(low, min(high, float(value[1])))
        return [min(start, end), max(start, end)]


class Handler(BaseHTTPRequestHandler):
    server_version = "CobraGui/0.2"

    @property
    def app(self):
        return self.server.app

    def log_message(self, format, *args):
        return

    def _send_bytes(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status=status)

    def do_GET(self):
        path = urlparse(self.path).path

        if path in STATIC_FILES:
            filename, content_type = STATIC_FILES[path]
            body = (WEB_DIR / filename).read_bytes()
            if filename == "index.html":
                body = body.replace(
                    b"__DEFAULT_GENRE__", self.app.default_genre.encode("utf-8")
                )
            self._send_bytes(body, content_type)
            return

        if path == "/api/genres":
            self._send_json({"genres": self.app.all_genre_labels()})
            return

        if path.startswith("/api/stream/"):
            track_id = unquote(path[len("/api/stream/"):])
            try:
                url = self.app.stream_url(track_id)
            except Exception as error:
                self._send_json({"ok": False, "error": str(error)}, status=502)
                return
            if not url:
                self._send_json(
                    {"ok": False, "error": "Unknown track."}, status=404
                )
                return
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path == "/favicon.ico":
            self._send_bytes(b"", "image/x-icon", status=204)
            return

        self._send_json({"ok": False, "error": "Not found."}, status=404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "Invalid JSON."}, status=400)
            return

        try:
            if path == "/api/filter":
                result = self.app.apply_filters(payload)
            elif path == "/api/random":
                result = self.app.random_track()
            else:
                self._send_json({"ok": False, "error": "Not found."}, status=404)
                return
        except Exception as error:
            self._send_json({"ok": False, "error": str(error)}, status=500)
            return

        self._send_json(result, status=200 if result.get("ok") else 400)


def main():
    parser = argparse.ArgumentParser(description="Cobra music explorer GUI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8777)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    app = MusicApp()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.app = app
    url = f"http://{args.host}:{args.port}/"

    print(f"GUI running at {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

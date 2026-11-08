"""Simple local web GUI for testing the music utilities.

Run with:
    .venv/bin/python src/gui.py

It only adds a new entry point. Existing utility code is not modified.
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


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cobra music explorer</title>
<style>
  :root {
    color-scheme: dark;
    --bg: #12141a;
    --panel: #1b1f28;
    --panel-2: #232835;
    --text: #e8eaf0;
    --muted: #9aa3b5;
    --accent: #7c9cff;
    --accent-2: #4ade80;
    --border: #303747;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    background: radial-gradient(circle at top left, #1d2435, var(--bg) 55%);
    color: var(--text);
    font: 15px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  header {
    padding: 24px 28px 8px;
  }
  h1 { margin: 0; font-size: 24px; letter-spacing: .3px; }
  header p { margin: 4px 0 0; color: var(--muted); }
  main {
    display: grid;
    grid-template-columns: minmax(320px, 420px) 1fr;
    gap: 20px;
    padding: 20px 28px 40px;
    max-width: 1180px;
  }
  @media (max-width: 860px) { main { grid-template-columns: 1fr; } }
  section {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 16px 40px rgba(0,0,0,.22);
  }
  h2 { margin: 0 0 14px; font-size: 16px; }
  label { display: block; margin: 14px 0 6px; color: var(--muted); font-size: 13px; }
  input[type="text"], input[type="search"] {
    width: 100%;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--panel-2);
    color: var(--text);
    font: inherit;
  }
  input[type="range"] { width: 100%; accent-color: var(--accent); }
  .range-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .range-row output { min-width: 66px; text-align: right; color: var(--accent); font-variant-numeric: tabular-nums; }
  .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
  button {
    border: 0;
    border-radius: 10px;
    padding: 10px 14px;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    background: var(--panel-2);
    color: var(--text);
    border: 1px solid var(--border);
  }
  button.primary { background: var(--accent); color: #0b1020; border-color: transparent; }
  button.good { background: var(--accent-2); color: #052e16; border-color: transparent; }
  button:hover { filter: brightness(1.08); }
  #status { min-height: 20px; margin-top: 14px; color: var(--muted); font-size: 13px; white-space: pre-wrap; }
  .track { margin-top: 6px; }
  .track-artist { color: var(--muted); font-size: 14px; }
  .track-title { font-size: 27px; line-height: 1.2; margin: 2px 0 8px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 18px; }
  .chip {
    padding: 5px 10px;
    border-radius: 999px;
    background: var(--panel-2);
    border: 1px solid var(--border);
    color: var(--muted);
    font-size: 12px;
  }
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
  .metric { background: var(--panel-2); border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; }
  .metric span { display: block; color: var(--muted); font-size: 12px; }
  .metric strong { font-size: 18px; font-variant-numeric: tabular-nums; }
  audio { width: 100%; margin-top: 18px; }
  .empty { color: var(--muted); padding: 30px 0; text-align: center; }
  .genre-list { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 7px; }
  .genre-pill {
    font-size: 11px;
    color: var(--muted);
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 3px 8px;
  }
</style>
</head>
<body>
<header>
  <h1>Cobra music explorer</h1>
  <p>Musicmap graph &rarr; genre filter &rarr; random track &rarr; full stream</p>
</header>
<main>
  <section>
    <h2>Filter settings</h2>
    <label for="genre">Musicmap genre</label>
    <input id="genre" type="search" list="genreList" value="__DEFAULT_GENRE__" autocomplete="off">
    <datalist id="genreList"></datalist>

    <label>Popularity <span class="range-row"><input id="popularity" type="range" min="0" max="100" value="100"><output></output></span></label>
    <label>Danceability <span class="range-row"><input id="danceability" type="range" min="0" max="100" value="100"><output></output></span></label>
    <label>Energy <span class="range-row"><input id="energy" type="range" min="0" max="100" value="100"><output></output></span></label>
    <label>Tempo (BPM) <span class="range-row"><input id="tempo" type="range" min="0" max="250" value="250"><output></output></span></label>
    <label>Year <span class="range-row"><input id="year" type="range" min="1900" max="2026" value="2026"><output></output></span></label>

    <div class="actions">
      <button class="primary" id="apply">Apply filters</button>
      <button class="good" id="random">Random song</button>
    </div>
    <div id="status"></div>
    <div class="genre-list" id="genreChips"></div>
  </section>

  <section>
    <h2>Now playing</h2>
    <div id="trackBox" class="empty">No song selected yet.</div>
    <div id="trackTemplate" class="track" hidden>
      <div class="track-artist" id="artist"></div>
      <div class="track-title" id="title"></div>
      <div class="chips" id="chips"></div>
      <div class="metrics">
        <div class="metric"><span>Popularity</span><strong id="mPopularity"></strong></div>
        <div class="metric"><span>Danceability</span><strong id="mDanceability"></strong></div>
        <div class="metric"><span>Energy</span><strong id="mEnergy"></strong></div>
        <div class="metric"><span>Tempo</span><strong id="mTempo"></strong></div>
        <div class="metric"><span>Year</span><strong id="mYear"></strong></div>
        <div class="metric"><span>Duration</span><strong id="mDuration"></strong></div>
      </div>
      <audio id="player" controls preload="none"></audio>
      <div class="actions">
        <button id="play">Play</button>
        <button id="stop">Stop</button>
      </div>
      <div id="streamStatus" class="genre-list"></div>
    </div>
  </section>
</main>
<script>
const $ = (id) => document.getElementById(id);
const rangeIds = ["popularity", "danceability", "energy", "tempo", "year"];

function rangeLabel(id, value) {
  if (id === "danceability" || id === "energy") return (Number(value) / 100).toFixed(2);
  if (id === "tempo") return value + " BPM";
  return value;
}

function refreshRange(id) {
  const input = $(id);
  input.parentElement.querySelector("output").textContent = rangeLabel(id, input.value);
}

for (const id of rangeIds) {
  $(id).addEventListener("input", () => refreshRange(id));
  refreshRange(id);
}

function setStatus(text) { $("status").textContent = text; }

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body || {}),
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || response.statusText);
  return data;
}

async function loadGenres() {
  try {
    const response = await fetch("/api/genres");
    const data = await response.json();
    const list = $("genreList");
    for (const name of data.genres) {
      const option = document.createElement("option");
      option.value = name;
      list.appendChild(option);
    }
  } catch (error) {
    setStatus("Could not load genres: " + error.message);
  }
}

function currentFilters() {
  return {
    genre: $("genre").value.trim(),
    popularity: [0, Number($("popularity").value)],
    danceability: [0, Number($("danceability").value) / 100],
    energy: [0, Number($("energy").value) / 100],
    tempo: [0, Number($("tempo").value)],
    year: [1900, Number($("year").value)],
  };
}

async function applyFilters() {
  setStatus("Filtering...");
  try {
    const data = await post("/api/filter", currentFilters());
    setStatus("Matched " + data.count + " track(s).");
    $("genreChips").innerHTML = "";
    for (const name of data.genres) {
      const pill = document.createElement("span");
      pill.className = "genre-pill";
      pill.textContent = name;
      $("genreChips").appendChild(pill);
    }
  } catch (error) {
    setStatus("Filter error: " + error.message);
  }
}

function showTrack(track) {
  $("trackBox").hidden = true;
  $("trackTemplate").hidden = false;
  $("artist").textContent = track.artist_name || "Unknown artist";
  $("title").textContent = track.track_name || "Unknown track";
  $("chips").innerHTML = "";
  for (const value of [track.genre, track.year]) {
    if (!value) continue;
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = value;
    $("chips").appendChild(chip);
  }
  $("mPopularity").textContent = track.popularity;
  $("mDanceability").textContent = Number(track.danceability).toFixed(2);
  $("mEnergy").textContent = Number(track.energy).toFixed(2);
  $("mTempo").textContent = Math.round(track.tempo) + " BPM";
  $("mYear").textContent = track.year || "-";
  $("mDuration").textContent = track.duration_ms
    ? Math.floor(track.duration_ms / 60000) + ":" + String(Math.floor((track.duration_ms % 60000) / 1000)).padStart(2, "0")
    : "-";

  const player = $("player");
  player.pause();
  player.removeAttribute("src");
  player.load();
  $("streamStatus").textContent = "";
  player.dataset.stream = track.stream_url;
}

async function randomTrack() {
  setStatus("Picking a random song...");
  try {
    const data = await post("/api/random");
    showTrack(data.track);
    setStatus("Random pick from " + data.count + " matching track(s).");
  } catch (error) {
    setStatus("Random error: " + error.message);
  }
}

$("apply").addEventListener("click", applyFilters);
$("random").addEventListener("click", randomTrack);

$("play").addEventListener("click", () => {
  const player = $("player");
  if (!player.dataset.stream) return;
  $("streamStatus").textContent = "Resolving stream with yt-dlp...";
  player.src = player.dataset.stream;
  player.play().catch((error) => {
    $("streamStatus").textContent = "Playback error: " + error.message;
  });
});

$("player").addEventListener("playing", () => {
  $("streamStatus").textContent = "Streaming full track.";
});
$("player").addEventListener("error", () => {
  $("streamStatus").textContent = "Could not load the stream. Check the server console.";
});

$("stop").addEventListener("click", () => {
  const player = $("player");
  player.pause();
  player.removeAttribute("src");
  player.load();
  $("streamStatus").textContent = "Stopped.";
});

loadGenres().then(applyFilters);
</script>
</body>
</html>
"""


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
    server_version = "CobraGui/0.1"

    @property
    def app(self):
        return self.server.app

    def log_message(self, format, *args):
        return

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self._send_html(PAGE.replace("__DEFAULT_GENRE__", self.app.default_genre))
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

# shadow-cobra
Music app for actually discovering new music - not an ehco chamber

## Layout

```
src/cobra/          application package (importable)
  cli.py            command-line entry point
  db/               spotify CSV loading + filtering state
  filters/          track filtering rules
  graph/            Musicmap genre graph
  playback/         yt-dlp / mpv streaming
  web/              local web GUI (server.py + static/)
tools/              offline scripts that generate data/ (not importable by the app)
data/               graph JSON + spotify_data.csv (gitignored)
```

## Running

```sh
pip install -e .
cobra            # CLI
cobra-gui        # local web GUI
```

Without installing:

```sh
PYTHONPATH=src .venv/bin/python -m cobra.cli
PYTHONPATH=src .venv/bin/python -m cobra.web.server
```

## Data

`data/musicmap-graph.json` and `data/musicmap-graph-cleaned.json` are tracked.
`data/spotify_data.csv` is not, and must be supplied locally.

Regenerate the graph artifacts with:

```sh
python3 tools/fetch_musicmap_graph.py --out-dir data
python3 tools/build_cleaned_graph.py
```

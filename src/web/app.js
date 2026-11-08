const $ = (id) => document.getElementById(id);

const METRICS = {
  popularity: { scale: 1, decimals: 0, suffix: "" },
  danceability: { scale: 100, decimals: 2, suffix: "" },
  energy: { scale: 100, decimals: 2, suffix: "" },
  tempo: { scale: 1, decimals: 0, suffix: " BPM" },
  year: { scale: 1, decimals: 0, suffix: "" },
};

const ranges = new Map();

function formatValue(metric, raw) {
  const config = METRICS[metric];
  return (raw / config.scale).toFixed(config.decimals) + config.suffix;
}

function setupRange(filter) {
  const metric = filter.dataset.metric;
  const minInput = filter.querySelector(".range-min");
  const maxInput = filter.querySelector(".range-max");
  const fill = filter.querySelector(".range-fill");
  const output = filter.querySelector(".filter-value");

  function sync() {
    const low = Number(minInput.value);
    const high = Number(maxInput.value);
    const floor = Number(minInput.min);
    const ceiling = Number(minInput.max);
    const span = ceiling - floor;

    const left = ((low - floor) / span) * 100;
    const right = ((high - floor) / span) * 100;

    fill.style.left = `${left}%`;
    fill.style.width = `${right - left}%`;

    // Keep the thumb nearest the right edge clickable when both overlap.
    const midpoint = (floor + ceiling) / 2;
    minInput.style.zIndex = low > midpoint ? "5" : "3";
    maxInput.style.zIndex = low > midpoint ? "3" : "5";

    output.textContent = `${formatValue(metric, low)} \u2013 ${formatValue(metric, high)}`;
  }

  minInput.addEventListener("input", () => {
    if (Number(minInput.value) > Number(maxInput.value)) {
      minInput.value = maxInput.value;
    }
    sync();
  });

  maxInput.addEventListener("input", () => {
    if (Number(maxInput.value) < Number(minInput.value)) {
      maxInput.value = minInput.value;
    }
    sync();
  });

  sync();
  ranges.set(metric, { minInput, maxInput });
}

for (const filter of document.querySelectorAll(".filter")) {
  setupRange(filter);
}

function rawRange(metric) {
  const range = ranges.get(metric);
  return [Number(range.minInput.value), Number(range.maxInput.value)];
}

function scaledRange(metric) {
  const config = METRICS[metric];
  return rawRange(metric).map((value) => value / config.scale);
}

function setStatus(text) {
  $("status").textContent = text;
}

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || response.statusText);
  }
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
    popularity: scaledRange("popularity"),
    danceability: scaledRange("danceability"),
    energy: scaledRange("energy"),
    tempo: scaledRange("tempo"),
    year: scaledRange("year"),
  };
}

async function applyFilters() {
  setStatus("Filtering...");
  try {
    const data = await post("/api/filter", currentFilters());
    setStatus("Matched " + data.count + " track(s).");
    const chips = $("genreChips");
    chips.innerHTML = "";
    for (const name of data.genres) {
      const pill = document.createElement("span");
      pill.className = "genre-pill";
      pill.textContent = name;
      chips.appendChild(pill);
    }
  } catch (error) {
    setStatus("Filter error: " + error.message);
  }
}

function formatDuration(durationMs) {
  if (!durationMs) return "-";
  const minutes = Math.floor(durationMs / 60000);
  const seconds = Math.floor((durationMs % 60000) / 1000);
  return minutes + ":" + String(seconds).padStart(2, "0");
}

function showTrack(track) {
  $("trackBox").hidden = true;
  $("trackTemplate").hidden = false;
  $("artist").textContent = track.artist_name || "Unknown artist";
  $("title").textContent = track.track_name || "Unknown track";

  const chips = $("chips");
  chips.innerHTML = "";
  for (const value of [track.genre, track.year]) {
    if (!value) continue;
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = value;
    chips.appendChild(chip);
  }

  $("mPopularity").textContent = track.popularity;
  $("mDanceability").textContent = Number(track.danceability).toFixed(2);
  $("mEnergy").textContent = Number(track.energy).toFixed(2);
  $("mTempo").textContent = Math.round(track.tempo) + " BPM";
  $("mYear").textContent = track.year || "-";
  $("mDuration").textContent = formatDuration(track.duration_ms);

  const player = $("player");
  player.pause();
  player.removeAttribute("src");
  player.load();
  player.dataset.stream = track.stream_url;
  $("streamStatus").textContent = "";
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

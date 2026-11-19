import subprocess


class StreamWorker:
  
    def __init__(self):
        self.process = None
        self._owned = False

    def start(self, query):
        self._cleanup()
        self.query = query
        self.process = subprocess.Popen(
            [
                "yt-dlp",
                "--no-playlist",
                "--quiet",
                "--no-warnings",
                "-f", "bestaudio/best",
                "-o", "-",
                f"ytsearch1:{query}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._owned = True
        return self.process

    def prefetch(self, query):
        return self.start(query)

    def take_stream(self):
        if not self._owned or self.process is None:
            return None
        self._owned = False
        return self.process.stdout

    def healthcheck(self):
        if self._owned and self.process is not None and self.process.poll() is not None:
            self._cleanup()
        return self.is_running()

    def is_running(self):
        return (
            self._owned
            and self.process is not None
            and self.process.poll() is None
        )

    def _cleanup(self):
        process = self.process
        if process is not None:
            if process.stdout is not None:
                try:
                    process.stdout.close()
                except OSError:
                    pass
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    process.kill()
                    process.wait()
        self.process = None
        self._owned = False

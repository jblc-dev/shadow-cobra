import queue
import subprocess
import threading
import time

class StreamWorker:

    def __init__(self):

        self.stream = None

    def start(self):

        while True:
            try:
                
        
    def _start(self,query):

        self.stream = subprocess.Popen(
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
    
    def prefetch(self,query):
        self._cleanup()
        self.start(query)

    def healthcheck(self):
        if self.stream is not None and not self.is_running():
            self._cleanup()
    def _cleanup(self):
        self.stream = None

    def is_running(self):
        if self.stream is None:
            return False
        
        return self.stream.poll() is None
        
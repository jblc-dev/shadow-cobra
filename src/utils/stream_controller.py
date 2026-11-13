import queue
import subprocess
import threading
import time

class StreamController:

    def __init__(
        self,
        MAX_QUEUE_SIZE=10,
        MAX_WORKERS=3
    ):
        self.queryQueue = queue.Queue()
        self.MAX_QUEUE_SIZE=MAX_QUEUE_SIZE
        self.queue_capacity=MAX_QUEUE_SIZE
        self.MAX_WORKERS =MAX_WORKERS
        self._isRunning =True
        
         

        


    def addSong(self,query:str):
        if query None:
            return
        
        if self.queue_capacity >0:
            self.queryQueue.append(query)
            self.queue_capacity-=1

    def checkCapacity(self):
        return self.queue_capacity


    def _stream_audio(query: str) -> bytes:
        ytdlp = subprocess.Popen(
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

        mpv = subprocess.Popen(
        [
            "mpv",
            "--no-video",       
            "--really-quiet",      
            "-",                   
        ],
        stdin=ytdlp.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

        ytdlp.stdout.close()
        audio = mpv.stdout.read()
        ytdlp.wait()
        mpv.wait()
        return audio
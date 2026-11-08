import subprocess
class StreamController:

    def stream_audio(query: str) -> bytes:
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
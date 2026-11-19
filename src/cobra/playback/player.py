import queue

from cobra.playback.mpv import MPVPlayerController
from cobra.playback.stream_manager import StreamManager


class MusicPlayer:

    def __init__(self):
        self.queue = queue.Queue()
        self.mpv = MPVPlayerController()
        self.worker_manager = StreamManager(self.queue)
        self.worker_manager.start()

    def add_track(self, track):
        self.queue.put(track)

    def play(self):
        stream_pipe = self.worker_manager.get_active_stream()
        if stream_pipe is None:
            return False
        self.mpv.start_player(stream_pipe)
        return True

    def pause(self):
        self.mpv.pause_song()

    def resume(self):
        self.mpv.start_song()

    def set_volume(self, level):
        self.mpv.set_volume(level)

    def skip(self):
        self.mpv.clean_up()
        self.worker_manager.skip()
        stream_pipe = self.worker_manager.get_active_stream(timeout=1.0)
        if stream_pipe is not None:
            self.mpv.start_player(stream_pipe)

    def stop(self):
        self.mpv.clean_up()
        self.worker_manager.stop()

    def wait(self):
        if self.mpv.process is not None:
            self.mpv.process.wait()

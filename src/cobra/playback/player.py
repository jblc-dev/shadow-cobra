import queue
import MPVPlayerController
import StreamManager
class MusicPlayer:

    def __init__(self):
        self.queue = queue.queue()
        self.mpv = MPVPlayerController()
        self.worker_manager = StreamManager(self.queue)
        

    def add_track(self,track):
        self.queue.append(track)
    
    def pause(self):
        self.mpv.pause_song()
    def skip(self):
        self.mpv.clean_up()
        self.worker_manager.skip()
        stream_pipe = self.worker_manager.get_active_stream()
        self.mpv.start_player(stream_pipe)
    


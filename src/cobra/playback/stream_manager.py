import threading
import StreamWorker

class StreamManager:

    def __init__(
        self,
        queue
        ):
        self.worker1 = StreamWorker()
        self.worker2 = StreamWorker()
        self.queue=queue
        self.is_running = True

    def start(self):

        while self.is_running:
            try:
                next_track = self.queue.poll()






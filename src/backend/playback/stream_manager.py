import logging
import queue
import threading
import time

from cobra.playback.stream import StreamWorker


class StreamManager:

    def __init__(self, track_queue):
        self.queue = track_queue
        self.worker1 = StreamWorker()
        self.worker2 = StreamWorker()
        self.active = self.worker1
        self.standby = self.worker2
        self.is_running = False
        self._active_in_use = False
        self._cond = threading.Condition()
        self._thread = None

    def start(self):
        with self._cond:
            if self.is_running:
                return
            self.is_running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="stream-manager"
        )
        self._thread.start()

    def stop(self):
        with self._cond:
            self.is_running = False
            self._cond.notify_all()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)
            if thread.is_alive():
                logging.warning("stream-manager thread did not stop within 2s")
        with self._cond:
            self.active._cleanup()
            self.standby._cleanup()
            self._active_in_use = False
            self._thread = None

    def _run(self):
        while True:
            with self._cond:
                while self.is_running and not (
                    self._active_in_use and not self.standby.is_running()
                ):
                    self._cond.wait()
                if not self.is_running:
                    return

            try:
                track = self.queue.get(timeout=0.2)
            except queue.Empty:
                continue

            with self._cond:
                if self.standby.is_running():
                    self.queue.put(track)
                else:
                    try:
                        self.standby.prefetch(track)
                    except Exception:
                        logging.exception("Failed to prefetch track: %r", track)
                self._cond.notify_all()

    def add_track(self, track):
        
        with self._cond:
            self.queue.put(track)
            self._cond.notify_all()

    def get_active_stream(self, timeout=10.0):
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                if self.active.is_running():
                    self._active_in_use = True
                    self._cond.notify_all()
                    return self.active.take_stream()

                if self.standby.is_running():
                    self._promote_locked()
                    self._active_in_use = True
                    self._cond.notify_all()
                    return self.active.take_stream()

                track = self._next_track_locked()
                if track is not None:
                    self.active.prefetch(track)
                    self._active_in_use = True
                    self._cond.notify_all()
                    return self.active.take_stream()

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cond.wait(min(remaining, 0.1))

    def skip(self):
        with self._cond:
            self._promote_locked()
            self._active_in_use = self.active.is_running()
            self._cond.notify_all()
            return self._active_in_use

    def _promote_locked(self):
        self.active._cleanup()
        self.active, self.standby = self.standby, self.active

    def _next_track_locked(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None

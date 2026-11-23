"""One producer per backend process; slow subscribers skip obsolete frames."""
import logging
import threading


class CameraWorker:
    def __init__(self, source):
        self.source = source
        self.condition = threading.Condition()
        self.stop_event = threading.Event()
        self.thread = None
        self.frame = None
        self.sequence = 0
        self.error = None

    def start(self):
        with self.condition:
            if self.stop_event.is_set():
                return
            if self.thread is None:
                self.thread = threading.Thread(target=self._run, name="camera-inference", daemon=True)
                self.thread.start()

    def _run(self):
        while not self.stop_event.is_set():
            frames = self.source()
            try:
                for frame in frames:
                    if self.stop_event.is_set():
                        break
                    with self.condition:
                        self.frame = frame
                        self.sequence += 1
                        self.error = None
                        self.condition.notify_all()
            except Exception as error:
                logging.exception("Camera worker failed; retrying")
                with self.condition:
                    self.error = str(error)
                    self.frame = None
                    self.condition.notify_all()
            finally:
                frames.close()
            self.stop_event.wait(1)

    def subscribe(self):
        self.start()
        sequence = -1
        while not self.stop_event.is_set():
            with self.condition:
                self.condition.wait_for(lambda: self.stop_event.is_set() or
                                        (self.frame is not None and self.sequence != sequence))
                if self.stop_event.is_set():
                    return
                sequence, frame = self.sequence, self.frame
            yield frame

    def stop(self):
        self.stop_event.set()
        with self.condition:
            self.condition.notify_all()
        if self.thread is not None:
            self.thread.join(timeout=5)

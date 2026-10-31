"""Real capture CLI/session/control; synthetic sniffer instead of NIC for tests."""
import threading
import time
from stage20_test_capture_adapter import packet
import run_live_capture


class SyntheticSniffer:
    def __init__(self, **kwargs):
        self.callback = kwargs['prn']
        self.running = False
        self.event = threading.Event()
        self.stop_cb = self.event.set
        self.thread = None
        self.error = None

    def start(self):
        def work():
            self.running = True
            deadline = time.monotonic() + 8  # Never leave a fixture orphan forever.
            try:
                while not self.event.is_set() and time.monotonic() < deadline:
                    p = packet(0, payload=16)
                    p.time = time.time()
                    self.callback(p)
                    self.event.wait(.02)
            except BaseException as error:
                self.error = error
            finally:
                self.running = False
        self.thread = threading.Thread(target=work)
        self.thread.start()

    def stop(self, join=False):
        self.event.set()

    def join(self, timeout=0):
        self.thread.join(timeout)
        if self.error:
            raise self.error


if __name__ == '__main__':
    run_live_capture.AsyncSniffer = SyntheticSniffer
    run_live_capture.main()

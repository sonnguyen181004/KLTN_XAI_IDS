"""Capture failures must reach the CLI, including exceptions swallowed by Scapy."""
import threading
import time


def check_health(session):
    error = getattr(session, '_capture_error', None)
    if error is not None:
        raise RuntimeError('Capture lỗi; phiên không hoàn tất: ' + str(error)) from error


def guarded_process(session):
    def process(packet):
        check_health(session)
        try:
            return session.process(packet)
        except Exception as error:
            session._capture_error = error
            raise
    return process


def start_gc(session, interval=1.):
    session._gc_stop = threading.Event()
    def run():
        while not session._gc_stop.wait(interval):
            try:
                check_health(session)
                session.garbage_collect(time.time())
            except Exception as error:
                if getattr(session, '_capture_error', None) is None:
                    session._capture_error = error
                session._gc_stop.set()
                return
    session._gc_thread = threading.Thread(target=run, name='project-flow-gc', daemon=True)
    session._gc_thread.start()


def stop_gc(session):
    event = getattr(session, '_gc_stop', None)
    if event is not None:
        event.set()
        session._gc_thread.join(timeout=3)
        if session._gc_thread.is_alive():
            raise RuntimeError('GC chưa dừng; không flush đồng thời hoặc báo dừng an toàn.')

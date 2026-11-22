# -*- coding: utf-8 -*-
"""Scope background results to one operation and one live Enigma2 screen."""
import threading


class TaskCancelled(Exception):
    pass


class TaskScope:
    def __init__(self, dispatch):
        self.dispatch = dispatch
        self.current = None
        self.closed = False

    def begin(self):
        self.cancel()
        if self.closed:
            raise TaskCancelled()
        self.current = threading.Event()
        return self.current

    def cancel(self):
        if self.current is not None:
            self.current.set()
        self.current = None

    def close(self):
        self.closed = True
        self.cancel()

    def valid(self, token):
        return token is not None and not self.closed and token is self.current and not token.is_set()

    def progress(self, callback):
        token = self.current

        def deliver(*args):
            if self.valid(token):
                callback(*args)

        def report(*args):
            if not self.valid(token):
                raise TaskCancelled()
            self.dispatch(deliver, *args)
        return report

    def run(self, work, done):
        token = self.current

        def deliver(result, error):
            if self.valid(token):
                done(result, error)

        def worker():
            if not self.valid(token):
                return
            try:
                result, error = work(), None
            except TaskCancelled:
                return
            except Exception as exc:
                result, error = None, str(exc)
            self.dispatch(deliver, result, error)

        thread = threading.Thread(target=worker, name="IPTVDream-worker")
        thread.daemon = True
        thread.start()
        return thread

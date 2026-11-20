# -*- coding: utf-8 -*-
"""Bind AI streaming responses to the existing gevent HTTP connection."""
import re
import socket

import gevent
from gevent.socket import wait_read
from geventwebsocket.gunicorn.workers import GeventWebSocketWorker
from geventwebsocket.handler import WebSocketHandler

DISCONNECT_HOOK = "rainbond.ai_proxy_watch_disconnect"
AI_PATH = re.compile(r"^/(?:console/regions/[^/]+/(?:backend|proxy)/plugins/rainbond-ai-engine/"
                     r"|openapi/v1/ai-engine/[^/]+/(?:regions/[^/]+/)?v1/)")


class AIProxyWebSocketHandler(WebSocketHandler):
    def get_environ(self):
        environ = super().get_environ()
        if AI_PATH.match(environ.get("PATH_INFO", "")):
            # A non-HTTP environ entry cannot be supplied by browser headers.
            environ[DISCONNECT_HOOK] = self._watch_disconnect
        return environ

    def _watch_disconnect(self):
        consumer = gevent.getcurrent()
        # Observe without sharing the WSGI body's gevent read watcher. A stale
        # readability notification must not make MSG_PEEK block on that reader.
        downstream = self.socket.dup()
        downstream.setblocking(False)
        active = True

        def watch():
            try:
                while active:
                    try:
                        wait_read(downstream.fileno())
                        data = downstream.recv(1, socket.MSG_PEEK)
                    except BlockingIOError:
                        continue
                    except (OSError, ValueError):
                        data = b""
                    if not data:
                        if active:
                            # Unwind the blocked read in its own greenlet. Concurrent
                            # response.close() can wait on the reader's buffer lock.
                            consumer.kill(block=False)
                        return
                    # Leave request/pipelined bytes untouched; the body reader
                    # may still be forwarding them to the upstream request.
                    gevent.sleep(0.1)
            finally:
                downstream.close()

        watcher = gevent.spawn(watch)

        def stop():
            nonlocal active
            active = False
            watcher.kill(block=False)
            downstream.close()

        return stop


class AIProxyWorker(GeventWebSocketWorker):
    wsgi_handler = AIProxyWebSocketHandler

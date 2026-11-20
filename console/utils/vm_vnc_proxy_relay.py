# -*- coding: utf-8 -*-
"""Binary-only VNC relay; callers have already resolved and authorized the VMI."""
from django.http import HttpResponse


def relay_component_vnc(client_ws, upstream, backend_path):
    import gevent
    from websocket import ABNF, WebSocketTimeoutException, create_connection
    backend = None
    jobs = []
    try:
        target = ('wss://' + upstream[8:] if upstream.startswith('https://') else 'ws://' + upstream[7:]) + backend_path
        backend = create_connection(target, timeout=10)
        backend.settimeout(30)

        def to_backend():
            while True:
                data = client_ws.receive()
                if data is None:
                    return
                if not isinstance(data, (bytes, bytearray)):
                    return
                backend.send_binary(bytes(data))

        def to_client():
            while True:
                try:
                    opcode, data = backend.recv_data()
                except WebSocketTimeoutException:
                    continue
                if opcode == ABNF.OPCODE_CLOSE:
                    return
                if opcode == ABNF.OPCODE_BINARY:
                    client_ws.send(data, binary=True)
                elif opcode == ABNF.OPCODE_PING:
                    backend.pong(data)

        jobs = [gevent.spawn(to_backend), gevent.spawn(to_client)]
        gevent.joinall(jobs, count=1)
    except Exception:
        return HttpResponse('VNC connection unavailable', status=502)
    finally:
        for job in jobs:
            job.kill()
        if backend:
            try:
                backend.close()
            except Exception:
                pass
        try:
            client_ws.close()
        except Exception:
            pass
    return HttpResponse(status=204)

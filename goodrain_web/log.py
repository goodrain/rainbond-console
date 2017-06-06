import time
import socket
import logging
import zmq
from zmq.log.handlers import PUBHandler
from zmq.utils.strtypes import cast_bytes

TOPIC_DELIM = " :: "
HOSTNAME = socket.gethostname()


class MyLogRecord(logging.LogRecord):

    def __init__(self, name, level, pathname, lineno,
                 msg, args, exc_info, func=None):
        if args and '%' not in msg:
            arg = args[0]

            try:
                if isinstance(arg, unicode):
                    msg = u'{0}{1}{2}'.format(msg, TOPIC_DELIM, arg)
                else:
                    msg = '{0}{1}{2}'.format(msg, TOPIC_DELIM, arg)
            except Exception:
                print "type is %s" % type(arg)
                print "arg is", arg
            finally:
                args = []

        super(MyLogRecord, self).__init__(name, level, pathname, lineno,
                                          msg, args, exc_info, func=func)


logging.LogRecord = MyLogRecord


class ZmqHandler(PUBHandler):

    def __init__(self, address, root_topic):
        logging.Handler.__init__(self)

        self.ctx = zmq.Context()
        self.socket = None
        if '.' in root_topic:
            raise AttributeError("root_topic should not contains any '.', provided '%s'" % root_topic)
        self.root_topic = root_topic
        self.zmq_address = address

    def is_connected(self):
        return bool(self.socket is not None)

    def connect(self):
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.connect(self.zmq_address)

    def format(self, record):
        fmt = self.formatter
        return fmt.format(record)

    def emit(self, record):
        """Emit a log message on my socket."""

        try:
            topic, record.msg = record.msg.split(TOPIC_DELIM, 1)
        except Exception:
            topic = "untopic"

        record.__dict__['hostname'] = HOSTNAME

        try:
            bmsg = cast_bytes(self.format(record))
        except Exception:
            self.handleError(record)
            return

        topic_list = [self.root_topic, topic]

        btopic = b'.'.join(cast_bytes(t) for t in topic_list)
        blevel = cast_bytes(record.levelname)

        if not self.is_connected():
            self.connect()
            time.sleep(0.1)
        self.socket.send_multipart([btopic, blevel, bmsg])

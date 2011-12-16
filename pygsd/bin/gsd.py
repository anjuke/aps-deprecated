#!/usr/bin/env python

import getopt
import sys
import os
import subprocess
import signal
import time
from collections import deque
import msgpack
import zmq

VERSION = r'APS10'
EMPTY = r''

def microtime():
    return int(round(time.time() * 1000 * 1000))

def millitime():
    return int(round(time.time() * 1000))

class Workers:
    def __init__(self):
        self.workers = {}
        self.queue = deque()

    def is_available(self):
        if self.queue:
            return True
        else:
            return False

    def add(self, wid):
        if wid not in self.workers or self.workers[wid][1]:
            self.queue.append(wid)
        self.workers[wid] = (millitime(), False)

    def remove(self, wid):
        del self.workers[wid]
        self.queue.remove(wid)

    def borrow(self):
        try:
            wid = self.queue.popleft()
        except IndexError:
            return None
        else:
            self.workers[wid] = (self.workers[wid], True)
            return wid

    def order_than(self, expire_time):
        return [wid for wid, (timestamp, status)
                in self.workers.items()
                if timestamp < expire_time]

class Device():
    def __init__(self, options):
        self.options = options
        self.workers = Workers()
        self.pendings = deque()
        self.pids = set()

        def create_socket(socktype, endpoints):
            socket = zmq.Socket(zmq.Context.instance(), socktype)
            socket.setsockopt(zmq.LINGER, 0)
            for endpoint in endpoints:
                socket.bind(endpoint)
            return socket

        self.client_socket = create_socket(zmq.XREP, self.options.feps)
        self.worker_socket = create_socket(zmq.XREP, self.options.beps)
        self.monitor_socket = create_socket(zmq.PUB, self.options.meps)

        self.interrupted = False
        self.last_maintain = 0

        signal.signal(signal.SIGCHLD, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        print "SIG: ", signum
        if signum == signal.SIGCHLD:
            pid, status = os.waitpid(-1, os.WNOHANG)
            self.pids.discard(pid)
            self.workers.remove(str(pid))
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            for pid in self.pids:
                os.kill(pid, signum)
            print "Terminated:", signum
            self.interrupted = True

    def start(self):
        self.loop()

    def stop(self):
        self.interrupted = True
    
    def maintain(self):
        now = millitime()
        
        if now - self.last_maintain < self.options.interval:
            return

        # TODO:
        # remove dead workers
        # remove spare workers

        # create new workers
        spare = len(self.workers.queue)
        total = len(self.workers.workers)
        if total < self.options.minw:
            for i in xrange(total, self.options.minw):
                self.fork_worker()

        self.last_maintain = now

    def fork_worker(self):
        if len(self.pids) < self.options.maxw:
            p = subprocess.Popen(self.options.args)
            self.pids.add(p.pid)

    def loop(self):
        poller = zmq.Poller()
        poller.register(self.client_socket, zmq.POLLIN)
        poller.register(self.worker_socket, zmq.POLLIN)
        while not self.interrupted:
            self.maintain()

            try:
                events = poller.poll(self.options.interval)
            except zmq.ZMQError as e:
                if e.errno == 4:    # system interrupted
                    continue
                else:
                    pass

            for socket, flags in events:
                if socket == self.worker_socket:
                    self.handle_worker()
                elif socket == self.client_socket:
                    self.handle_client()
                else:
                    assert False

    def handle_client(self):
        while True:
            try:
                frames = self.client_socket.recv_multipart(zmq.NOBLOCK)
            except zmq.ZMQError as e:
                if e.errno == 35:   # no more message to handle
                    break
                else:
                    pass

            self.forward_to_worker(frames)

    def forward_to_worker(self, frames):
        i = frames.index(EMPTY)
        if frames[i+1] != VERSION:
            pass # handle version mismatch
        sequence, timestamp, expiry = msgpack.unpackb(frames[i+2])
        # handle expired

        wid = self.workers.borrow()
        if not wid:
            self.pendings.append(frames)
            self.fork_worker()
        else:
            frames = self.build_worker_request(wid, frames[:i], frames[i+2:])
            self.worker_socket.send_multipart(frames)
        
        return wid

    def handle_pendings(self):
        while self.pendings:
            frames = self.pendings.popleft()
            if not self.forward_to_worker(frames):
                break

    def handle_worker(self):
        while True:
            try:
                frames = self.worker_socket.recv_multipart(zmq.NOBLOCK)
            except zmq.ZMQError as e:
                if e.errno == 35:   # no more message to handle
                    break
                else:
                    pass

            i = frames.index(EMPTY)
            assert(i == 1)
            wid = frames[0]

            if frames[i+1] != VERSION:
                pass # handle version mismatch

            command = frames[i+2]
            if command == '\x00':   # REQUEST
                j = frames.index(EMPTY, i+3)
                frames = self.build_client_reply(frames[i+3:j], frames[j+1:])
                self.client_socket.send_multipart(frames)
                self.workers.add(wid)
                self.handle_pendings()

            elif command == '\x01': # HEARTBEAT
                self.workers.add(wid)
                self.handle_pendings()

            elif command == '\x02': # GOODBYE
                pass #

            else:
                pass # handle unknown command   

    def build_worker_request(self, wid, envelope, body):
        frames = [wid, EMPTY, VERSION, '\x00']
        frames.extend(envelope)
        frames.append(EMPTY)
        frames.extend(body)
        return frames

    def build_client_reply(self, envelope, body):
        frames = envelope[:]
        frames.append(EMPTY)
        frames.append(VERSION)
        frames.extend(body)
        return frames


class Options:
    """
options:
    -h, --help            
        Show this help message and exit

    -f <endpoint>, --frontend=<endpoint>
        The binding endpoints where clients will connect to
        [default: tcp://*:5000]

    -b <endpoint>, --backend=<endpoint>
        The binding endpoints where workers will connect to
        [default: ipc:///tmp/gsd-{pid}.ipc]

    -m <endpoint>, --monitor=<endpoint>
        The binding endpoints where monitor events will be published to

    -n, --min-worker=<num>
        The mininum number of workers should be started before accepting 
        request [default: 1]

    -x, --max-worker=<num> 
        The maxinum number of workers [default: 32]

    -s, --spare-worker=<num>
        The maxinum number of spare workers [default: 8]

    --timeout=<milliseconds>
        Worker timeout in millisecond [default: 10000]
    
    --interval=<milliseconds>
        Maintain interval in millisecond [default: 1000]
    
    -d, --daemon

    -v, --verbose
    """

    def __init__(self, argv):
        self.prog = os.path.basename(argv[0])

        self.feps = []       # frontend endpoints
        self.beps = []       # backend endpoints
        self.meps = []       # monitor endpoints
        self.minw = 1        # min worker
        self.maxw = 32       # max worker
        self.spaw = 8        # spare worker
        self.timeout = 10000 # worker timeout
        self.interval = 1000 # maintain interval
        self.args = []

        self.errno = 0
         
        try:
            self.parse(argv)
        except:
            self.errno = 2
            pass

    def parse(self, argv):
        opts, self.args = getopt.getopt(argv[1:], 'hf:b:m:n:x:s:i:dv', ['help',
            'frontend=', 'backend=', 'monitor=',
            'min-worker=', 'max-worker=', 'spare-worker=',
            'timeout=', 'interval=', 'daemon=', 'verbose='])

        for o, a in opts:
            if o in ('-h', '--help'):
                self.usage()
                self.errno = 1
                return
            elif o in ('-f', '--frontend'):
                self.feps.append(a)
            elif o in ('-b', '--backend'):
                self.beps.append(a)
            elif o in ('-m', '--monitor'):
                self.meps.append(a)
            elif o in ('-n', '--min-worker'):
                self.minw = int(a)
            elif o in ('-x', '--max-worker'):
                self.maxw = int(a)
            elif o in ('-s', '--spare-worker'):
                self.spaw = int(a)
            elif o in ('--timeout='):
                self.timeout = int(a)
            elif o in ('--interval='):
                self.interval = int(a)
            elif o in ('-d', '--daemon'):
                self.daemon = True
            elif o in ('-v', '--verbose'):
                self.verbose = True
            else:
                pass

        if (not self.args):
            self.errno = 3

        if not self.feps:
            self.feps = ['tcp://*:5000']
        if not self.beps:
            self.beps = ['ipc:///tmp/gsd-{}.ipc'.format(os.getpid())]

    def usage(self):
        print('usage: %s [options] <worker command line>' % self.prog)
        print self.__doc__
        sys.exit(1)


def main():
    options = Options(sys.argv)
    if options.errno:
        options.usage()
        return options.errno

    device = Device(options)
    device.start()


if __name__ == '__main__':
    sys.exit(main())

__all__ = []


#!/usr/bin/env python

import getopt
import sys
import os
import subprocess
import time
import msgpack
import zmq
from zmq.eventloop import ioloop, zmqstream

VERSION = r'APS10'
EMPTY = r''

def microtime():
    return int(round(time.time() * 1000 * 1000))

def millitime():
    return int(round(time.time() * 1000))

class GSD:
    feps = []       # frontend endpoints
    beps = []       # backend endpoints
    meps = []       # monitor endpoints
    minw = 1        # min worker
    maxw = 32       # max worker
    spaw = 8        # spare worker
    timeout = 10000 # worker timeout
    interval = 1000 # maintain interval
    args = []

    def start(self):
        for i in xrange(self.minw):
            self.create_worker()

        self.spare_workers = []
        self.workers = {}

        self.pending_requests = []  # to hold requests if there's no worker available

        def create_socket(socktype, endpoints):
            socket = zmq.Socket(zmq.Context.instance(), socktype)
            socket.setsockopt(zmq.LINGER, 0)
            for endpoint in endpoints:
                socket.bind(endpoint)
            return socket

        if self.feps:
            feps = self.feps
        else:
            feps = ['tcp://*:5000']
        if self.beps:
            beps = self.beps
        else:
            beps = ['tcp://*:5001']
        if self.meps:
            meps = self.meps
        else:
            meps = ['tcp://*:5002']

        self.client_socket = create_socket(zmq.XREP, feps)
        self.worker_socket = create_socket(zmq.XREP, beps)
        self.monitor_socket = create_socket(zmq.PUB, meps)

        self.loop = ioloop.IOLoop.instance()
        self.client_stream = zmqstream.ZMQStream(self.client_socket, self.loop)
        self.worker_stream = zmqstream.ZMQStream(self.worker_socket, self.loop)
        self.monitor_stream = zmqstream.ZMQStream(self.monitor_socket, self.loop)

        self.client_stream.on_recv(self.handle_client)
        self.worker_stream.on_recv(self.handle_worker)

        self.maintainer = ioloop.PeriodicCallback(self.maintain, self.interval, self.loop)

        self.maintainer.start()
        self.loop.start()

    def stop(self):
        self.loop.stop()

    def maintain(self):
        self.maintain_workers()

    def handle_client(self, frames):
        i = frames.index(EMPTY)
        if frames[i+1] != VERSION:
            pass # handle version mismatch
        sequence, timestamp, expiry = msgpack.unpackb(frames[i+2])
        # handle expired

        wid = self.borrow_worker()
        if wid:
            frames = self.build_worker_request(wid, frames[:i], frames[i+2:])
            self.worker_stream.send_multipart(frames)
        else:
            self.pending_requests.append(frames)

        return wid

    def handle_pending_requests(self):
        while self.pending_requests:
            frames = self.pending_requests.pop(0)
            if not self.handle_client(frames):
                break

    def handle_worker(self, frames):
        i = frames.index(EMPTY)
        assert(i == 1)
        wid = frames[0]

        if frames[i+1] != VERSION:
            pass # handle version mismatch

        command = frames[i+2]
        if command == '\x00':   # REQUEST
            j = frames.index(EMPTY, i+3)
            frames = self.build_client_reply(frames[i+3:j], frames[j+1:])
            self.client_stream.send_multipart(frames)
            self.return_worker(wid)
            self.handle_pending_requests()

        elif command == '\x01': # HEARTBEAT
            self.return_worker(wid)
            self.handle_pending_requests()

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

    def create_worker(self):
        p = subprocess.Popen(self.args)
        print p.pid

    def borrow_worker(self):
        if not self.spare_workers:
            return None

        wid = self.spare_workers.pop(0)
        (timestamp, leased) = self.workers[wid]
        self.workers[wid] = (timestamp, True)
        return wid

    def return_worker(self, wid):
        try:
            (timestamp, leased) = self.workers[wid]
        except KeyError:
            self.spare_workers.append(wid)
        else:
            if leased:
                self.spare_workers.append(wid)

        self.workers[wid] = (millitime(), False)

    def maintain_workers(self):
        return
        """ 1. terminate dead workers """
        """ 2. create new worker if too few """
        """ 3. terminate spare workers if too many """
        now = millitime()
        expiry = now - self.timeout
        size = len(self.spare_workers)
        i = 0
        while i < size:
            wid, timestamp = self.spare_workers[i]
            if timestamp >= expiry: 
                break
            i += 1
        expired_spare_workers = self.spare_workers[:i]
        expired_leased_workers = list(wid
            for wid, timestamp in self.leased_workers.iteritems() if timestamp < expiry)

        self.spare_workers = self.spare_workers[i+1:]
        for wid in expired_leased_workers:
            del self.leased_workers[wid]

        # say GOODBYE to workers?
        # kill the process?



def usage():
    print('usage: %s [options] <worker command line>' % os.path.basename(sys.argv[0]))
    print """
options:
    -h, --help            
        Show this help message and exit

    -f <endpoint>, --frontend=<endpoint>
        The binding endpoints where clients will connect to
        [default: tcp://*:5000]

    -b <endpoint>, --backend=<endpoint>
        The binding endpoints where workers will connect to
        [default: ipc://tmp/(pid-of-gsd).ipc]

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
        Worker timeout in millisecond [default: 1000]
    
    --interval=<milliseconds>
        Maintain interval in millisecond [default: 1000]
    
    -d, --daemon

    -v, --verbose
"""
    sys.exit(2)

def main():
    print "Generic Service Daemon"
    print
    gsd = GSD()

    # parse args
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hf:b:m:n:x:s:i:dv', ['help',
            'frontend=', 'backend=', 'monitor=',
            'min-worker=', 'max-worker=', 'spare-worker=',
            'timeout=', 'interval=', 'daemon=', 'verbose='])
    except getopt.GetoptError, err:
        usage()

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-f', '--frontend'):
            gsd.feps.append(a)
        elif o in ('-b', '--backend'):
            gsd.beps.append(a)
        elif o in ('-m', '--monitor'):
            gsd.meps.append(a)
        elif o in ('-n', '--min-worker'):
            gsd.minw = int(a)
        elif o in ('-x', '--max-worker'):
            gsd.maxw = int(a)
        elif o in ('-s', '--spare-worker'):
            gsd.spaw = int(a)
        elif o in ('--timeout='):
            gsd.timeout = int(a)
        elif o in ('--interval='):
            gsd.interval = int(a)
        elif o in ('-d', '--daemon'):
            pass
        elif o in ('-v', '--verbose'):
            verbose = True
        else:
            usage()

    if (not args):
        usage()

    gsd.args = args

    gsd.start()
    return 0


if __name__ == '__main__':
    sys.exit(main())

__all__ = []


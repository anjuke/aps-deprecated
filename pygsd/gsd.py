
import getopt
import sys
import os
import time
import zmq
from zmq.eventloop import ioloop, zmqstream

def microtime():
    return int(round(time.time() * 1000 * 1000))

def millitime():
    return int(round(time.time() * 1000))

VERSION = r'APS10'
EMPTY = r''

class GSD:
    def __init__(self, args, feps, beps, meps, maxw, minw, spaw, hbi):
        self.worker_cmd = args

        self.maxw = maxw    # max num of workers
        self.minw = minw    # min num of workers
        self.spaw = spaw    # spare workers
        self.maintain_period = hbi;
        self.heartbeat_timeout = hbi << 2;

        self.spare_workers =  []    # item is tuple (wid, timestamp)
        self.leased_workers = {}    # item is wid: timestamp

        self.pending_requests = []  # to hold requests if there's no worker available



        self.client_socket = self.create_socket(zmq.XREP, feps)
        self.worker_socket = self.create_socket(zmq.XREP, beps)
        self.monitor_socket = self.create_socket(zmq.PUB, meps)

        self.loop = ioloop.IOLoop.instance()
        self.client_stream = zmqstream.ZMQStream(self.client_socket, self.loop)
        self.worker_stream = zmqstream.ZMQStream(self.worker_socket, self.loop)
        self.monitor_stream = zmqstream.ZMQStream(self.monitor_socket, self.loop)

        self.client_stream.on_recv(self.handle_client)
        self.worker_stream.on_recv(self.handle_worker)

        self.maintainer = ioloop.PeriodicCallback(self.maintain, self.maintain_period, self.loop)

    def create_socket(self, socktype, endpoints):
        socket = zmq.Socket(zmq.Context.instance(), socktype)
        socket.setsockopt(zmq.LINGER, 0)
        for endpoint in endpoints:
            socket.bind(endpoint)
        return socket

    def start(self):
        self.maintainer.start()
        self.loop.start()

    def stop(self):
        self.loop.stop()

    def maintain(self):
        self.maintain_workers()
        pass

    def handle_client(self, frames):
        frames = client_socket.recv_multiparts()
        i = frames.index[EMPTY]
        if frames[i+1] != VERSION:
            pass # handle version mismatch
        sequence, timestamp, expiry = msgpack.unpackb(frames[i+2])
        # handle expired

        wid = self.borrow_worker()
        if wid:
            frames = self.build_worker_request(self, wid, frames[:i], frames[i+2:])
            self.worker_stream.send_multipart(frames)
        else:
            self.pending_requests.push(frames)
            # TODO: warning

    def handle_pending_requests(self):
        while self.pending_requests:
            frames = self.pending_requests.pop(0)
            handle_client(frames)

    def handle_worker(self, frames):
        i = frames.index[EMPTY]
        assert(i == 1)
        wid = frames[0]

        if frames[i+1] != VERSION:
            pass # handle version mismatch

        command = frames[i+2]
        if command == '\x00':   # REQUEST
            j = frames.index[EMPTY, i+3]
            frames = build_client_reply(frames[i+3,j], frames[j+1])
            client_socket.send_multipart(frames)
            self.return_worker(wid)
            self.handle_pending_requests()

        elif command == '\x01': # HEARTBEAT
            self.return_worker(wid)
            self.handle_pending_requests()

        elif command == '\x02': # GOODBYE
            pass #

        else:
            pass # handle unknown command

    def build_worker_request(self, worker_envelope, envelope, body):
        frames = worker_envelope[:]
        frames.append(EMPTY)
        frames.append(VERSION)
        frames.append('\x00')
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

    def borrow_worker(self):
        wid, timestamp = self.spare_workers.pop(0)
        self.leased_workers[wid] = timestamp
        return wid

    def return_worker(self, wid):
        del self.leased_workers[wid]
        self.spare_workers.append((wid, millitime()))

    def maintain_workers(self):
        """ 1. terminate dead workers """
        """ 2. create new worker if too few """
        """ 3. terminate spare workers if too many """
        now = millitime()
        deadtime = now - self.heartbeat_timeout
        size = len(self.spare_workers)
        i = 0
        while i < size:
            wid, timestamp = self.spare_workers[i]
            if timestamp > deadtime: 
                break
            i += 1
        dead_spare_workers = self.spare_workers[:i]
        dead_leased_workers = list(wid
            for wid, timestamp in self.leased_workers.iteritems() if timestamp > deadtime)

        self.spare_workers = self.spare_workers[i+1:]
        for wid in dead_leased_workers:
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

    --hearbeat-interval=<milliseconds>
        Heartbeat interval in millisecond [default: 1000]
    
    -d, --daemon

    -v, --verbose
"""
    sys.exit(2)


def parse_args(argv):
    feps = []       # frontend endpoints
    beps = []       # backend endpoints
    meps = []       # monitor endpoints
    minw = 1        # min worker
    maxw = 32       # max worker
    spaw = 8        # spare worker
    hbi = 1000      # heartbeat interval
    
    try:
        opts, args = getopt.getopt(argv, 'hf:b:m:n:x:s:i:dv', ['help',
            'frontend=', 'backend=', 'monitor=',
            'min-worker=', 'max-worker=', 'spare-worker=',
            'heartbeat-interval=', 'daemon=', 'verbose='])
    except getopt.GetoptError, err:
        usage()

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-f', '--frontend'):
            feps.append(a)
        elif o in ('-b', '--backend'):
            beps.append(a)
        elif o in ('-m', '--monitor'):
            meps.append(a)
        elif o in ('-n', '--min-worker'):
            minw = int(a)
        elif o in ('-x', '--max-worker'):
            maxw = int(a)
        elif o in ('-s', '--spare-worker'):
            maxiw = int(a)
        elif o in ('--hearbeat-interval='):
            hbi = int(a)
        elif o in ('-d', '--daemon'):
            pass
        elif o in ('-v', '--verbose'):
            pass
        else:
            usage()

    if (not args):
        usage()

    return (args, feps, beps, meps, maxw, minw, spaw, hbi)

def main():
    print "Generic Service Daemon"
    print
    args, feps, beps, meps, maxw, minw, spaw, hbi = parse_args(sys.argv[1:])
    gsd = GSD(args, feps, beps, meps, maxw, minw, spaw, hbi)
    gsd.start()
    return 0


if __name__ == '__main__':
    sys.exit(main())

__all__ = []


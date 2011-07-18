
import getopt
import sys
import os


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
    minw = 1        # min worker
    maxw = 32       # max worker
    spaw = 8        # spare worker
    hbi = 1000      # heartbeat interval
    
    try:
        opts, args = getopt.getopt(argv, 'hf:b:n:x:s:i:dv', ['help',
            'frontend=', 'backend=', 'min-worker=', 'max-worker=', 'spare-worker=',
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
        elif o in ('-n', '--min-worker'):
            minw = a
        elif o in ('-x', '--max-worker'):
            maxw = a
        elif o in ('-s', '--spare-worker'):
            maxiw = a
        elif o in ('--hearbeat-interval='):
            hbi = a
        elif o in ('-d', '--daemon'):
            pass
        elif o in ('-v', '--verbose'):
            pass
        else:
            usage()

    if (not args):
        usage()

    return (args, feps, beps, maxw, minw, spaw, hbi)

def main():
    print "Generic Service Daemon"
    print
    print parse_args(sys.argv[1:])
    return 0


if __name__ == '__main__':
    sys.exit(main())


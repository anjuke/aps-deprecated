
import struct
import zmq

VERSION = 'APS10'
EMPTY = r'';
REQUEST = struct.pack(r'b', 0);
HEARTBEAT = struct.pack(r'b', 1);
GOODBYE = struct.pack(r'b', 2);

class APSError(Exception):
    def __init__(self, value):
        super(APSError, self).__init__(value)

def envelope_unwrap(frames):
    try:
        i = frames.index(EMPTY)
        envelope, body = frames[:i], frames[i+1:]
    except ValueError:
        return ([], frames)
    else:
        return (envelope, body)

def envelope_wrap(envelope, body):
    frames = envelope[:]
    frames.append(EMPTY)
    frames.extend(body)
    return frames

def parse_client_request(frames):
    try:
        version = frames[0]
        sequence, timestamp, expiry = struct.unpack('>3L', frames[1])
        method = frames[2]
        body = frames[3:]
    except:
        raise APSError('invalid client request')
    else:
        return (version, sequence, timestamp, expiry, method, body)


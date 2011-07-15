<?php
require_once dirname(__FILE__) . '/aps-functions.php';

/**
 *
 */
class APSClient {
    const VERSION = 'APS10';

    /**
     * @params $context ZMQContext
     * @params $endpoints array of endpoint the client will connect to.
     */
    public function __construct($context, $endpoints) {
        $socket = new ZMQSocket($context, ZMQ::SOCKET_XREQ);
        $socket->setsockopt(ZMQ::SOCKOPT_LINGER, 0);
#        $socket->setsockopt(ZMQ::SOCKOPT_HWM, 10);
        foreach ($endpoints as $endpoint) {
            $socket->connect($endpoint);
        }

        self::$sockets[] = $socket;
        $this->socket = $socket;
    }

    public function __destruct () {
        $i = array_search($this->socket, self::$sockets, true);
        unset(self::$sockets[$i]);
    }

    protected $socket;

    protected $pending_request_count;

    protected static $sockets = array();
    protected static $pending_requests = array();
    protected static $sequence = 0;


    /**
     */
    public function start_request($method, $params, $callback, $expiry = 0) {
        $sequence = ++self::$sequence;
        $timestamp = aps_millitime();

        $frames[] = '';
        $frames[] = self::VERSION;
        $frames[] = pack('N*', $sequence, $timestamp, $expiry);
        $frames[] = msgpack_pack(array($method, $params));

        aps_send_frames($this->socket, $frames);

        self::$pending_requests[$sequence] = array($this, $callback);

        return $sequence;
    }

    /**
     * @params $clients array of client to poll
     * @params $timeout in millisecond
     *
     * @return The count of pending request
     */
    public static function wait_for_replies($timeout = NULL) {
        $poll = new ZMQPoll();
        foreach (self::$sockets as $socket) {
            $poll->add($socket, ZMQ::POLL_IN);
        }
        $readable = $writeable = array();
        if ($timeout !== NULL) {
            $bt = aps_microtime();
            $timeout_micro = $timeout * 1000;
        } else {
            $timeout_micro = -1;
        }
        while (count(self::$pending_requests) > 0) {
            $events = $poll->poll($readable, $writeable, $timeout_micro);
            if ($events == 0) {
                break;
            }

            foreach ($readable as $socket) {
                self::process_reply($socket);
            }

            if ($timeout !== NULL) {
                $timeout_micro -= ($bt - aps_microtime());
                if ($timeout_micro <= 0) {
                    break;
                }
            }
        }
        return count(self::$pending_requests);
    }
    
    /**
     */
    protected static function process_reply($socket) {
        $frames = aps_recv_frames($socket);
        list($envelope, $message) = aps_envelope_unwrap($frames);
        $version = array_shift($message);
        list($sequence, $timestamp, $status) = array_values(unpack('N*', array_shift($message)));

        $reply = array_shift($message);
        if ($reply !== NULL) {
            $reply = msgpack_unpack($reply);
        }

        list($client, $callback) = self::$pending_requests[$sequence];
        unset(self::$pending_requests[$sequence]);

        call_user_func_array($callback, array($reply, $status));
    }
}


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
        $socket->setsockopt(ZMQ::SOCKOPT_HWM, 1000);
        foreach ($endpoints as $endpoint) {
            $socket->connect($endpoint);
        }

        self::$sockets[] = $socket;
        $this->socket = $socket;
        $this->expiry = 1000;
    }

    public function __destruct () {
        $i = array_search($this->socket, self::$sockets, true);
        unset(self::$sockets[$i]);
    }

    protected $socket;

    protected $pending_request_count;

    protected $expiry;

    protected static $sockets = array();
    protected static $pending_requests = array();
    protected static $sequence = 0;

    protected static $replies = array();

    public function set_expiry($expiry) {
        $this->expirt = $expiry;
    }

    public function get_expiry() {
        return $this->expirt;
    }

    public function set_default_callback($callback) {
        $this->default_callback = $callback;
    }

    /**
     */
    public function start_request($method, $params, $callback = NULL, $expiry = NULL) {
        $sequence = ++self::$sequence;
        $timestamp = aps_millitime();
        if ($expiry === NULL) {
            $expiry = $this->expiry;
        }

        $frames[] = '';
        $frames[] = self::VERSION;
        $frames[] = msgpack_pack(array($sequence, $timestamp, $expiry));
        $frames[] = $method;
        $frames[] = msgpack_pack($params);

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

    public static function fetch_reply($sequence, $keep = false) {
        if (!isset(self::$replies[$sequence])) {
            return array(NULL, 101);
        }
        $rs = self::$replies[$sequence];
        if (!$keep) {
            unset(self::$replies[$sequence]);
        }
        return $rs;
    }

    protected static function store_reply($sequence, $reply, $status) {
        self::$replies[$sequence] = array($reply, $status);
    }
    
    /**
     */
    protected static function process_reply($socket) {
        $frames = aps_recv_frames($socket);
        list($envelope, $message) = aps_envelope_unwrap($frames);
        $version = array_shift($message);
        list($sequence, $timestamp, $status) = msgpack_unpack(array_shift($message));

        $reply = array_shift($message);
        if ($reply !== NULL) {
            $reply = msgpack_unpack($reply);
        }

        list($client, $callback) = self::$pending_requests[$sequence];
        unset(self::$pending_requests[$sequence]);

        if (!$callback) {
            $callback = $client->default_callback;
        }
        if ($callback) {
            call_user_func_array($callback, array($reply, $status));
        } else {
            self::store_reply($sequence, $reply, $status);
        }
    }

    /**
     */
    public function __call($name, $args) {
        return $this->start_request($name, $args, NULL, $this->expiry);
    }
}


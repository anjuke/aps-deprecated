<?php
require_once dirname(__FILE__) . '/aps-functions.php';

/**
 */
class APSDevice {
    const VERSION = 'APS10';

    public function __construct($context, $frontend, $backend) {
        $socket = new ZMQSocket($context, ZMQ::SOCKET_XREP);
        $socket->setsockopt(ZMQ::SOCKOPT_LINGER, 0);        
        $socket->bind($frontend);
        $this->socket_c = $socket;

        $socket = new ZMQSocket($context, ZMQ::SOCKET_XREP);
        $socket->setsockopt(ZMQ::SOCKOPT_LINGER, 0);        
        $socket->bind($backend);
        $this->socket_w = $socket;

        $this->interval = 1000 * 1000;
        $this->interrupted = false;

        $this->workers = array();
    }

    public function run() {
        while (!$this->interrupted) {
            $poll = new ZMQPoll();
            if (!empty($this->workers)) {
                $poll->add($this->socket_c, ZMQ::POLL_IN);
            }
            $poll->add($this->socket_w, ZMQ::POLL_IN);
            $readable = $writeable = array();
            $events = $poll->poll($readable, $writeable, $this->interval);
            if ($events == 0) {
                continue;
            }

            foreach ($readable as $socket) {
                if ($socket === $this->socket_c) {
                    $this->client_process();
                } elseif ($socket === $this->socket_w) {
                    $this->worker_process();
                }
            }
        }
    }

    protected function client_process() {
        $worker = array_shift($this->workers);
        $w = @array_shift(unpack('H*', $worker));
        echo "$w\n";

        $frames = aps_recv_frames($this->socket_c);

        list($envelope, $message) = aps_envelope_unwrap($frames);
        $version = array_shift($message);
        
        // TODO: check expiry?

        $frames = array($worker, '', self::VERSION, chr(0x00));
        $frames = array_merge($frames, $envelope, array(''), $message);
        aps_send_frames($this->socket_w, $frames);
    }

    protected function worker_process() {
        $frames = aps_recv_frames($this->socket_w);

        list($envelope, $message) = aps_envelope_unwrap($frames);
        $worker = $envelope[0];
        $version = array_shift($message);
        $command = ord(array_shift($message));

        if ($command == 0x00) {
            list($envelope, $message) = aps_envelope_unwrap($message);
            array_unshift($message, self::VERSION);
            $frames = aps_envelope_wrap($envelope, $message);
            aps_send_frames($this->socket_c, $frames);
            array_push($this->workers, $worker);

        } elseif ($command == 0x01) {
            if (array_search($worker, $this->workers, true) === false) {
                array_push($this->workers, $worker);
            }

        } elseif ($command == 0x02) {
            // TODO:
        }
    }
}


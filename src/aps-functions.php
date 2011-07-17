<?php
function aps_microtime() {
    return round(microtime(true) * 1000000);
}

function aps_millitime() {
    return round(microtime(true) * 1000);
}

/**
 * Receive frames from a given socket. This function will be blocked until
 * frames received. So usally poll the socket before invoke receive.
 *
 * @param $socket ZMQSocket
 * @return array of frame
 */
function aps_recv_frames($socket) {
    $frames = array();
    do {
        $frames[] = $socket->recv();
    } while ($socket->getsockopt(ZMQ::SOCKOPT_RCVMORE));
    return $frames;
}

/**
 * Send frames to the given socket.
 *
 * @param $socket ZMQSocket
 * @param $frame array of frame to be send
 */
function aps_send_frames($socket, $frames) {
    $last = array_pop($frames);
    foreach ($frames as $frame) {
        $socket->send($frame, ZMQ::MODE_SNDMORE);
    }
    $socket->send($last);
}

/**
 * Unwrap the envelope from frames. Return empty envelope if there's no envelop
 * delimiter(The empty frame) found.
 * Usally use list($envelope, $messages) to split the returns array.
 *
 * @param @frames array of frame
 * @return array($envelope, $message)
 */
function aps_envelope_unwrap($frames) {
    $i = array_search('', $frames, true);
    if ($i === NULL) {
        return array(array(), $frames);
    }
    return array(array_slice($frames, 0, $i), array_slice($frames, $i + 1));
}

/**
 * Wrap the envelope to the given frames. The empty frame delimiter will be
 * add between the envelope and the message.
 *
 * @param $envelope array of envelope frame
 * @param $message array of message frame
 */
function aps_envelope_wrap($envelope, $message) {
    return array_merge($envelope, array(''), $message);
}

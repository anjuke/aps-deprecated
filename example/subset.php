<?php
$a = $argv[1];
$b = $argv[2];

if (!$a || !$b) {
    die("Usage:prog <expression> <expression>\n");
}

require_once dirname(__FILE__) . '/../src/aps-client.php';
$context = new ZMQContext();

// async
echo "\nStart async RPC\n";
$bt = aps_microtime();
$client = new APSClient($context, array('tcp://127.0.0.1:5000'));

function invoke_is_subset($a, $b) {
    global $client;
    $client->start_request('is_subset', array($a, $b),
        function($reply) use ($a, $b) {
            if ($reply) {
                print "'$a' is subset of '$b'\n";
            } else {
                print "'$a' is NOT subset of '$b'\n";
            }
        }
    );
}

invoke_is_subset($a, $b);
invoke_is_subset($b, $a);
echo "Wait for replies\n";

$pending = APSClient::wait_for_replies(4000);
if ($pending > 0) {
    echo "Timeout. $pending replies discarded\n";
}

echo "time:  ", aps_microtime() - $bt, " microseconds\n";

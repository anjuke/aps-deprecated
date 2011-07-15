<?php
require_once dirname(__FILE__) . '/../src/aps-client.php';
$context = new ZMQContext();

// async
echo "\nStart async RPC\n";
$bt = aps_microtime();
$client = new APSClient($context, array('tcp://127.0.0.1:5000'));
$client->start_request('sleep_for', array('1'),
    function($reply, $status) {
        echo "$reply\n";
    }
);
$client->start_request('sleep_for', array('2'),
    function($reply) {
        echo "$reply\n";
    }
);
echo "Wait for replies\n";
$pending = APSClient::wait_for_replies(4000);
if ($pending > 0) {
    echo "Timeout. $pending replies discarded\n";
}
echo "async: ", aps_microtime() - $bt, " microseconds\n";

// sync
echo "\nStart sync RPC\n";
$bt = aps_microtime();
require_once dirname(__FILE__) . '/demo-model.php';
$model = new DemoModel();
echo $model->sleep_for(1), "\n";
echo $model->sleep_for(2), "\n";
echo "sync:  ", aps_microtime() - $bt, " microseconds\n";

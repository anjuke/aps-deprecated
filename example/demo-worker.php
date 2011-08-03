<?php
require_once dirname(__FILE__) . '/../src/aps-worker.php';
require_once dirname(__FILE__) . '/demo-model.php';

$context = new ZMQContext();
#$worker = new APSWorker($context, 'tcp://127.0.0.1:5001');
$worker = new APSWorker($context, 'ipc:///tmp/gsd-'.posix_getppid().'.ipc');
$worker->delegate = new DemoModel(); 
$worker->run();

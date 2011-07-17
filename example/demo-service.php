<?php
require_once dirname(__FILE__) . '/../src/aps-device.php';

function fork_and_exec($cmd, $args=array()) {
    $pid = pcntl_fork();
    if ($pid > 0) {
        return $pid;
    } else if ($pid == 0) {
        pcntl_exec($cmd, $args);
        exit(0);
    } else {
        // TODO:
        die('could not fork');
    }
}

$context = new ZMQContext();

$frontend = 'tcp://127.0.0.1:5000';
$backend = 'tcp://127.0.0.1:5001';

$device = new APSDevice($context, $frontend, $backend);

print_r($argv);
if (isset($argv[1])) {
    $c = $argv[1];
} else {
    $c = 5;
}

$pids = array();
$worker = dirname(__FILE__) . '/demo-worker.php';
for ($i = 0; $i < $c; $i++) {
    $pids[] = fork_and_exec('/usr/bin/env', array('php', $worker));
}
register_shutdown_function(function($pids) {
    foreach($pids as $pid) {
        posix_kill($pid, SIGTERM);
    }
}, $pids);


$device->run();


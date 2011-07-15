<?php
class DemoModel {
    function md5($data) {
        return md5($data);
    } 

    function sha($data) {
        return sha1($data);
    }

    function sleep_for($second) {
        sleep($second);
        return "Sleep $second";
    }
}

Anjuke PHP Service
==================

We introduce three simple method to APF framework.

- publish()
- start_request()
- wait_for_replies()

```php
<?php
$apf->publish('DEBUG', $_SERVER);

start_request('sql-executor')->query('table_a',
    'SELECT count(*) FROM table_a WHERE field = 123',
    function($reply, $status) use (&$count_a) {
        if ($status == 200) { $count_a = $reply->rows[0][0]; }
    }
);
start_request('solr-executor')->query('index_a',
    'q=*:*&sort=score+desc'
    function($reply) use (&$count_b) {
        if ($reply) { $count_b = $reply->records; }
    }
);
wait_for_replies();
echo $count_b, $count_b, "\n";
```

See the [Specification][spec] for details.

Note: PHP extenstion for [ZeroMQ][zeromq] and [MessagePack][msgpack] required

[spec]: https://github.com/anjuke/aps/blob/master/doc/aps-spec.asciidoc
[zeromq]: http://www.zeromq.org/
[msgpack]: http://msgpack.org/

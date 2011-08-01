import unittest
import msgpack
from aps import *

class APSTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_envelope_unwrap(self):
        self.assertEqual(envelope_unwrap([]), ([], []))
        self.assertEqual(envelope_unwrap(['part1', 'part2']), (
            [], ['part1', 'part2']))
        self.assertEqual(envelope_unwrap([EMPTY, 'part1', 'part2']), (
            [], ['part1', 'part2']))
        self.assertEqual(envelope_unwrap(['head', EMPTY, 'body']), (
            ['head'], ['body']))
        self.assertEqual(envelope_unwrap(['head1', 'head2', EMPTY, 'part1', 'part2']), (
            ['head1', 'head2'], ['part1', 'part2']))
        self.assertEqual(envelope_unwrap(['head1', 'head2', EMPTY, 'part1', EMPTY, 'part2']), (
            ['head1', 'head2'], ['part1', EMPTY, 'part2']))
        self.assertEqual(envelope_unwrap(['head1', 'head2', EMPTY, EMPTY, 'part1', 'part2']), (
            ['head1', 'head2'], [EMPTY, 'part1', 'part2']))

    def test_envelope_wrap(self):
        self.assertEqual(envelope_wrap([], []), [EMPTY])
        self.assertEqual(envelope_wrap(['head'], ['body']),
            ['head', EMPTY, 'body'])

    def test_parse_client_request(self):
        cases = [
            (['APS10', msgpack.packb([1, 2, 3]), 'method', 'params'],
                ('APS10', 1, 2, 3, 'method', ['params'])),
            (['APS09', msgpack.packb([2, 3, 1]), 'method'],
                ('APS09', 2, 3, 1, 'method', [])),
        ]
        for frames, expect in cases:
            request = parse_client_request(frames)
            self.assertEqual(request, expect)

    def test_parse_invalid_client_request(self):
        cases = [
            (['APS10', '1', 'x', 'y', 'method', 'params'],
                'invalid sequence, timestamp, expiry'),
            ([], 'empty request')
        ]
        for frames, msg in cases:
            try:
                request = parse_client_request(frames)
            except APSError:
                self.assertTrue(True)
            else:
                self.assertTrue(False, msg)

    def test_build_client_reply(self):
        frames = build_client_reply(1, 200, ['body', 'more'])
        sequence, timestamp, status = msgpack.unpackb(frames[1])
        self.assertEqual(frames[0], VERSION)
        self.assertEqual(sequence, 1)
        self.assertEqual(status, 200)
        self.assertEqual(frames[2:], ['body', 'more'])

if __name__ == '__main__':
    unittest.main()


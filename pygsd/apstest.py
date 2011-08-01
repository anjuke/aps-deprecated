import unittest
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
            (['APS10', struct.pack('>3L', 1,2,3), 'method', 'params'],
                ('APS10', 1, 2, 3, 'method', ['params'])),
            (['APS09', struct.pack('>3L', 2,3,1), 'method'],
                ('APS09', 2, 3, 1, 'method', [])),
        ]
        for frames, expect in cases:
            request = parse_client_request(frames)
            self.assertEqual(request, expect)

    def test_parse_invalid_client_request(self):
        cases = [
            (['APS10', struct.pack('>2L', 1,2), 'method', 'params'],
                'invalid sequence, timestamp, expiry'),
            (['APS10', struct.pack('>3L', 1,2,3)], 'no method'),
            ([], 'empty request')
        ]
        for frames, msg in cases:
            try:
                request = parse_client_request(frames)
            except APSError:
                self.assertTrue(True)
            else:
                self.assertTrue(False, msg)

if __name__ == '__main__':
    unittest.main()


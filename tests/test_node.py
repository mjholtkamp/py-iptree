import unittest

from iptree import IPNode


class TestIPNode(unittest.TestCase):
    def test_node_ipv4(self):
        node = IPNode('0.0.0.0/0')
        node.add(IPNode('127.0.0.1/32'))
        assert '127.0.0.1/32' in node
        assert '192.0.2.1/32' not in node

    def test_node_ipv6(self):
        node = IPNode('::/0')
        node.add(IPNode('::1/128'))
        assert '::1/128' in node
        assert '2001:db8::1/128' not in node

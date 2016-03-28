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

    def test_node_aggregate(self):
        root = IPNode('::/0')
        child = IPNode('2001:db8::/32')
        child.add(IPNode('2001:db8:cafe::1'))
        child.add(IPNode('2001:db8:cafe::2'))
        root.add(child)
        leafs = list(root.aggregate())

        assert root.children == {}
        assert child.parent is None
        assert child.children == {}
        assert len(leafs) == 2


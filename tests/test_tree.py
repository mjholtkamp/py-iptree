import unittest

import pytest

from iptree.iptree import BaseTree, IPTree, IPv4Tree, IPv6Tree


class TestIPTree(unittest.TestCase):
    def test_tree_base(self):
        tree = BaseTree(net_all='127.0.0.1/32', prefixes=(0, 32))
        assert tree.net_all == '127.0.0.1/32'
        assert tree.prefixes == (0, 32)

    def test_tree_add(self):
        tree = IPv6Tree(prefixes=(64, 128))

        node = tree.add('2001:db8:cafe::1')
        node = tree.add('2001:db8:cafe::1')
        assert node.network == '2001:db8:cafe::1/128'
        assert node.hit_count == 2

        node = tree.add('2001:db8::1')
        assert node.network == '2001:db8::1/128'
        assert node.hit_count == 1

        node = tree.add('2001:db8::2')
        assert node.network == '2001:db8::2/128'
        assert node.hit_count == 1

        parent = node.parent
        assert parent.network == '2001:db8::/64'
        assert parent.hit_count == 2

        root = parent.parent
        assert root.network == '::/0'
        assert root.hit_count == 4

    def test_tree_add_invalid(self):
        tree = IPv6Tree()
        with pytest.raises(ValueError):
            tree.add('2001::db8::1')

    def test_tree_ipv4(self):
        tree = IPv4Tree()
        assert tree.net_all == '0.0.0.0/0'

    def test_tree_ipv6(self):
        tree = IPv6Tree()
        assert tree.net_all == '::/0'

    def test_tree(self):
        tree = IPTree()
        assert tree is not None

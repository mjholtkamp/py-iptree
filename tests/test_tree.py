import pytest
import unittest

from iptree.iptree import IPTree, IPv4Tree, IPv6Tree, BaseTree


class TestIPTree(unittest.TestCase):
    def test_tree_base(self):
        tree = BaseTree(net_all='127.0.0.1/32', prefixes=(0, 32))
        assert tree.net_all == '127.0.0.1/32'
        assert tree.prefixes == (0, 32)

    def test_tree_add(self):
        tree = IPv6Tree()
        tree.add('2001:db8::1')

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

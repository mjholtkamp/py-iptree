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

    def test_aggregate_128(self):
        tree = IPv6Tree()
        tree.leaf_limit = 10

        for x in range(tree.leaf_limit):
            address = u'2001:db8::{}'.format(x)
            tree.add(address)

        added = list(tree.leafs_added())
        removed = list(tree.leafs_removed())
        assert len(added) == 10
        assert len(removed) == 0

        address = u'2001:db8::ffff'
        tree.add(address)

        added = list(tree.leafs_added())
        removed = list(tree.leafs_removed())
        assert len(added) == 1
        assert len(removed) == 10

        assert added[0].network == '2001:db8::/112'

    def test_aggregate_128_to_96(self):
        """Test if aggregates can aggregate from 128 to 96.
        If the limit for a 112 is lower than leaf_limit, while
        the above 96 exceeds the leaf_limit, multiple 128's
        should be aggregated into that 96.
        """
        tree = IPv6Tree()
        tree.leaf_limit = 10

        for x in range(5):
            address = u'2001:db8:1:2:3:4:1234:{}'.format(x)
            tree.add(address)

        for x in range(5):
            address = u'2001:db8:1:2:3:4:4321:{}'.format(x)
            tree.add(address)

        assert len(list(tree.leafs_added())) == 10
        assert len(list(tree.leafs_removed())) == 0

        node = tree.add('2001:db8:1:2:3:4:4321:6')

        assert node.network == '2001:db8:1:2:3:4::/96'
        assert len(list(tree.leafs_removed())) == 10
        assert len(list(tree.leafs_added())) == 1

    def test_append_aggregated(self):
        tree = IPv6Tree()
        tree.leaf_limit = 10

        for x in range(tree.leaf_limit):
            address = u'2001:db8::{}'.format(x)
            tree.add(address)

        address = u'2001:db8::1234'
        node = tree.add(address)
        assert node.network == '2001:db8::/112'

        node = tree.add(address)
        assert node.network == '2001:db8::/112'

import unittest

import pytest

from iptree.iptree import (
    BaseTree, IPTree, IPv4Tree, IPv6Tree, RemoveNonLeafException,
    RemoveRootException,
)

from . import debug

debug.init()


class TestIPTree(unittest.TestCase):
    def test_tree_base(self):
        tree = BaseTree(
            net_all='127.0.0.1/32',
            prefix_limits=((32, -1), (64, 2)),
        )
        assert tree.net_all == '127.0.0.1/32'
        assert tree.prefix_limits == ((32, -1), (64, 2))

    def test_tree_ipv4(self):
        tree = IPv4Tree()
        assert tree.net_all == '0.0.0.0/0'

    def test_tree_ipv6(self):
        tree = IPv6Tree()
        assert tree.net_all == '::/0'

    def test_tree(self):
        tree = IPTree()

        tree.add('127.0.0.1')
        tree.add('2001:db8::1')

        assert '127.0.0.1/32' in [x.network for x in tree.leafs()]
        assert '2001:db8::1/128' in [x.network for x in tree.leafs()]

        assert len(list(tree.leafs())) == 2


class TestAdd(unittest.TestCase):
    def test_tree_add(self):
        tree = IPTree()

        tree.add('2001:db8:cafe::1')
        hit = tree.add('2001:db8:cafe::1')
        assert hit.node.network == '2001:db8:cafe::1/128'
        assert hit.node.hit_count == 2

        hit = tree.add('2001:db8::1')
        assert hit.node.network == '2001:db8::1/128'
        assert hit.node.hit_count == 1

        hit = tree.add('2001:db8::2')
        assert hit.node.network == '2001:db8::2/128'
        assert hit.node.hit_count == 1

        parent = hit.node.parent
        assert parent.network == '2001:db8::/112'
        assert parent.hit_count == 2

        assert tree.ipv6.root.network == '::/0'
        assert tree.ipv6.root.hit_count == 4

    def test_tree_add_invalid(self):
        tree = IPTree()
        with pytest.raises(ValueError):
            tree.add('2001::db8::1')

        with pytest.raises(ValueError):
            tree.add('127.0.0.0.1')

    def test_append_aggregated(self):
        tree = IPTree()

        for x in range(3):
            address = u'2001:db8::{}'.format(x)
            tree.add(address)

        address = u'2001:db8::1234'
        hit = tree.add(address)
        assert hit.node.network == '2001:db8::/112'

        hit = tree.add(address)
        assert hit.node.network == '2001:db8::/112'


class TestRemove(unittest.TestCase):
    def test_tree_remove(self):
        tree = IPTree()

        hit = tree.add('2001:db8:cafe::1')
        assert hit.node.network == '2001:db8:cafe::1/128'
        hit = tree.add('2001:db8:cafe::2')
        assert hit.node.network == '2001:db8:cafe::2/128'

        leafs = [x.network for x in tree.leafs()]
        assert len(leafs) == 2

        tree.remove(hit.node)

        leafs = [x.network for x in tree.leafs()]
        assert len(leafs) == 1
        assert '2001:db8:cafe::1/128' in leafs

    def test_tree_remove_root(self):
        tree = IPTree()

        leafs = [x for x in tree.leafs()]
        assert len(leafs) == 0

        with pytest.raises(RemoveRootException):
            tree.remove(tree.ipv6.root)

        with pytest.raises(RemoveRootException):
            tree.remove(tree.ipv4.root)

    def test_tree_remove_non_leaf(self):
        """Test if non leafs can't be removed.
        Adding one IP address (/128), the following tree will be created:

        ::/0 (tree.root)
        `-2001:db8::/32 (first of tree.root.children)
          `-2001:db8:cafe::/48 (first of tree.root.children.children)
            `-2001:db8:cafe::/56 (... etc ...)
              `-2001:db8:cafe::/64
                `-2001:db8:cafe::/80
                  `-2001:db8:cafe::/96
                    `-2001:db8:cafe::/112
                      `-2001:db8:cafe::1/128

        """
        tree = IPTree()

        assert len([x for x in tree.leafs()]) == 0

        tree.add('2001:db8:cafe::1')

        assert len([x for x in tree.leafs()]) == 1

        with pytest.raises(RemoveNonLeafException):
            # 2001:db8::/32 is not a leaf
            tree.remove(tree.ipv6.root.children['2001:db8::/32'])

        assert len([x for x in tree.leafs()]) == 1

    def test_hit_count(self):
        tree = IPTree()

        for x in range(10):
            hit = tree.add('2001:db8:cafe::1')

        assert tree.ipv6.root.hit_count == 10

        tree.remove(hit.node)

        assert tree.ipv6.root.hit_count == 0

    def test_non_leafs_removed(self):
        tree = IPTree()

        hit = tree.add('2001:db8:cafe::1')

        tree.remove(hit.node)

        leafs = list(tree.ipv6.leafs())
        assert len(leafs) == 0

    def test_non_leafs_not_removed(self):
        tree = IPTree()

        tree.add('2001:db8:cafe::1')
        hit = tree.add('2001:db8:cafe::2')

        tree.remove(hit.node)

        leafs = list(tree.ipv6.leafs())
        assert len(leafs) == 1
        assert leafs[0].network == '2001:db8:cafe::1/128'


class TestInitial(unittest.TestCase):
    def test_initial_data(self):
        tree = IPTree(initial_user_data={'initial': 'd'})
        assert tree.ipv4.root.data['initial'] == 'd'
        assert tree.ipv6.root.data['initial'] == 'd'
        tree.ipv6.root.data['initial'] = 'data'
        assert tree.ipv6.root.data['initial'] == 'data'

        # make sure changing one, will not affect new nodes
        hit = tree.add('2001:db8::1')
        assert hit.node.data['initial'] == 'd'

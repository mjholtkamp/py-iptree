import unittest

import pytest

from iptree.iptree import (
    BaseTree, IPTree, IPv4Tree, IPv6Tree, RemoveRootException,
    RemoveNonLeafException,
)


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
        assert tree is not None


class TestAdd(unittest.TestCase):
    def test_tree_add(self):
        tree = IPv6Tree()

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
        assert parent.network == '2001:db8::/112'
        assert parent.hit_count == 2

        assert tree.root.network == '::/0'
        assert tree.root.hit_count == 4

    def test_tree_add_invalid(self):
        tree = IPv6Tree()
        with pytest.raises(ValueError):
            tree.add('2001::db8::1')

    def test_append_aggregated(self):
        tree = IPv6Tree()

        for x in range(3):
            address = u'2001:db8::{}'.format(x)
            tree.add(address)

        address = u'2001:db8::1234'
        node = tree.add(address)
        assert node.network == '2001:db8::/112'

        node = tree.add(address)
        assert node.network == '2001:db8::/112'


class TestRemove(unittest.TestCase):
    def test_tree_remove(self):
        tree = IPv6Tree()

        node = tree.add('2001:db8:cafe::1')
        assert node.network == '2001:db8:cafe::1/128'
        node = tree.add('2001:db8:cafe::2')
        assert node.network == '2001:db8:cafe::2/128'

        leafs = [x.network for x in tree.root]
        assert len(leafs) == 2

        tree.remove(node)

        leafs = [x.network for x in tree.root]
        assert len(leafs) == 1
        assert leafs[0] == '2001:db8:cafe::1/128'

    def test_tree_remove_root(self):
        tree = IPv6Tree()

        leafs = [x for x in tree.root]
        assert len(leafs) == 1

        with pytest.raises(RemoveRootException):
            tree.remove(leafs[0])

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
        tree = IPv6Tree()

        assert len([x for x in tree.root]) == 1

        tree.add('2001:db8:cafe::1')

        with pytest.raises(RemoveNonLeafException):
            # 2001:db8::/32 is not a leaf
            tree.remove(tree.root.children['2001:db8::/32'])

        assert len([x for x in tree.root]) == 1


class TestInitial(unittest.TestCase):
    def test_initial_data(self):
        tree = IPv6Tree(initial_user_data={'initial': 'd'})
        assert tree.root.data['initial'] == 'd'
        tree.root.data['initial'] = 'data'
        assert tree.root.data['initial'] == 'data'

        # make sure changing one, will not affect new nodes
        node = tree.add('2001:db8::1')
        assert node.data['initial'] == 'd'

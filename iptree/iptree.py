import logging
from collections import namedtuple

import ipaddress

from .ipnode import IPNode

logger = logging.getLogger('iptree')


class RemoveRootException(Exception):
    pass


class RemoveNonLeafException(Exception):
    pass


class NodeNotFound(Exception):
    pass


Hit = namedtuple('Hit', ['node', 'leafs_removed', 'leafs_added'])
UserMethods = namedtuple('UserMethods', ['initial', 'add', 'aggregate'])


def default_initial_user_data():
    return None


def default_add_user_data(node):
    pass


def default_aggregate_user_data(into, from_):
    """Default no-op aggregate_user_data
    :param into: the aggregated node
    :param from_: the list of nodes to be aggregated
    """
    pass


class BaseTree(object):
    net_all = None
    prefix_limits = None

    def __init__(self, net_all=None, prefix_limits=None, user_methods=None,
                 *args, **kwargs):
        """Tree of IPNode objects.
        The Tree uses prefix length to group ip address in (tree) nodes. To
        prevent out-of-memory errors, nodes are automatically aggregated once
        their number exceed the leaf_limit.

        A large group of single IP-addresses are aggregated into a network
        range and a large group of network ranges are aggregated into a bigger
        network range.

        The prefix_limits determine how the addresses/network ranges are
        grouped.  For example, prefix_limits is ((32, 100), (64, 10), (128,
        0)).  If there are more than 10 addresses (/128), they will be grouped
        into the next prefix of a larger network (/64). Now instead of 10+
        leafs (the 10+ addresses with the /128 prefix), there is only 1 leaf
        (the network range with the prefix /64). If there are 100+ /64 network
        ranges in the /32 network range, they will be aggregated into the /32
        range as well.

        In the above example, if there are 9 /128 addresses each under 12
        different /64 ranges, there will not be 10+ per /64 so they will not be
        grouped under the /64 range, but the 9 * 12 addresses = 108 addresses.
        This is larger than the leaf_limit for the /32, so they will be grouped
        under the /32.

        Whenever addresses/networks are aggregated, information about specific
        address/networks are lost, but the total hit_count is preserved.

        It is possible to store and aggregate custom data as well. Each node
        has a 'data' attribute, which can be anything. Use 'initial_user_data'
        to initialize each node with. The 'aggregate_user_data' method will
        be called each time nodes are aggregated. For usage, see the method
        default_aggregate_user_data.
        """
        super(BaseTree, self).__init__()
        if net_all:
            self.net_all = net_all
        if prefix_limits:
            self.prefix_limits = prefix_limits

        if user_methods is None:
            user_methods = {}

        aggregate = user_methods.get('aggregate', default_aggregate_user_data)
        self.user_methods = UserMethods(
            initial=user_methods.get('initial', default_initial_user_data),
            add=user_methods.get('add', default_add_user_data),
            aggregate=aggregate,
        )

        self.root = IPNode(self.net_all, data=self.user_methods.initial())

    def __getitem__(self, network):
        return self.find_node(network)

    def _networks(self, address):
        """Generate networks for each of the prefixes, specific to address"""
        for prefix, leaf_limit in self.prefix_limits:
            current_network = u'{}/{}'.format(address, prefix)
            yield str(ipaddress.ip_network(current_network, strict=False))

    def find_node(self, address):
        node = self.root
        if '/' in address:
            without_prefix, prefix = address.split('/')
        else:
            without_prefix = address
        for net in self._networks(without_prefix):
            if node.aggregated or node.network == address:
                break

            try:
                node = node[net]
            except KeyError:
                raise NodeNotFound

        return node

    def create_node(self, address):
        """Create node if it doesn't exist yet"""
        node = self.root
        new_leaf = False

        for net in self._networks(address):
            if node.aggregated:
                break

            try:
                node = node[net]
            except KeyError:
                new_leaf = True
                new_node = IPNode(net, data=self.user_methods.initial())
                node.add(new_node)
                node = new_node
                logger.info('added node: {}'.format(node.network))

        if new_leaf:
            self._update_leaf_count(node, 1)
            logger.info('node {} is a leaf'.format(node.network))

        return node

    def add(self, address):
        """Add a hit to an address.

        If there is no node in the tree yet that represents the address,
        a node is created. An aggregate node represents the address if
        the subnets are the same (with equal prefix lengths).

        The hit_count for the node is increased and the node is returned.

        The affected nodes are also checked for leaf limits, so it could
        be that nodes will be aggregated because of this call. In that case,
        leafs_added and leafs_removed are updated accordingly.

        :return: Hit(node, leafs_removed, leafs_added)
                 Where node is the IPNode where the hit was registered,
                 leafs_removed is a list of nodes that were removed since
                 before this call and leafs_added is a list of nodes that
                 were added since before this call.
        """
        new_leaf = False
        try:
            node = self.find_node(address)
        except NodeNotFound:
            node = self.create_node(address)
            new_leaf = True
        else:
            self.user_methods.add(node)

        self._update_hit_count(node, 1)

        leafs_added = []
        aggregated_node, leafs_removed = self._aggregate_if_needed(node)

        if new_leaf:
            if leafs_removed:
                # some leafs were removed, so also the one we just added.
                # remove it from the leafs_removed list
                leafs_removed.remove(node)
                logger.info(
                    'Unmarked as removed/not marking as added: {}'
                    .format(node.network)
                )

            leafs_added.append(aggregated_node)
            logger.info('Marking as added: {}'.format(aggregated_node.network))

        return Hit(aggregated_node, leafs_removed, leafs_added)

    def leafs(self):
        """
        Returns a generator that will yield all leafs (not intermediate) nodes
        """
        return (x for x in self.root)

    def remove(self, node):
        if node.children:
            raise RemoveNonLeafException('Not a leaf node')

        if not node.parent:
            raise RemoveRootException("Can't remove root node")

        del node.parent.children[node.network]
        self._update_hit_count(node.parent, -node.hit_count)
        self._update_leaf_count(node.parent, -1)

        if not node.parent.children and node.parent.parent:
            self.remove(node.parent)

    def _update_hit_count(self, node, increment):
        while node:
            node.hit_count += increment
            node = node.parent

    def _update_leaf_count(self, node, increment):
        while node.parent:
            node = node.parent
            logger.debug(
                'node: {} old leaf_count: {} new leaf count: {}'.format(
                    node.network, node.leaf_count, node.leaf_count + increment
                )
            )
            node.leaf_count += increment

    def _aggregate_if_needed(self, node):
        """Check if node or any of its parents need to be aggregated.
        We only check from this node and up since this node and its
        parents are the only ones that changed.
        :return: tuple of (node, leafs_removed) where node is current
                 node or aggregated node and leafs_removed is a list
                 if nodes that are removed because of aggregation.
        """
        total_leafs_removed = []
        parent = node.parent

        node_prefix = int(node.network.split('/')[1])
        prefix_idx = -1
        for idx, (prefix, _) in enumerate(self.prefix_limits):
            if prefix == node_prefix:
                prefix_idx = idx - 1
                break

        while prefix_idx >= 0:
            prefix, leaf_limit = self.prefix_limits[prefix_idx]
            if leaf_limit > 0 and parent.leaf_count > leaf_limit:
                logger.info(
                    'prefix limit exceeded: {} leaf_count: {} leaf_limit: {}'
                    .format(parent.network, parent.leaf_count, leaf_limit)
                )
                leafs_removed = []
                for leaf in parent.aggregate():
                    leafs_removed.append(leaf)
                    logger.info('node removed: {}'.format(leaf.network))

                self.user_methods.aggregate(parent, leafs_removed)
                total_leafs_removed.extend(leafs_removed)

                # Update leaf count. We removed N leafs,
                # and we added one (parent is converted to leaf because
                # it lost all its children).
                self._update_leaf_count(parent, 1 - len(leafs_removed))
                node = parent
            parent = parent.parent
            prefix_idx -= 1
        return node, total_leafs_removed


class IPv4Tree(BaseTree):
    net_all = '0.0.0.0/0'
    prefix_limits = (
        (16, 0),
        (24, 16),
        (32, 0),
    )


class IPv6Tree(BaseTree):
    net_all = '::/0'
    prefix_limits = (
        (32, 0),
        (48, 50),
        (56, 10),
        (64, 5),
        (80, 4),
        (96, 3),
        (112, 2),
        (128, 0),
    )


class IPTree(object):
    def __init__(self, *args, **kwargs):
        super(IPTree, self).__init__()
        self.ipv4 = IPv4Tree(*args, **kwargs)
        self.ipv6 = IPv6Tree(*args, **kwargs)

    def __getitem__(self, network):
        return self._tree_by_network(network)[network]

    def __delitem__(self, network):
        self.remove(self._tree_by_network(network)[network])

    def _tree_by_network(self, network):
        if ':' in network:
            return self.ipv6
        return self.ipv4

    def leafs(self):
        for leaf in self.ipv6.leafs():
            yield leaf

        for leaf in self.ipv4.leafs():
            yield leaf

    def add(self, network):
        return self._tree_by_network(network).add(network)

    def remove(self, node):
        self._tree_by_network(node.network).remove(node)

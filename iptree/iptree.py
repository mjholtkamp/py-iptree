import ipaddress
import logging

from .ipnode import IPNode


logger = logging.getLogger('iptree')


class BaseTree(object):
    net_all = None
    prefix_limits = None

    def __init__(self, net_all=None, prefix_limits=None, *args, **kwargs):
        """Tree of IPNode objects.
        The Tree uses prefix length to group ip address in (tree) nodes. To
        prevent out-of-memory errors, nodes are automatically aggregated once
        their number exceed the leaf_limit.

        A large group of single IP-addresses are aggregated into a network
        range and a large group of network ranges are aggregated into a bigger
        network range.

        The prefix_limits determine how the addresses/network ranges are grouped.
        For example, prefix_limits is ((32, 100), (64, 10), (128, 0)).
        If there are more than 10 addresses (/128), they will be grouped into
        the next prefix of a larger network (/64). Now instead of 10+ leafs
        (the 10+ addresses with the /128 prefix), there is only 1 leaf (the
        network range with the prefix /64). If there are 100+ /64 network ranges
        in the /32 network range, they will be aggregated into the /32 range
        as well.

        In the above example, if there are 9 /128 addresses each under 12 different
        /64 ranges, there will not be 10+ per /64 so they will not be grouped under
        the /64 range, but the 9 * 12 addresses = 108 addresses. This is larger
        than the leaf_limit for the /32, so they will be grouped under the /32.

        Whenever addresses/networks are aggregated, information about specific
        address/networks are lost, but the total hit_count is preserved.
        """
        super(BaseTree, self).__init__()
        if net_all:
            self.net_all = net_all
        if prefix_limits:
            self.prefix_limits = prefix_limits
        self.root = IPNode(self.net_all)
        self._leafs_removed = []
        self._leafs_added = []

    def add(self, address):
        """Add address to tree.
        The address is added to the tree, unless an aggregated node already
        exists of a network that matches the address. In both cases, the
        hit_count for the node is increased and the node is returned.

        :return: Node that address was added too. Can be aggregated node.
        """
        prefix = self.prefix_limits[0]
        node = self.root
        new_leaf = None

        # find node to which we can add the address, create if it doesn't
        # exist. If node is aggregated, do not create one below it.
        for prefix, leaf_limit in self.prefix_limits:
            if node.aggregated:
                break

            current_network = u'{}/{}'.format(address, prefix)
            net = str(ipaddress.ip_network(current_network, strict=False))
            try:
                node = node[net]
            except KeyError:
                new_node = IPNode(net)
                node.add(new_node)
                node = new_node
                new_leaf = node
                logger.info('added node: {}'.format(new_leaf.network))

        self._hit(node)
        if new_leaf:
            self._update_leaf_count(node, 1)
            self._leafs_added.append(new_leaf)

        aggregated_node = self._check_aggregation(node)

        if aggregated_node != node:
            self._leafs_added.append(aggregated_node)
            if new_leaf:
                # leaf was added, but immediately caused aggregation, so it
                # got removed as well. Now it's in both list, which is
                # confusing. Remove from both lists to fix this.
                for leafs in (self._leafs_added, self._leafs_removed):
                    logger.info('delete added node: {}'.format(new_leaf.network))
                    idx = leafs.index(new_leaf)
                    del leafs[idx]

        return aggregated_node

    def leafs_added(self):
        while self._leafs_added:
            yield self._leafs_added.pop()

    def leafs_removed(self):
        while self._leafs_removed:
            yield self._leafs_removed.pop()

    def _hit(self, node):
        while node:
            node.hit_count += 1
            node = node.parent

    def _update_leaf_count(self, node, increment):
        while node.parent:
            node = node.parent
            logger.debug('node: {} old leaf_count: {} new leaf count: {}'.format(
                node.network, node.leaf_count, node.leaf_count + increment
            ))
            node.leaf_count += increment

    def _check_aggregation(self, node):
        """Check if node or any of its parents need to be aggregated.
        We only check from this node and up since this node and its
        parents are the only ones that changed.
        :return: current node or aggregated node
        """
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
                logger.info('prefix limit exceeded: {} leaf_count: {} leaf_limit: {}'.format(
                    prefix, parent.leaf_count, leaf_limit
                ))
                removed_leafs = 0
                for leaf in parent.aggregate():
                    self._leafs_removed.append(leaf)
                    logger.info('node removed: {}'.format(leaf.network))
                    removed_leafs += 1
                # Update leaf count. We removed 'removed_leafs' leafs,
                # and we added one (parent is converted to leaf because
                # it lost all its children).
                self._update_leaf_count(parent, 1 - removed_leafs)
                node = parent
            parent = parent.parent
            prefix_idx -= 1
        return node


class IPv4Tree(BaseTree):
    net_all = '0.0.0.0/0'
    prefix_limits = (
        (16, -1),
        (24, 16),
        (32, 0),
    )


class IPv6Tree(BaseTree):
    net_all = '::/0'
    prefix_limits = (
        (32, -1),
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
        super(IPTree, self).__init__(*args, **kwargs)
        self.ipv4 = IPv4Tree()
        self.ipv6 = IPv6Tree()

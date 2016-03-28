import ipaddress

from .ipnode import IPNode


class BaseTree(object):
    net_all = None
    prefixes = None
    leaf_limit = 1000

    def __init__(self, net_all=None, prefixes=None, *args, **kwargs):
        """Tree of IPNode objects.
        The Tree uses prefix length to group ip address in (tree) nodes. To
        prevent out-of-memory errors, nodes are automatically aggregated once
        their number exceed the leaf_limit.

        A large group of single IP-addresses are aggregated into a network
        range and a large group of network ranges are aggregated into a bigger
        network range.

        The prefixes determine how the addresses/network ranges are grouped.
        For example, suppose leaf_limit is 10 and prefixes is (32, 64, 128).
        If there are more than 10 addresses (/128), they will be grouped into
        the next prefix of a larger network (/64). Now instead of 10+ leafs
        (the 10+ addresses with the /128 prefix), there is only 1 leaf (the
        network range with the prefix /64). If there are 10+ /64 network ranges
        in the /32 network range, they will be aggregated into the /32 range
        as well.

        In the above example, if there are 5 /128 addresses under one /64 range
        and 6 /128 addresses under another /64 range, while both are under the
        same /32 range, they will be aggregated immediately into the /32. This
        might seem scary, but remember that the leaf count will be 1 if they
        are aggregated so it will not aggregated further up. The default list
        of prefixes has very short steps between each prefix, so aggregation
        is not that fast.

        Whenever addresses/networks are aggregated, information about specific
        address/networks are lost, but the total hit_count is preserved.
        """
        super(BaseTree, self).__init__(*args, **kwargs)
        if net_all:
            self.net_all = net_all
        if prefixes:
            self.prefixes = prefixes
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
        prefix = self.prefixes[0]
        node = self.root
        new_leaf = False

        # find node to which we can add the address, create if it doesn't
        # exist. If node is aggregated, do not create one below it.
        for prefix in self.prefixes:
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
                new_leaf = True

        self._hit(node)
        if new_leaf:
            self._update_leaf_count(node, 1)

        aggregated_node = self._check_aggregation(node)

        if new_leaf or aggregated_node != node:
            self._leafs_added.append(aggregated_node)

        return aggregated_node

    def leafs_added(self):
        return self._leafs_added.pop()

    def leafs_removed(self):
        return self._leafs_removed.pop()

    def _hit(self, node):
        while node:
            node.hit_count += 1
            node = node.parent

    def _update_leaf_count(self, node, increment):
        while node.parent:
            node = node.parent
            node.leaf_count += increment

    def _check_aggregation(self, node):
        """Check if node or any of its parents need to be aggregated.
        We only check from this node and up since this node and its
        parents are the only ones that changed.
        :return: current node or aggregated node
        """
        parent = node.parent

        while parent:
            if parent.leaf_count > self.leaf_limit:
                removed_leafs = 0
                for leaf in parent.aggregate():
                    self._leafs_removed.append(leaf)
                    removed_leafs += 1
                # Update leaf count. We removed 'removed_leafs' leafs,
                # and we added one (parent is converted to leaf because
                # it lost all its children).
                self._update_leaf_count(1 - removed_leafs)
                node = parent
            parent = parent.parent
        return node


class IPv4Tree(BaseTree):
    net_all = '0.0.0.0/0'
    prefixes = (16, 24, 32)


class IPv6Tree(BaseTree):
    net_all = '::/0'
    prefixes = (32, 48, 56, 64, 80, 96, 112, 128)


class IPTree(object):
    def __init__(self, *args, **kwargs):
        super(IPTree, self).__init__(*args, **kwargs)
        self.ipv4 = IPv4Tree()
        self.ipv6 = IPv6Tree()

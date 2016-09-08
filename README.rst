===========================================
IP tree: efficiently counting IP addresses.
===========================================

``iptree`` is the package to count hits to IP addresses, both IPv4 as well as
IPv6. A use case for this is to keep track of IP addresses to throttle without
overloading your memory or overloading your firewall with millions of rules.

For efficiency, IP addresses or subnets are automatically aggregated into
larger subnets based on configurable thresholds.

.. examples-begin

Basic usage
===========

Let's start with some basic example. We create an IPtree object that will work
for both IPv4 as well as IPv6 addresses. If you only want one of them, you can
always use them directly, e.g.: ``iptree.IPv6Tree()`` for the IPv6 version.

.. code:: python

    >>> import iptree
    >>> tree = iptree.IPTree()
    >>> list(tree.leafs())
    []

Let's add some IP addresses to the tree:

.. code:: python

    >>> hit = tree.add('192.0.2.1')
    >>> hit
    Hit(node=<IPNode: 192.0.2.1/32>, leafs_removed=[], leafs_added=[<IPNode: 192.0.2.1/32>])
    >>> hit.node.hit_count
    1
    >>> hit = tree.add('192.0.2.1')
    >>> hit
    Hit(node=<IPNode: 192.0.2.1/32>, leafs_removed=[], leafs_added=[])
    >>> hit.node.hit_count
    2
    >>> list(tree.leafs())
    [<IPNode: 192.0.2.1/32>]

Aggregation
-----------

Now let's see what happens when multiple IP addresses are added:

.. code:: python

    >>> tree.add('2001:db8::1')
    Hit(node=<IPNode: 2001:db8::1/128>, leafs_removed=[], leafs_added=[<IPNode: 2001:db8::1/128>])
    >>> tree.add('2001:db8::2')
    Hit(node=<IPNode: 2001:db8::2/128>, leafs_removed=[], leafs_added=[<IPNode: 2001:db8::2/128>])
    >>> hit = tree.add('2001:db8::3')
    >>> hit
    Hit(node=<IPNode: 2001:db8::/112>, leafs_removed=[<IPNode: 2001:db8::1/128>, <IPNode: 2001:db8::2/128>], leafs_added=[<IPNode: 2001:db8::/112>])
    >>> hit.node.hit_count
    3
    >>> list(tree.leafs())
    [<IPNode: 2001:db8::/112>, <IPNode: 192.0.2.1/32>]
    >>> iptree.IPv6Tree.prefix_limits  # The default limits
    ((32, 0), (48, 50), (56, 10), (64, 5), (80, 4), (96, 3), (112, 2), (128, 0))


As we can see from the default ``prefix_limits``, there are only 2 unique IP
addresses allowed per /112 subnet, so the third address triggered an
aggregation of multiple /128 subnets into one /112 subnet, while the
hit\_count is preserved.

Finding
-------

Finding nodes by address is pretty straightforward. An ``IPTree`` will return
an IPNode (possibly aggregated) if it finds a node by address, otherwise an
exception is raised.

.. code:: python

    >>> tree['2001:db8::42']
    <IPNode: 2001:db8::/112>
    >>> tree['2001:db8::/112']
    <IPNode: 2001:db8::/112>
    >>> tree['2001:db8:cafe::42']
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "iptree/iptree.py", line 293, in __getitem__
        return self._tree_by_network(network)[network]
      File "iptree/iptree.py", line 88, in __getitem__
        return self.find_node(network)
      File "iptree/iptree.py", line 111, in find_node
        raise NodeNotFound
    iptree.iptree.NodeNotFound

Removing
--------

Removing can be done on address or network with prefix, provided that the
address or network/prefix exists in the tree:

.. code:: python

    >>> del tree['2001:db8::/112']
    >>> del tree['192.0.2.1']
    >>> list(tree.leafs())
    []

Advanced usage
==============

It is possible to add custom data on nodes and have them automatically
mutated in three situations:

1. When a node is created (initial)
2. When a hit is added to a node (add)
3. When multiple nodes are aggregated into one (aggregate)

The following example shows how this works. The example is a bit silly since
hits are already counted by iptree, but the aggregating function selects the
max of the counters of all nodes that are aggregated instead.

.. code:: python

    >>> def initial():
    ...     return {'counter': 1}
    ...
    >>> def add(node):
    ...     node.data['counter'] += 1
    ...
    >>> def aggregate(into, from_):
    ...     into.data['counter'] = max([node.data['counter'] for node in from_])
    ...
    >>> methods = dict(
    ...     initial=initial,
    ...     add=add,
    ...     aggregate=aggregate,
    ... )
    >>> tree = iptree.IPTree(user_data_methods=methods)
    >>> hit = tree.add('2001:db8::1')
    >>> hit.node.data
    {'counter': 1}  # node is created, so 'initial()' is called
    >>> hit = tree.add('2001:db8::1')
    >>> hit.node.data
    {'counter': 2}  # same node, so 'add()' is called
    >>> hit = tree.add('2001:db8::2')
    >>> hit.node.aggregated
    False
    >>> hit.node.data
    {'counter': 1}
    >>> hit = tree.add('2001:db8::3')
    >>> hit.node.aggregated
    True
    >>> hit.node.data
    {'counter': 2}  # because the prefix limit was passed, 'aggregated()' is called



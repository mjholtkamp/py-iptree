class IPNode(object):
    def __init__(self, network, parent=None, data=None, *args, **kwargs):
        super(IPNode, self).__init__(*args, **kwargs)
        self.leaf_count = 0
        self.hit_count = 0
        self.aggregated = False
        self.network = network
        self.data = data or {}  # user data
        self.parent = parent or None
        self.children = {}

    def __contains__(self, network):
        return network in self.children

    def __getitem__(self, network):
        return self.children[network]

    def __iter__(self):
        if self.children:
            for child in self.children.values():
                for grandchild in iter(child):
                    yield grandchild

            # done, unlink the children
            self.children = {}
        else:
            yield self

    def add(self, node):
        node.parent = self
        self.children[node.network] = node

    def aggregate(self):
        """Aggregate all descendants into this node.
        yield all leafs that were removed because of the aggregation
        """
        self.aggregated = True
        for child in self._unlink(ourselves=False):
            yield child

    def _unlink(self, ourselves):
        if ourselves:
            # unlink ourselves
            self.parent = None

        if self.children:
            for child in self.children.values():
                for grandchild in child._unlink(ourselves=True):
                    yield grandchild

            # done, unlink the children
            self.children = {}
        else:
            yield self

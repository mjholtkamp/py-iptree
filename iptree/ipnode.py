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

    def add(self, node):
        node.parent = self
        self.children[node.network] = node

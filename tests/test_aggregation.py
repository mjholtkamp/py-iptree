import random

from iptree.iptree import IPv6Tree

from . import debug

debug.init()


class RandomIPv6(object):
    def __init__(self, prefix, amount, base_address=None, index=None):
        """Generate random IPv6 addresses.
        :param prefix: network prefix to generate address in. should be
                       multiple of 16.
        :param amount: amount of addresses to generate
        :param base_address: override default base_address
        """
        self.amount = amount
        if base_address is None:
            base_address = '2001:db8'

        parts = prefix // 16
        base_address_parts = len(list(filter(None, base_address.split(':'))))
        fillers = parts - base_address_parts
        index_part = ''
        if index is not None:
            fillers -= 1
            index_part = ':{:x}'.format(index)

        address = base_address + ':0' * fillers + index_part

        self.parts = 8 - parts
        self.ip_fmt = address + ':{:x}' * self.parts

    def __iter__(self):
        for x in range(self.amount):
            octets = [
                int(random.uniform(0, 0xffff))
                for x in range(self.parts)
            ]
            yield self.ip_fmt.format(*octets)


class TestRandomIPv6(object):
    def test_ip_32(self):
        for ip in RandomIPv6(32, 10):
            assert ip.startswith('2001:db8:')
            assert not ip.startswith('2001:db8:0:')

    def test_ip_64(self):
        for ip in RandomIPv6(64, 10):
            assert ip.startswith('2001:db8:0:0:')
            assert not ip.startswith('2001:db8:0:0:0:')

    def test_ip_112(self):
        for ip in RandomIPv6(112, 10):
            assert ip.startswith('2001:db8:0:0:0:0:0:')

    def test_index_64(self):
        for ip in RandomIPv6(64, 10, index=0x4f3c):
            assert ip.startswith('2001:db8:0:4f3c:')

    def test_index_112(self):
        for ip in RandomIPv6(112, 10, index=0x4f3c):
            assert ip.startswith('2001:db8:0:0:0:0:4f3c:')


class TestIPTree(object):
    def setup_method(self, method):
        self.leafs_removed = []
        self.leafs_added = []

    def generate_addresses(self, prefix, amount, unique):
        """Generate random IPv6 address generators.
        :param prefix: the prefix in which to generate random addresses.
        :param amount: the amount of random addresses to generate.
        :param unique: the amount of unique sequential prefixes.

        For example, <prefix> = 64, <unique> = 13, then 13 generators will
        be returned, with prefixes '2001:db8:0:1::/64' up to and including
        '2001:db8:0:13::/64'. Each of these generators will yield <amount>
        addresses.
        """
        return [
            RandomIPv6(prefix, amount, index=idx)
            for idx in range(1, unique + 1)
        ]

    def add_ip(self, tree, ip):
        hit = tree.add(ip)
        self.leafs_removed.extend([x.network for x in hit.leafs_removed])
        self.leafs_added.extend([x.network for x in hit.leafs_added])
        return hit.node

    def test_add_from_one_128(self):
        tree = IPv6Tree()
        for prefix in self.generate_addresses(128, 100, 1):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert children[0] == '2001:db8::1/128'

        assert tree.root.hit_count == 100
        assert tree.root.leaf_count == 1
        assert len(self.leafs_removed) == 0
        assert len(self.leafs_added) == 1

    def test_add_from_two_128(self):
        tree = IPv6Tree()
        for prefix in self.generate_addresses(128, 100, 2):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert '2001:db8::1/128' in children
        assert '2001:db8::2/128' in children

        assert tree.root.hit_count == 200
        assert tree.root.leaf_count == 2
        assert len(self.leafs_removed) == 0
        assert len(self.leafs_added) == 2

    def test_add_from_three_128(self):
        tree = IPv6Tree()
        for prefix in self.generate_addresses(128, 100, 3):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert children[0] == '2001:db8::/112'
        assert '2001:db8::/112' in self.leafs_added

        assert tree.root.hit_count == 300
        assert tree.root.leaf_count == 1
        assert len(self.leafs_removed) == 2
        assert len(self.leafs_added) == 3

    def test_add_from_one_112(self):
        tree = IPv6Tree()
        for prefix in self.generate_addresses(112, 100, 1):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert children[0] == '2001:db8::1:0/112'
        assert '2001:db8::1:0/112' in self.leafs_added

        assert tree.root.hit_count == 100
        assert tree.root.leaf_count == 1
        assert len(self.leafs_removed) == 2
        assert len(self.leafs_added) == 3

    def test_add_from_two_simultaneous_112(self):
        """If two /112's are added in turn, the threshold for
        the /96 (3) is reached sooner than the individual thresholds
        for the two /112's (2); 2 + 2 > 3.
        So we expect then to them aggregated together in one /96
        instead of two /112's.
        """
        tree = IPv6Tree()
        for ips in zip(*self.generate_addresses(112, 100, 2)):
            for ip in ips:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert '2001:db8::/96' in children
        assert '2001:db8::/96' in self.leafs_added

        assert tree.root.hit_count == 200
        assert tree.root.leaf_count == 1
        # only 3 removed and not 4, because when we are about
        # to add the fourth, the treshold for the /96 is exceeded
        # and aggregation is triggered.
        assert len(self.leafs_removed) == 3
        assert len(self.leafs_added) == 4

    def test_add_from_two_sequential_112(self):
        tree = IPv6Tree()
        for prefix in self.generate_addresses(112, 100, 2):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert '2001:db8::1:0/112' in children
        assert '2001:db8::2:0/112' in children
        assert '2001:db8::1:0/112' in self.leafs_added
        assert '2001:db8::2:0/112' in self.leafs_added

        assert tree.root.hit_count == 200
        assert tree.root.leaf_count == 2
        assert len(self.leafs_removed) == 4
        assert len(self.leafs_added) == 6

    def test_add_from_three_112(self):
        tree = IPv6Tree()
        for prefix in self.generate_addresses(112, 100, 3):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert children[0] == '2001:db8::/96'
        assert '2001:db8::/96' in self.leafs_added

        assert tree.root.hit_count == 300
        assert tree.root.leaf_count == 1
        assert len(self.leafs_removed) == 7
        assert len(self.leafs_added) == 8

    def test_add_from_one_64(self):
        tree = IPv6Tree()
        for prefix in self.generate_addresses(64, 100, 1):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert children[0] == '2001:db8:0:1::/64'
        assert '2001:db8:0:1::/64' in self.leafs_added

        assert tree.root.hit_count == 100
        assert tree.root.leaf_count == 1
        assert len(self.leafs_removed) == 5
        assert len(self.leafs_added) == 6

    def test_add_from_ten_simultaneous_64(self):
        """If two /64's are added in turn, the threshold for
        the /56 (6) is reached sooner than the individual thresholds
        for the two /64's (5); 5 + 5 > 6.
        So we expect then to them aggregated together in one /56
        instead of two /64's.
        """
        tree = IPv6Tree()
        for ips in zip(*self.generate_addresses(64, 100, 10)):
            for ip in ips:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert '2001:db8::/56' in children
        assert '2001:db8::/56' in self.leafs_added

        assert tree.root.hit_count == 1000
        assert tree.root.leaf_count == 1
        assert len(self.leafs_removed) == 10
        assert len(self.leafs_added) == 11

    def test_add_from_six_sequential_64(self):
        tree = IPv6Tree()
        prefixes = 6
        for prefix in self.generate_addresses(64, 100, prefixes):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        for idx in range(1, prefixes + 1):
            assert '2001:db8:0:{}::/64'.format(idx) in children
            assert '2001:db8:0:{}::/64'.format(idx) in self.leafs_added

        assert tree.root.hit_count == 600
        assert tree.root.leaf_count == 6
        assert len(self.leafs_removed) == 30
        assert len(self.leafs_added) == 36

    def test_add_from_seven_64(self):
        """After 7 sequential /64 groups of ip addresses, aggregate to /56.
        The limit for /64 is 5, the limit for /56 is 10.
        This means that after 6 /64's have been aggregated, the seventh
        will trigger aggregation to a /56 before aggregation from the last
        5 /128's to one /64 is triggered.
        Explanation:
         - The first six groups will each be aggrated into one /64.
         - There are now 6 /64's, so the leaf count is 6.
         - A new group of addresses from a new /64 will be added.
         - When the new group has added 5 IP addresses, those addresses
           will not be aggregated into one /64 (5 is equal to the limit
           for a /64, so the next one would trigger aggregation, but not
           this one).
         - The total leaf count is now 6 + 5 = 11. Six from the previous
           /64's and 5 from the new /64.
         - Because 11 > 10 (the limit for a /56), it will be aggregated into
           the parent /56 range.
        """
        tree = IPv6Tree()
        for prefix in self.generate_addresses(64, 100, 7):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert '2001:db8::/56' in children
        assert '2001:db8::/56' in self.leafs_added

        assert tree.root.hit_count == 700
        assert tree.root.leaf_count == 1
        # each aggregated /64 removes 5 leafs, 6 are aggreated
        # each aggregated /56 removes 10 leafs, 1 is aggregated
        # 6 * 5 + 1 * 10 = 40
        assert len(self.leafs_removed) == 40
        assert len(self.leafs_added) == 41

    def test_add_one_48(self):
        tree = IPv6Tree()
        for prefix in self.generate_addresses(48, 100, 1):
            for ip in prefix:
                self.add_ip(tree, ip)

        children = [x.network for x in tree.root]
        assert '2001:db8:1::/48' in children
        assert '2001:db8:1::/48' in self.leafs_added

        assert tree.root.hit_count == 100
        assert tree.root.leaf_count == 1
        assert len(self.leafs_removed) == 50
        assert len(self.leafs_added) == 51

    def test_user_data(self):
        def aggregate_user_data(into, from_):
            """Our custome aggregate function to test the calling
            of the aggregate function. It simply sums up all counters."""
            into.data['counter'] += sum([x.data['counter'] for x in from_])

        kwargs = dict(
            aggregate_user_data=aggregate_user_data,
            initial_user_data={'counter': 0},
        )
        tree = IPv6Tree(**kwargs)
        for prefix in self.generate_addresses(112, 100, 1):
            for ip in prefix:
                node = self.add_ip(tree, ip)
                node.data['counter'] += 2

        children = [x for x in tree.root]
        assert children[0].data['counter'] == 200

import unittest

from iptree import IPNode


class TestIPTree(unittest.TestCase):
    def test_node(self):
        node = IPNode()
        assert node is not None

import collections


class EtcdResult(object):
    _node_props = {
        'key': None,
        'value': None,
        'expiration': None,
        'ttl': None,
        'modifiedIndex': None,
        'createdIndex': None,
        'newKey': False,
        'dir': False,
    }

    def __init__(self, action=None, node=None, prevNode=None, **kwdargs):
        """
        Creates an EtcdResult object.

        Args:
            action (str): The action that resulted in key creation

            node (dict): The dictionary containing all node information.

        """
        self.action = action
        for (key, default) in self._node_props.items():
            if key in node:
                setattr(self, key, node[key])
            else:
                setattr(self, key, default)

        self._children = []
        if self.dir and 'nodes' in node:
            # We keep the data in raw format, converting them only when needed
            self._children = node['nodes']

        if prevNode:
            self._prev_node = EtcdResult(None, node=prevNode)
            # See issue 38: when returning a write() op etcd has a bogus result.
            if self._prev_node.dir and not self.dir:
                self.dir = True

    def parse_headers(self, response):
        headers = response.getheaders()
        self.etcd_index = int(headers.get('x-etcd-index', 1))
        self.raft_index = int(headers.get('x-raft-index', 1))

    def get_subtree(self, leaves_only=False):
        """
        Get all the subtree resulting from a recursive=true call to etcd.

        Args:
            leaves_only (bool): if true, only value nodes are returned


        """
        if not self._children:
            # if the current result is a leaf, return itself
            yield self
            return
        for n in self._children:
            node = EtcdResult(None, n)
            if not leaves_only:
                # Return also dirs, not just value nodes
                yield node
            for child in node.get_subtree(leaves_only=leaves_only):
                yield child
        return

    @property
    def leaves(self):
        return self.get_subtree(leaves_only=True)

    @property
    def children(self):
        """ Deprecated, use EtcdResult.leaves instead """
        return self.leaves

    def __eq__(self, other):
        if not (type(self) is type(other)):
            return False
        for k in self._node_props.keys():
            try:
                a = getattr(self, k)
                b = getattr(other, k)
                if a != b:
                    return False
            except:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

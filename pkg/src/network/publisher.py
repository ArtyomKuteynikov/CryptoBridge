import socket

from pkg.src.network.node import Node


class Publisher:
    """Publish data to outer node"""

    def __init__(self, host: str, port: int, bind_port: int | None = None):
        self.host = host
        self.port = port
        self.connect = Node(host, port)
        self.socket = self.connect.connect(bind_port)
        self.stream = self.socket.makefile('rb', None)

    def publishBlock(self, block):
        """Publish block to other node"""
        self.connect.send(block)

    def publishTx(self, tx):
        """Publish transaction to other node"""
        self.connect.send(tx)

    def sendRequest(self, headers):
        """Send request to get some data"""
        self.connect.send(headers)

    def close(self):
        """Close connection to node"""
        self.connect.closeConnection()
        self.stream.close()

    def restart(self):
        self.socket = self.connect.restart()
        self.stream = self.socket.makefile('rb', None)

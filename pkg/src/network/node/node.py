import socket
import struct

from pkg.src.network.network import NetworkEnvelope


class Node:
    """Connection handler object"""

    def __init__(self, host: str, port: int):
        self.host: str = host
        self.port: int = int(port)
        self.ADDR = ("0.0.0.0", self.port)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))

    def startServer(self):
        """ Start the Server and bind it"""
        self.server.bind(self.ADDR)
        self.server.listen()

    def acceptConnection(self):
        """Accept outer connections to our node"""
        self.conn, self.addr = self.server.accept()
        self.stream = self.conn.makefile('rb', None)
        return self.conn, self.addr

    def connect(self, port: int | None = None):
        """Connect to outer node"""
        if port:
            self.server.bind(("0.0.0.0", port))
        self.server.connect((self.host, self.port))
        return self.server

    def closeConnection(self):
        """Close connection to outer node"""
        self.server.close()

    def send(self, message):
        """Send message to outer node"""
        envelope = NetworkEnvelope(message.command, message.serialize())
        self.server.sendall(envelope.serialize())

    def restart(self):
        self.server.close()
        self.server.connect((self.host, self.port))
        return self.server

    def read(self):
        """Read incoming message"""
        envelope = NetworkEnvelope.parse(self.stream)
        return envelope

    def timeout(self):
        ...

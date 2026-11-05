"""Tests locaux du transport, sans serveur distant ni interface graphique."""
import socket
import threading
import unittest
from unittest.mock import patch

from client import Client
from clientthread import ClientListener


class ClientTests(unittest.TestCase):
    def connect_client(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        self.addCleanup(listener.close)
        client = Client('Alice', '127.0.0.1', listener.getsockname()[1])
        peer, _ = listener.accept()
        peer.settimeout(2)
        self.addCleanup(peer.close)
        self.addCleanup(client.tidy_up)
        self.assertEqual(peer.recv(1024), b'USERNAME Alice\n')
        return client, peer

    def test_fragmented_unicode_and_multiple_messages(self):
        client, peer = self.connect_client()
        messages = []
        done = threading.Event()
        client.on_message = messages.append
        client.on_disconnect = done.set
        client.listen()
        peer.sendall(b'caf\xc3')
        peer.sendall(b'\xa9\nsuite\n')
        peer.shutdown(socket.SHUT_WR)
        self.assertTrue(done.wait(2))
        self.assertEqual(messages, ['caf\u00e9', 'suite'])
        self.assertFalse(client.listening)

    def test_send_and_repeated_cleanup(self):
        client, peer = self.connect_client()
        client.send('Bonjour')
        self.assertEqual(peer.recv(1024), b'Bonjour\n')
        client.tidy_up()
        client.tidy_up()
        with self.assertRaises(ConnectionError):
            client.send('Bonjour')

    def test_validation(self):
        for username, host, port in [('', 'localhost', 42), ('Alice', '', 42),
                                     ('Alice', 'localhost', 0), ('A\nB', 'localhost', 42)]:
            with self.assertRaises(ValueError):
                Client(username, host, port)

    def test_server_parses_combined_and_fragmented_commands(self):
        server_peer, peer = socket.socketpair()
        self.addCleanup(peer.close)
        class Server:
            def __init__(self):
                self.messages = []
            def echo(self, message):
                self.messages.append(message)
            def remove_socket(self, sock):
                pass
        server = Server()
        worker = ClientListener(server, server_peer, ('local', 0))
        worker.start()
        peer.sendall(b'USERNAME Ali')
        peer.sendall(b'ce\nBonjour\nQUIT\n')
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(server.messages, ['Alice has joined.\n', 'Alice: Bonjour\n', 'Alice has quit\n'])


if __name__ == '__main__':
    unittest.main()

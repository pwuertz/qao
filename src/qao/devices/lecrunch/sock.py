#!/usr/bin/env python

import struct
import socket
import os

headerformat = '>BBBBL'

errors = { 1  : 'unrecognized command/query header',
           2  : 'illegal header path',
           3  : 'illegal number',
           4  : 'illegal number suffix',
           5  : 'unrecognized keyword',
           6  : 'string error',
           7  : 'GET embedded in another message',
           10 : 'arbitrary data block expected',
           11 : 'non-digit character in byte count field of arbitrary data '
                'block',
           12 : 'EOI detected during definite length data block transfer',
           13 : 'extra bytes detected during definite length data block '
                'transfer' }

class Socket(object):
    def __init__(self, host, port=1861, timeout=5.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.settimeout(timeout)

    def clear(self, timeout=0.5):
        """
        Clear any bytes in the oscilloscope's output queue by receiving
        packets until the connection blocks for more than `timeout` seconds.
        """
        t = self.sock.gettimeout()
        self.sock.settimeout(timeout)
        try:
            while True:
                self.sock.recv(4096)
        except socket.timeout:
            pass
        self.sock.settimeout(t)

    def send(self, msg):
        """Format and send the string `msg`."""
        if not msg.endswith('\n'):
            msg += '\n'
        header = struct.pack(headerformat, 129, 1, 1, 0, len(msg))
        self.sock.sendall(header + msg)

    def check_last_command(self):
        """
        Check that the last command sent was received okay; if not, raise
        an exception with details about the error.
        """
        self.send('cmr?')
        err = int(self.recv().split(' ')[-1].rstrip('\n'))

        if err in errors:
            self.sock.close()
            raise Exception(errors[err])

    def recv(self):
        """Return a message from the scope."""

        reply = ''
        while True:
            header = ''

            while len(header) < 8:
                header += self.sock.recv(8 - len(header))

            operation, headerver, seqnum, spare, totalbytes = \
                struct.unpack(headerformat, header)

            buffer = ''

            while len(buffer) < totalbytes:
                buffer += self.sock.recv(totalbytes - len(buffer))

            reply += buffer

            if operation % 2:
                break

        return reply

    def __del__(self):
        self.sock.close()

if __name__ == '__main__':
    import sys
    import setup

    sock = Socket(setup.scope_ip)
    sock.clear()

    for msg in sys.argv[1:]:
        sock.send(msg)

        if '?' in msg:
            print repr(sock.recv())

        sock.check_last_command()

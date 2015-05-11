import base64
import struct
import numpy as np

try:
    import sha

    def sha1(text):
        return sha.new(text)
except ImportError:
    # sha is deprecated in python3.
    # use haslib instead
    import hashlib

    def sha1(text):
        return hashlib.sha1(text.encode())


GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

OPCODE_CONTINUATION = 0x0
OPCODE_ASCII        = 0x1
OPCODE_BINARY       = 0x2
OPCODE_CLOSE        = 0x8
OPCODE_PING         = 0x9
OPCODE_PONG         = 0xA


def xor(data, mask):
    mask = struct.unpack(">BBBB", mask)
    return ''.join([chr(ord(data[i]) ^ mask[i%4]) for i in range(len(data))])


def np_xor(data, mask):
    if isinstance(mask, tuple):
        mask = ''.join([chr(b) for b in mask])
    m = len(data)
    if m % 4:
        padded_data = data + ("\x00" * (4 - (m % 4)))
    else:
        padded_data = data
    mask_int = np.frombuffer(mask, dtype="<u4")
    view = np.frombuffer(padded_data, dtype="<u4")

    return str(np.bitwise_xor(view, mask_int).view(dtype='u1')[:m].data)


class HTTPHeader(object):
    def __init__(self, requestLine='', attr={}):
        self.attr = attr
        self.requestLine = requestLine
        self.parser = self.readHeader()
        next(self.parser)

    def createHeader(self):
        lines = [self.requestLine]
        lines.extend(["%s: %s" % (key, value) for key, value in self.attr.items()])
        lines.append("\r\n")
        return "\r\n".join(lines)

    def readHeader(self):
        self.requestLine = (yield 1)

        def strip(text, stripe="\n\r\t "):
            return text.strip(stripe)

        while True:
            line = (yield 1)
            if strip(line) == '':
                break
            try:
                key, value = line.split(':', 1)
                self.attr[strip(key)] = strip(value)
            except Exception as e:
                print("could not interpret header line: %s: %s" % (line, e))
    
    def buildServerReply(self):
        header = 'HTTP/1.1 101 Switching Protocols'
        answerAttributes = {'Upgrade': 'websocket',
                            'Connection': 'Upgrade'}
        
        #calculate 'Sec-WebSocket-Accept'
        assert 'Sec-WebSocket-Key' in self.attr
        shaedKey = sha1("%s%s" % (self.attr['Sec-WebSocket-Key'], GUID))
        replyKey = base64.b64encode(shaedKey.digest())
        answerAttributes.update({'Sec-WebSocket-Accept': replyKey})
        
        hdr = HTTPHeader(header, answerAttributes)
        return hdr
        

class DefaultHTTPClientHeader(HTTPHeader):
    def __init__(self):
        HTTPHeader.__init__(self)
        self.requestLine = "GET /chat HTTP/1.1"
        self.attr = { 'Host': 'server.example.com',\
                        'Upgrade': 'websocket',\
                        'Connection': 'Upgrade',\
                        'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',\
                        'Origin': 'http://example.com',\
                        'Sec-WebSocket-Protocol': 'chat, superchat',\
                        'Sec-WebSocket-Version': '13'}


class Frame(object):
    def __init__(self, opCode=None, data=b'', mask=None, fin=0, rsv1=0, rsv2=0, rsv3=0):
        self.fin     = fin
        self.rsv1    = rsv1
        self.rsv2    = rsv2
        self.rsv3    = rsv3
        self.opCode  = opCode
        self.maskBit = None
        self.length  = len(data)
        self.mask    = mask
        self.data    = data
        
        self.payload = None
        self.parser = self._parse()
        
    def build(self):
        byteList = [0, 0]
        byteList[0]  = self.fin <<  7    #fin-bit
        byteList[0] += self.rsv1 << 6    #rsv-bit
        byteList[0] += self.rsv2 << 5    #rsv-bit
        byteList[0] += self.rsv3 << 4    #rsv-bit
        byteList[0] += self.opCode       #op-code
        
        byteList[0] = chr(byteList[0])
        
        # check whether to set the mask bit
        if self.mask is not None:
            byteList[1] = 1 << 7
        else:
            byteList[1] = 0
        
        # check what length to write
        if self.length > 2**16:
            byteList[1] += 127
            byteList.extend(struct.pack(">Q",self.length))
        elif self.length >= 2**7:
            byteList[1] += 126
            byteList.extend(struct.pack(">H",self.length))
        else:
            byteList[1] += self.length

        if self.mask is not None:
            byteList.extend(list(self.mask))
            self.payload = np_xor(self.data, self.mask)
        else:
            self.payload = self.data
        byteList[1] = chr(byteList[1]) 
        
        """
        print "="*20
        print "-> FIN: %s"%self.fin
        print "-> RSV1: %i"%self.rsv1
        print "-> RSV2: %i"%self.rsv2
        print "-> RSV3: %i"%self.rsv3
        print "-> OP: %i"%self.opCode
        print "-> MASK: ", self.mask
        print "-> LEN: %i"%self.length
        """

        return ''.join(byteList) + self.payload

    def _parse(self):
        recvData = (yield 2)

        self.fin            = (ord(recvData[0]) & 0b10000000) >> 7 
        self.rsv1           = (ord(recvData[0]) & 0b01000000) >> 6
        self.rsv2           = (ord(recvData[0]) & 0b00100000) >> 5
        self.rsv3           = (ord(recvData[0]) & 0b00010000) >> 4
        self.opCode         = (ord(recvData[0]) & 0b00001111)
        self.maskBit        = (ord(recvData[1]) & 0b10000000) >> 7
        self.length         = (ord(recvData[1]) & 0b01111111)

        if self.length == 126:
            self.length = struct.unpack(">H", (yield 2))[0]

        elif self.length == 127:
            self.length = struct.unpack(">Q", (yield 8))[0]

        if self.maskBit:
            self.mask = struct.unpack(">BBBB", (yield 4))

        self.payload = (yield self.length)

        if self.maskBit:
            self.data = np_xor(self.payload, self.mask)
        else:
            self.data = self.payload

        """
        print "="*20
        print "<- FIN: %s"%self.fin
        print "<- RSV1: %i"%self.rsv1
        print "<- RSV2: %i"%self.rsv2
        print "<- RSV3: %i"%self.rsv3
        print "<- OP: %i"%self.opCode
        print "<- MASK: ", self.mask
        print "<- LEN: %i"%self.length
        """

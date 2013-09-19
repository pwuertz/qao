import socket,sha,base64
import sys,select,struct

GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

OPCODE_CONTINUATION = 0x0
OPCODE_ASCII        = 0x1
OPCODE_BINARY       = 0x2
OPCODE_CLOSE        = 0x8
OPCODE_PING         = 0x9
OPCODE_PONG         = 0xA

def xor(data,mask):
    return ''.join([chr(ord(data[i]) ^ ord(mask[i%4]))for i in xrange(len(data))])

class HTTPHeader(object):
    def __init__(self,requestLine='', attr={}):
        self.attr = attr
        self.requestLine = requestLine
        self.parser = self.readHeader()
        next(self.parser)

        
    def createHeader(self):
        header = "%s\r\n"%self.requestLine
        for key, value in self.attr.items():
            header = "%s%s: %s\r\n"%(header,key,value)
        header = "%s\r\n"%header
        print header
        return header
    
    def readHeader(self):
        self.requestLine = (yield 1)
        while True:
            line = (yield 1)
            if line.strip("\n\r\t ") == '': break
            try:
                key, value = line.split(':',1)
                self.attr.update({key.strip("\n\r\t "):value.strip("\n\r\t ")})
            except Exception, e:
                print "could not interpret header line: %s: %s"%(line,e)
    
    def buildServerReply(self):
        header = 'HTTP/1.1 101 Switching Protocols\r\n'
        answerAttributes = {'Upgrade': 'websocket', 'Connection': 'Upgrade'}
        
        #calculate 'Sec-WebSocket-Accept'
        assert 'Sec-WebSocket-Key' in self.header
        shaedKey = sha.new("%s%s"%(self.header['Sec-WebSocket-Key'],GUID))
        replyKey = base64.b64encode(shaedKey.digest())
        answerAttributes.update({'Sec-WebSocket-Accept':replyKey})
        
        hdr = HTTPHeader(header,answerAttributes)
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
                        'Sec-WebSocket-Version': 13}

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
        byteList = [0,0]
        byteList[0]  = self.fin <<  7    #fin-bit
        byteList[0] += self.rsv1 << 6    #rsv-bit
        byteList[0] += self.rsv2 << 5    #rsv-bit
        byteList[0] += self.rsv3 << 4    #rsv-bit
        byteList[0] += self.opCode       #op-code
        
        byteList[0] = chr(byteList[0])
        
        #check whether to set the mask bit
        if self.mask != None:
            byteList[1] = 1 << 7
        else:
            byteList[1] = 0
        
        #check what length to write
        if self.length > 2**16:
            byteList[1] += 127
            byteList.extend(struct.pack(">Q",self.length))
        elif self.length > 2**7:
            byteList[1] += 126
            byteList.extend(struct.pack(">H",self.length))
        else:
            byteList[1] += self.length
        if self.mask != None:
            byteList.extend(list(self.mask))
            self.payload = xor(self.data,self.mask)
        else:
            self.payload = self.data
        byteList[1] = chr(byteList[1])   
        return ''.join(byteList)+self.payload
        
    
    def _parse(self):
        data = {}
        recvData = (yield 2)
        
        self.fin            = (ord(recvData[0]) & 0b10000000) >> 7 == 1
        self.rsv1           = (ord(recvData[0]) & 0b01000000) >> 6
        self.rsv1           = (ord(recvData[0]) & 0b00100000) >> 5
        self.rsv1           = (ord(recvData[0]) & 0b00010000) >> 4
        self.opCode         = (ord(recvData[0]) & 0b00001111)
        self.maskBit        = (ord(recvData[1]) & 0b10000000) >> 7 == 1
        self.length         = (ord(recvData[1]) & 0b01111111)
    
        if self.length == 126:
            self.length = struct.unpack(">H",(yield 2))[0]
            
        elif self.length == 127:
            self.length = struct.unpack(">Q",(yield 8))[0]
        
        if self.maskBit:
            self.mask = struct.unpack(">BBBB",(yield 4))
    
        self.payload = (yield self.length)
    
        if self.maskBit:
            self.data = xor(self.payload,self.mask)
        else:
            self.data = self.payload
        
        """
        print "FIN: %s"%(data['finBit'])
        print "RSV: %i"%(data['rsvBits'])
        print "OP: %i"%(data['opCode'])
        print "MASK: %s"%(data['maskPresent'])
        print "LEN: %i"%(data['dataLen'])
        print "MASK: %x %x %x %x"%(data['maskArray'][0],data['maskArray'][1],data['maskArray'][2],data['maskArray'][3])
        """

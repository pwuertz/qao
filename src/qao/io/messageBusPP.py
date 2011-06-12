import socket,struct,cPickle,select,sys

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9090
DEFAULT_TIMEOUT = 5000

TYPE_SUBSCRIBE   = "subscribe"
TYPE_UNSUBSCRIBE = "unsubscribe"
TYPE_PUBLISH     = "publish"
TYPE_SET         = "set"
TYPE_ACK         = "ack"
TYPE_NAK         = "nak"

class tcpPkgClient():
    def __init__(self):
        self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def connectToServer(self, host = DEFAULT_HOST, port = DEFAULT_PORT, timeout = DEFAULT_TIMEOUT):
        self.clientSock.connect((host, port))
        self.clientSock.setblocking(0)
        self.clientSock.settimeout(timeout)

    def disconnectFromServer(self):
        self.clientSock.close()
        
    def _sendPacket(self,byteArray):
        bytesWritten = self.clientSock.send(struct.pack("!I", len(byteArray))+byteArray)
        if bytesWritten != 4+len(byteArray): raise Exception("Not all Bytes written!")
    
    def _sendPacketPickled(self,data):
        self._sendPacket(cPickle.dumps(data, -1))
        
    def _recvPacket(self):
        #TODO: if only one packet arrives which is longer or shorter then announced, this routine
        #will fail forever and ever!
        
        #first read announced number of bytes
        pkgLenData = self.clientSock.recv(4)
        pkgLen = struct.unpack("!I", pkgLenData)
        
        data=""
        #read data
        while len(data) < pkgLen[0]:
            currentData = self.clientSock.recv(min(4096,pkgLen[0]-len(data)))
            data = ''.join([data,currentData])
            
        if len(data) != pkgLen[0]: raise Exception("Number of Bytes wrong during read")
        #print data
        return data
        
class MessageBusClient(tcpPkgClient):
    
    def __init__(self):
        self.subscriptionCallbacks = {}
        tcpPkgClient.__init__(self)
        
    def subscribe(self, topic, callback = None):
        topic = str(topic)
        self._sendPacketPickled([TYPE_SUBSCRIBE, topic])
        if callback: self.subscriptionCallbacks[topic] = callback

    def unsubscribe(self, topic):
        topic = str(topic)
        self._sendPacket([TYPE_UNSUBSCRIBE, topic])
        if topic in self.subscriptionCallbacks: self.subscriptionCallbacks.remove(topic)
        
    def publishEvent(self, topic, data):
        topic = str(topic)
        self._sendPacketPickled([TYPE_PUBLISH, topic, data])
        
    def waitForEventPublished(self, timeout = DEFAULT_TIMEOUT):
        pass
    
    def handleEvent(self):
        topic, data = self._recvPacketPickled()
        if topic in self.subscriptionCallbacks: self.subscriptionCallbacks[topic](topic,data)
        
    def _recvPacketPickled(self):
        try:
            dataRaw = self._recvPacket()
            data = cPickle.loads(dataRaw)
            if len(data) < 2:
                raise Exception("packet with insufficient number of args")
            
            if data[0] == TYPE_PUBLISH:
                if len(data) < 3: raise Exception("packet with insufficient number of args")
                return data[1], data[2]
            
            if data[0] == TYPE_NAK:
                raise Exception("server reported: %s" % data[1])
            
        except Exception, e:
            errorstr = type(e).__name__ + ", " + str(e)
            sys.stderr.write(errorstr + "\n")           
        
    
if __name__ == "__main__":
    
    def printdummy(topic,data):
        print "%s: %s"%(topic,data)
    
    client = MessageBusClient()
    client.connectToServer()
    client.subscribe("testing",callback=printdummy)
    client.publishEvent("testing",["foo","bar"])
    
    #To integrate with Qt use QSocketNotifier which emits the signal activated whenever
    #the socket has something to read. Connect this to the handleEvent()-Function
    
    print "starting main loop"
    while True:
        readySocks = select.select([client.clientSock],[],[])
        if readySocks[0] == [client.clientSock]:
            client.handleEvent()
    client.disconnectFromServer()

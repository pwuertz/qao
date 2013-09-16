import socket,struct,cPickle,select,sys
import time #for profiling
import json

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9090
DEFAULT_TIMEOUT = 500

TYPE_SUBSCRIBE   = "subscribe"
TYPE_UNSUBSCRIBE = "unsubscribe"
TYPE_PUBLISH     = "publish"
TYPE_SET         = "set"
TYPE_ACK         = "ack"
TYPE_NAK         = "nak"

class TcpPkgClient():
    """
    Low level class that handles the sending and receiving of data organised in packets via tcp.
    The content of a packet is not interpreted, this should be done by derived classe.
    """
    def __init__(self):
        self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connectToServer(self, host = DEFAULT_HOST, port = DEFAULT_PORT, timeout = DEFAULT_TIMEOUT):
        self.clientSock.connect((host, port))
        self.clientSock.setblocking(0)
        self.clientSock.settimeout(timeout)

    def disconnectFromServer(self):
        self.clientSock.close()

    def _sendPacket(self,byteArray):
        lenByteArray=len(byteArray)
        totalBytesWritten=0
        while totalBytesWritten < lenByteArray:
            bytesWritten = self.clientSock.send((struct.pack("!I", lenByteArray)+byteArray)[totalBytesWritten:])
            totalBytesWritten += bytesWritten
        if totalBytesWritten != 4+len(byteArray): raise Exception("Not all Bytes written!")
        

    def _recvPacket(self):
        #NOTE: if only one packet arrives which is longer or shorter then announced, this routine
        #will fail forever and ever! Maybe one should add some magic bits at the end of every packet
        
        #first read announced number of bytes
        pkgLenData = self.clientSock.recv(4)
        pkgLen = struct.unpack("!I", pkgLenData)

        dataArray=[]
        lenRecv = 0
        
        #read data
        while lenRecv < pkgLen[0]:
            currentData = self.clientSock.recv(min(4096,pkgLen[0]-lenRecv))
            dataArray.append(currentData)
            lenRecv += len(currentData)
        data = ''.join(dataArray)
        if len(data) != pkgLen[0]: raise Exception("Number of Bytes wrong during read")
        return data

class MessageBusClient(TcpPkgClient):

    def __init__(self):
        self.subscriptionCallbacks = {}
        TcpPkgClient.__init__(self)

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

    def _sendPacketPickled(self,data):
        self._sendPacket(json.dumps(data, separators=(',', ':'), sort_keys=True))
        
    def _recvPacketPickled(self):
        try:
            dataRaw = self._recvPacket()
            #picklestarttime = time.time()
            try:
                data = json.loads(dataRaw)
            except Exception, e:
                print("no valid json data received: falling back to old pickle decoding")
                data = cPickle.loads(dataRaw)
            #print "Depickle took %.2f s"%(time.time()-picklestarttime)
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


class QMessageBusClient(MessageBusClient):
    def __init__(self):
        try:
            from PyQt4 import QtCore
        except ImportError:
            from PySide import QtCore
        
        MessageBusClient.__init__(self)
        self.s_notify = QtCore.QSocketNotifier(self.clientSock.fileno(),QtCore.QSocketNotifier.Read)
        self.s_notify.activated.connect(self.handleEvent)

if __name__ == "__main__":
    import time
    
    def printdummy(topic,data):
        print "%s: %s (Data:%.2f)"%(topic,data[0],float(data[1]))

    #initiate client connection
    client = MessageBusClient()
    client.connectToServer()
    
    #subscribe and publish first event
    client.subscribe("testing",callback=printdummy)
    client.publishEvent("testing",["foo","31.0"])

    print "starting main loop"
    
    while True:
        readySocks = select.select([client.clientSock],[],[])
        if readySocks[0] == [client.clientSock]:
            client.handleEvent()
    client.disconnectFromServer()


import sys, cPickle
try:
    from PyQt4 import QtCore, QtNetwork
    from PyQt4.QtCore import pyqtSignal as qtSignal
except ImportError:
    from PySide import QtCore, QtNetwork
    from PySide.QtCore import Signal as qtSignal
    

DEFAULT_PORT = 9090
DEFAULT_TIMEOUT = 5000

TYPE_SUBSCRIBE   = "subscribe"
TYPE_UNSUBSCRIBE = "unsubscribe"
TYPE_PUBLISH     = "publish"
TYPE_SET         = "set"
TYPE_ACK         = "ack"
TYPE_NAK         = "nak"

def simplePublish(topic, data, hostname, port = DEFAULT_PORT):
    c = MessageBusClient()
    c.connectToServer(hostname, port)
    c.publishEvent(topic, data)
    c.waitForEventPublished()

class MessageBusClient(QtCore.QObject):
    
    receivedEvent = qtSignal(str, object)
    disconnected = qtSignal()
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.connection = QtNetwork.QTcpSocket()
        self.connection.disconnected.connect(self.disconnected)
        self.connection.readyRead.connect(self._handleReadyRead)
        self.packetSize = 0
        self.packetBuffer = ""
        
        self.subscriptionCallbacks = {}
        
    def connectToServer(self, host, port = DEFAULT_PORT, timeout = DEFAULT_TIMEOUT):
        self.connection.connectToHost(host, port)
        if not self.connection.waitForConnected(timeout): raise Exception("no connection to event server")
    
    def disconnectFromServer(self):
        self.connection.disconnectFromHost()
        
    def subscribe(self, topic, callback = None):
        topic = str(topic)
        self._sendPacket([TYPE_SUBSCRIBE, topic])
        if callback: self.subscriptionCallbacks[topic] = callback

    def unsubscribe(self, topic):
        topic = str(topic)
        self._sendPacket([TYPE_UNSUBSCRIBE, topic])
        if topic in self.subscriptionCallbacks: self.subscriptionCallbacks.remove(topic)
        
    def publishEvent(self, topic, data):
        topic = str(topic)
        self._sendPacket([TYPE_PUBLISH, topic, data])
        
    def waitForEventPublished(self, timeout = DEFAULT_TIMEOUT):
        while self.connection.bytesToWrite() > 0:
            self.connection.waitForBytesWritten(DEFAULT_TIMEOUT)
    
    def handleEvent(self, topic, data):
        self.receivedEvent.emit(topic, data)
        if topic in self.subscriptionCallbacks: self.subscriptionCallbacks[topic](data)         
        
    def _sendPacket(self, data):
        stream = QtCore.QDataStream(self.connection)
        dataSer = cPickle.dumps(data, -1)
        stream.writeUInt32(len(dataSer))
        nWritten = stream.writeRawData(dataSer)

    def _handleReadyRead(self):
        while self.connection.bytesAvailable() > 0:
            # if the last packet was complete, read the size of the next
            if self.packetSize == 0:
                if self.connection.bytesAvailable() < 4: return
                stream = QtCore.QDataStream(self.connection)
                self.packetSize   = stream.readUInt32()
            
            # if the packet is not complete, wait for more data
            if self.connection.bytesAvailable() < self.packetSize: return
            packet = str(self.connection.read(self.packetSize))
            self._handleNewPacket(packet)
            self.packetSize = 0

    def _handleNewPacket(self, dataRaw):
        try:
            data = cPickle.loads(dataRaw)
            if len(data) < 2:
                raise Exception("packet with insufficient number of args")
            
            if data[0] == TYPE_PUBLISH:
                if len(data) < 3: raise Exception("packet with insufficient number of args")
                self.handleEvent(data[1], data[2])
                return
            
            if data[0] == TYPE_NAK:
                raise Exception("server reported: %s" % data[1])
            
        except Exception, e:
            errorstr = type(e).__name__ + ", " + str(e)
            sys.stderr.write(errorstr + "\n")

class ServerClientConnection(QtCore.QObject):
    
    eventPublished = qtSignal(str, object)
    disconnected = qtSignal()
    
    def __init__(self, connection):
        QtCore.QObject.__init__(self)
        self.connection = connection
        self.connection.disconnected.connect(self.disconnected)
        self.connection.readyRead.connect(self._handleReadyRead)
        self.packetSize = 0
        self.subscriptions = set([])
    
    def forwardEvent(self, topic, data):
        self._sendPacket([TYPE_PUBLISH, topic, data])
        
    def _sendPacket(self, data):
        stream = QtCore.QDataStream(self.connection)
        dataSer = cPickle.dumps(data, -1)
        stream.writeUInt32(len(dataSer))
        nWritten = stream.writeRawData(dataSer)
    
    def _handleReadyRead(self):
        while self.connection.bytesAvailable() > 0:
            # if the last packet was complete, read the size of the next
            if self.packetSize == 0:
                if self.connection.bytesAvailable() < 4: return
                stream = QtCore.QDataStream(self.connection)
                self.packetSize   = stream.readUInt32()
            
            # if the packet is not complete, wait for more data
            if self.connection.bytesAvailable() < self.packetSize: return
            packet = str(self.connection.read(self.packetSize))
            self._handleNewPacket(packet)
            self.packetSize = 0

    def _handleNewPacket(self, dataRaw):
        try:
            data = cPickle.loads(dataRaw)
            
            if len(data) < 2:
                raise Exception("packet with insufficient number of args")
            
            # add the second arg to the list of subscriptions
            if data[0] == TYPE_SUBSCRIBE:
                self.subscriptions.add(data[1])
                return
            
            # remove the second arg to the list of subscriptions
            if data[0] == TYPE_UNSUBSCRIBE:
                self.subscriptions.remove(data[1])
                return
            
            # publish packet to the server
            if data[0] == TYPE_PUBLISH:
                if len(data) < 3:
                    raise Exception("packet with insufficient number of args")
                self.eventPublished.emit(data[1], data[2])
                return
            
            # packet not recognized
            raise Exception("unrecognized instruction in packet")
            
        except Exception, e:
            errorstr = type(e).__name__ + ", " + str(e)
            # notify the client about the error
            self._sendPacket([TYPE_NAK, errorstr])
            # print the error server side
            print "error reading packet:", errorstr

class MessageBusServer(QtCore.QObject):
    
    clientConnected = qtSignal(object)
    clientDisconnected = qtSignal(object)
    eventPublished = qtSignal(str, object)
    
    def __init__(self, port = DEFAULT_PORT):
        QtCore.QObject.__init__(self)
        # setup server
        self.server = QtNetwork.QTcpServer()
        self.server.listen(port=port)
        self.server.newConnection.connect(self._handleNewConnection)
        # list of client connections
        self.clients = []
            
    def _handleNewConnection(self):
        client = ServerClientConnection(self.server.nextPendingConnection())
        client.eventPublished.connect(self._handlePublish)
        client.disconnected.connect(self._handleDisconnect)
        self.clients.append(client)
        self.clientConnected.emit(client)
    
    def _handlePublish(self, topic, data):
        topic = str(topic)
        # search clients for subscribers
        for client in self.clients:
            if topic in client.subscriptions:
                client.forwardEvent(topic, data)
        self.eventPublished.emit(topic, data)
    
    def _handleDisconnect(self):
        client = self.sender()
        self.clientDisconnected.emit(client)
        self.clients.remove(client)

if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    print "Starting MessageServer at port %d" % DEFAULT_PORT
    
    class ConsoleServer(MessageBusServer):
        def __init__(self):
            MessageBusServer.__init__(self)
            self.eventPublished.connect(self.printEventPublished)
            
        def printEventPublished(self, topic, data):
            print "new event: %s" % str(topic)
    
    app = QtCore.QCoreApplication([])
    serv = ConsoleServer()
    app.exec_()

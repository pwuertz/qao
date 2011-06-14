from qao.io import messageBusPP as messageBus
import socket,cPickle

try:
    from PyQt4 import QtCore, QtNetwork
    from PyQt4.QtCore import pyqtSignal as qtSignal
except ImportError:
    from PySide import QtCore, QtNetwork
    from PySide.QtCore import Signal as qtSignal

class ServerClientConnection(messageBus.TcpPkgClient):
    
    def __init__(self, server, connSockDesc):
        self.clientSock = socket.fromfd(connSockDesc,socket.AF_INET, socket.SOCK_STREAM)
        self.server = server
        self.subscriptions = set([])
        self.s_notify = QtCore.QSocketNotifier(connSockDesc,QtCore.QSocketNotifier.Read)
        self.s_notify.activated.connect(self._recvPacketPickled)
    
    def forwardEvent(self, topic, data):
        self._sendPacketPickled([messageBus.TYPE_PUBLISH, topic, data])
    
    def _sendPacketPickled(self,data):
        self._sendPacket(cPickle.dumps(data, -1))
    
    def _recvPacketPickled(self):
        try:
            dataRaw = self._recvPacket()
            data = cPickle.loads(dataRaw)
            
            if len(data) < 2:
                raise Exception("packet with insufficient number of args")
            
            # add the second arg to the list of subscriptions
            if data[0] == messageBus.TYPE_SUBSCRIBE:
                self.subscriptions.add(data[1])
                return
            
            # remove the second arg to the list of subscriptions
            if data[0] == messageBus.TYPE_UNSUBSCRIBE:
                self.subscriptions.remove(data[1])
                return
            
            # publish packet to the server
            if data[0] == messageBus.TYPE_PUBLISH:
                if len(data) < 3:
                    raise Exception("packet with insufficient number of args")
                self.server._handlePublish(data[1], data[2])
                return
            
            # packet not recognized
            raise Exception("unrecognized instruction in packet")
            
        except Exception, e:
            errorstr = type(e).__name__ + ", " + str(e)
            # notify the client about the error
            self._sendPacketPickled([messageBus.TYPE_NAK, errorstr])
            # print the error server side
            print "error reading packet:", errorstr

class MessageBusServer(QtCore.QObject):
    
    clientConnected = qtSignal(object)
    clientDisconnected = qtSignal(object)
    eventPublished = qtSignal(str, object)
    
    def __init__(self, port = messageBus.DEFAULT_PORT):
                
        QtCore.QObject.__init__(self)
        # setup server
        self.server = QtNetwork.QTcpServer()
        self.server.listen(port=port)
        self.server.newConnection.connect(self._handleNewConnection)
        # list of client connections
        self.clients = []
            
    def _handleNewConnection(self):
        client = ServerClientConnection(self,self.server.nextPendingConnection().socketDescriptor())
        client.disconnected.connect(self._handleDisconnect)
        self.clients.append(client)
        self.clientConnected.emit(client)
        assert (not self.server.hasPendingConnections()) # TODO: do we have to check for multiple connections?
    
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
    
    print "Starting MessageServer at port %d" % messageBus.DEFAULT_PORT
    
    class ConsoleServer(MessageBusServer):
        def __init__(self):
            MessageBusServer.__init__(self)
            self.eventPublished.connect(self.printEventPublished)
            
        def printEventPublished(self, topic, data):
            print "new event: %s" % str(topic)
    
    app = QtCore.QCoreApplication([])
    serv = ConsoleServer()
    app.exec_()

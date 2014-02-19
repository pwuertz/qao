from qao.io import messageBusPP as messageBus
import socket,cPickle,select
import json


class ServerClientConnection(messageBus.TcpPkgClient):
    
    def __init__(self, server, connSock):
        self.clientSock = connSock
        self.server = server
        self.subscriptions = set([])
        
    def forwardEvent(self, topic, data):
        self._sendPacketPickled([messageBus.TYPE_PUBLISH, topic, data])
    
    def fileno(self):
        #needed for select
        return self.clientSock.fileno()
    
    def _sendPacketPickled(self,data):
        self._sendPacket(json.dumps(data, separators=(',', ':'), sort_keys=True))
    
    def _recvPacketPickled(self):
        try:
            dataRaw = self._recvPacket()
            print dataRaw
            try:
                data = json.loads(dataRaw)
            except Exception, e:
                print("no valid json data received: falling back to old pickle decoding")
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

class MessageBusServer():
    
    def __init__(self, port = messageBus.DEFAULT_PORT):
        
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSock.bind(('', port))
        self.serverSock.listen(1)
        # list of client connections
        self.clients = []
            
    def _handleNewConnection(self):
        conn, addr = self.serverSock.accept()
        print 'Connected by', addr
        client = ServerClientConnection(self,conn)
        self.clients.append(client)
        #assert (not self.server.hasPendingConnections()) # TODO: do we have to check for multiple connections?
    
    def _handlePublish(self, topic, data):
        topic = str(topic)
        # search clients for subscribers
        for client in self.clients:
            if topic in client.subscriptions:
                client.forwardEvent(topic, data)
     
    def fileno(self):
        #needed for select
        return self.serverSock.fileno()
    
    def disconnectClient(self,client):
        self.clients.remove(client)
        del(client)
        
    def _handleDisconnect(self):
        client = self.sender()
        self.disconnectClient(client)

if __name__ == "__main__":
    import time
    
    def printdummy(topic,data):
        print "%s: %s (Dauer:%.2f)"%(topic,data[0],time.time()-float(data[1]))

    #initiate client connection
    server = MessageBusServer()
    
    print "starting main loop"
    
    while True:
        checkConns = []
        checkConns.append(server)
        checkConns.extend(server.clients)
        
        #print checkConns
        readyConns = select.select(checkConns,[],[],1)
        print "check"

        clientConns = [client for client in readyConns[0] if isinstance(client,ServerClientConnection)]
        serverConns = [client for client in readyConns[0] if isinstance(client,MessageBusServer)]
        for server in serverConns:
            print "handle new connection"
            server._handleNewConnection()
        for client in clientConns:
            try:
                print "read data"
                client._recvPacketPickled()
            except:
                print "client disconnected. Removing it!"
                server.disconnectClient(client)
    client.disconnectFromServer()

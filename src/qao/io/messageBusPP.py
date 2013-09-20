import socket,select,sys,time
import json
from WebSocketCommunicator import WebSocketCommunicator

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9090
DEFAULT_TIMEOUT = 500

TYPE_SUBSCRIBE   = "subscribe"
TYPE_UNSUBSCRIBE = "unsubscribe"
TYPE_PUBLISH     = "publish"
TYPE_SET         = "set"
TYPE_ACK         = "ack"
TYPE_NAK         = "nak"

class MessageBusClient(WebSocketCommunicator):

    def __init__(self):
        self.subscriptionCallbacks = {}
        WebSocketCommunicator.__init__(self)
        self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connectToServer(self, host = DEFAULT_HOST, port = DEFAULT_PORT, timeout = DEFAULT_TIMEOUT):
        self.clientSock.connect((host, port))
        self.clientSock.setblocking(0)
        self.clientSock.settimeout(timeout)
        self._sendClientHeader()
        time.sleep(.01) #HACK

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

    def _handlePublish(self,topic,data):
        if topic in self.subscriptionCallbacks: self.subscriptionCallbacks[topic](topic,data)

    def _handleHeaderReceived(self, httpHeader):
        #TODO: check validity HTTPHeader returned by the server
        pass

    def _sendPacketPickled(self,data):
        self._sendPacket(json.dumps(data, separators=(',', ':'), sort_keys=True))
        
    def _handleNewPacket(self, dataRaw):
        try:
            data = json.loads(dataRaw)

            #print "Depickle took %.2f s"%(time.time()-picklestarttime)
            if len(data) < 2:
                raise Exception("packet with insufficient number of args")

            if data[0] == TYPE_PUBLISH:
                if len(data) < 3: raise Exception("packet with insufficient number of args")
                self._handlePublish(data[1], data[2])

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
            client._recvData()
    client.disconnectFromServer()

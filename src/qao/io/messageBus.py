"""
MessageBus
----------

Subscribe/Publish data sharing via TCP/IP .

The messageBus module implements a subscribe/publish scheme for data exchange
between multiple applications within the same network. There are three types
of entities in this scheme. A publisher who wants to send data to whoever is
interested in, a subscriber who wants to be informed when new data related to
a specific topic is available, and a server connecting all participants.

.. note::

    Running this module as main routine starts a messageBus server with default
    settings, listening on all available network interfaces.

A simple publishing client is an application which connects to the server,
publishes information and quits afterwards::

    data = ["hello", "world"]
    simplePublish("some topic", data, "localhost")

A subscriber is usually an application which keeps running and waits for new
data to be received. You connect this client to the server first, and subscribe
to a specific topic you want to receive callbacks for::

    client = MessageBusClient()
    client.connectToServer("localhost")

    def doSomething(*args):
        print args
    client.subscribe("some topic", callback = doSomething)

    # run qt main loop
"""
import argparse

if __name__ == "__main__":
    """
    Add Arguments to explicitly choose the Qt version you like to run the messageBusServer.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--Qt4", action="store_true",
                        help="If you like to run messagebus Server using PyQt4 provide this flag"
                        )
    parser.add_argument("--PySide", action="store_true",
                        help="If you like to run messagebus Server using PySide provide this flag")

    args = parser.parse_args()

    if args.Qt4:
        from PyQt4 import QtCore
    elif args.PySide:
        from PySide import QtCore
    else:
        from PyQt5 import QtCore

    # enable memory debugger if possible
    try:
        import guppy.heapy.RM
        from guppy import hpy; hp=hpy()
        print "enabled heapy memory debug"
    except ImportError:
        pass

import sys,sha,time
import jsonEncoder
import websocket
import os

from qao.gui.qt import QtCore, QtNetwork, QT_API, QT_API_PYSIDE, QT_API_PYQT5, QT_API_PYQTv1
qtSignal = QtCore.Signal if (QT_API == QT_API_PYSIDE) else QtCore.pyqtSignal

__PYQT5_LOADED__ = (QT_API == QT_API_PYQT5)

DEFAULT_PORT = 9090
DEFAULT_TIMEOUT = 5000

TYPE_RPC_REGISTER   = "RPCregister"
TYPE_RPC_UNREGISTER = "RPCunregister"
TYPE_RPC_REQUEST    = "RPCrequest"
TYPE_RPC_REPLY      = "RPCreply"
TYPE_SUBSCRIBE      = "subscribe"
TYPE_UNSUBSCRIBE    = "unsubscribe"
TYPE_PUBLISH        = "publish"
TYPE_SET            = "set"
TYPE_INFO           = "info"
TYPE_ACK            = "ack"
TYPE_NAK            = "nak"

INFO_RPC_LIST       = "RPClist"

def simplePublish(topic, data, hostname, port = DEFAULT_PORT):
    """
    Publish new data on a messageBus server.

    This is a simple fire-and-forget function for publishing data. It connects
    to a server, publishes the given data, and returns when the data is sent. It
    is useful for small scripts exporting data.

    :param topic: (str) The topic for the messageBus event.
    :param data: (object) Any python object that can be serialized via json.
    :param hostname: (str) The hostname of the messageBus server.
    :param port: (int) TCP port to connect to.
    """
    c = MessageBusClient()
    c.connectToServer(hostname, port)
    c.publishEvent(topic, data)
    c.waitForEventPublished()

class MessageBusCommunicator(QtCore.QObject):
    def __init__(self, masking=False):
        QtCore.QObject.__init__(self)
        self.masking = masking
        self._cleanupCommunicator_()

    def _cleanupCommunicator_(self):
        self.currentFrame = websocket.Frame()
        self.neededBytes = next(self.currentFrame.parser)
        self.httpHeader = websocket.HTTPHeader()
        self.handshakeDone = False
        self.incompleteData = ''

    def _send(self,RawData, blocking=False):
        stream = QtCore.QDataStream(self.connection)
        if blocking:
            while self.connection.bytesToWrite() > 0:
                self.connection.waitForBytesWritten(DEFAULT_TIMEOUT)
        return stream.writeRawData(RawData)

    def _sendFrame_(self,data, opCode):
        mask = os.urandom(4) if self.masking else None
        frm = websocket.Frame(opCode,data,mask=mask,fin=1)
        nWritten = self._send(frm.build())

    def _sendPacket(self, data, binary = False):
        if len(data) <= 0: return
        opCode = websocket.OPCODE_BINARY if binary else websocket.OPCODE_ASCII
        dataSer = jsonEncoder.dumps(data, separators=(',', ':'), sort_keys=True)
        self._sendFrame_(dataSer,opCode)

    def _handleReadyRead(self):
        while self.connection.bytesAvailable() > 0:
            if not self.handshakeDone:
                while self.connection.canReadLine():
                    try:
                        line = self.connection.readLine()
                        if QT_API == QT_API_PYQTv1:
                            line = str(QtCore.QString(line))
                        else:
                            line = str(line)
                        self.httpHeader.parser.send(line)
                    except StopIteration:
                        self.handshakeDone=True
                        self._handleHeaderReceived(self.httpHeader)
                        break
            else:
                try:
                    if self.connection.bytesAvailable() < self.neededBytes: return
                    self.neededBytes = self.currentFrame.parser.send(str(self.connection.read(self.neededBytes)))
                except StopIteration:
                    self._handleFrame_(self.currentFrame)
                    self.currentFrame = websocket.Frame()
                    self.neededBytes = next(self.currentFrame.parser)

    def _pong_(self):
        self._sendFrame_('',websocket.OPCODE_PONG)

    def ping(self):
        self._sendFrame_('',websocket.OPCODE_PING)

    def _handleFrame_(self,frm):
        if frm.opCode == websocket.OPCODE_CLOSE:
            print "Disconnect Packet received. Cleaning up Communicator and wait for disconnect."
            self._cleanupCommunicator_()
            return

        if frm.opCode == websocket.OPCODE_PING:
            self._pong_()
            return

        if frm.opCode == websocket.OPCODE_ASCII or frm.opCode == websocket.OPCODE_BINARY:
            self.incompleteData = "%s%s"%(self.incompleteData, frm.data)
            if frm.fin == 1:
                self._handleNewPacket(self.incompleteData)
                self.incompleteData = ''

    def _handleNewPacket(self):
        raise NotImplementedError("Implement _handleNewPacket()")

    def _handleHeaderReceived(self):
        raise NotImplementedError("Implement _handleHeaderReceived()")

class ConnectionError(Exception):
    pass

class MessageBusClient(MessageBusCommunicator):
    """
    Class for sending/receiving data to/from the messageBus.

    A messageBus client keeps a persistent connection to a server, being
    able to publish new data or subscribe and recieve data from the bus.

    You first need a connection to a messageBus server::

        client = MessageBusClient()
        client.connectToServer("localhost")

    The client object is assumed to live in the context of a qt application,
    with an event-loop that handles network traffic. All you have to do is to
    register callbacks for topics you want to receive notifications and data
    for using the :func:`subscribe` method. Sending data to the bus is
    possible using the :func:`publishEvent` method.
    """

    receivedEvent = qtSignal(str, object)
    receivedInfo  = qtSignal(str, object)
    connected = qtSignal()
    disconnected = qtSignal()

    def __init__(self):
        MessageBusCommunicator.__init__(self)
        self.connection = QtNetwork.QTcpSocket()
        self.connection.disconnected.connect(self.disconnected)
        self.connection.readyRead.connect(self._handleReadyRead)

        self.subscriptionCallbacks = {}
        self.rpcCallbacks = {}
        self.rpcPendingRequests = {}

    def connectToServer(self, host, port = DEFAULT_PORT, timeout = DEFAULT_TIMEOUT):
        """
        Connect the client to a messageBus server.

        :param host: (str) Hostname of the server.
        :param port: (int) TCP port of the service.
        :param timeout: (int) Connection timeout in milliseconds.
        """
        self.connection.connectToHost(host, port)
        if not self.connection.waitForConnected(timeout):
            self.disconnected.emit()
            raise Exception("no connection to event server")
        self._sendHeader()

    def disconnectFromServer(self):
        """
        Disconnect the client from the current messageBus server.
        """
        self._cleanupCommunicator_()
        self.subscriptionCallbacks={}
        self.connection.disconnectFromHost()

    def isConnected(self):
        """
        Check if the client is connected to a server.
        :returns: (bool) Connection status.
        """
        return self.connection.state() == self.connection.ConnectedState

    def subscribe(self, topic, callback = None):
        """
        Subscribe to a topic on the currently connected bus.

        Whenever new data is published on the messageBus server, the data is
        forwarded to the registered callback function if the subscribed topic
        matches. If you already subscribed for this topic, the previously
        registered callback function will be replaced by the new one.

        :param topic: (str) Topic to receive events for.
        :param callback: (callable) Callback function for new events.
        """
        topic = str(topic)
        self._sendPacket([TYPE_SUBSCRIBE, topic])
        if callback: self.subscriptionCallbacks[topic] = callback

    def unsubscribe(self, topic):
        """
        Unsubscribe from a topic on the currently connected bus.

        Remove your subscription means that you will no longer receive
        callbacks for the unsubscribed topic.
        :param topic: (str) Topic to unsubscribe from.
        """
        topic = str(topic)
        self._sendPacket([TYPE_UNSUBSCRIBE, topic])
        if topic in self.subscriptionCallbacks:
            self.subscriptionCallbacks.pop(topic)

    def publishEvent(self, topic, data):
        """
        Publish data on the connected messageBus.

        This methods sends new data to the messageBus, making it available
        for anyone who subscribed to the given topic. Any data will be
        automatically serialized by JSON and sent to the subscribers.

        :param topic: (str) Topic for the published data.
        :param data: (object) Any python object that can be serialized via JSON.
        """
        topic = str(topic)
        self._sendPacket([TYPE_PUBLISH, topic, data])

    def waitForEventPublished(self, timeout = DEFAULT_TIMEOUT):
        """
        Block until all data is sent.

        The messageBus client is using asynchronous transfers. When the publishEvent
        method returns, the client has not finished sending the data to the server yet.
        This method will block until the message has been sent, or raise an exception.

        :param timeout: (int) Maximum time to wait for data to be sent.
        """
        while self.connection.bytesToWrite() > 0:
            self.connection.waitForBytesWritten(DEFAULT_TIMEOUT)

    def rpcRegister(self, funcName, argList, retCount, callback):
        """
        Register RPC call that should be made available.

        A program that has the ability to have certain functions called remotely must register
        these functions at the server before they can be called by other programs. This is done using this function

        :param funcName: (str) name under which the function can be called by the remote end. Preferably use the <program name>.<function name> scheme
        :param argList:  (list) list of argument names. Those names are used as keys in the 'args' dict when a rpcCall is made.
        :param retCount: (int) number of return values the function gives.
        :param callback: (function) a reference to the function that should be called if a remote client requests it.
        """
        self.rpcCallbacks.update({funcName:callback})
        self._sendPacket([TYPE_RPC_REGISTER, funcName, {'argList':argList, 'retCount':retCount}])

    def rpcUnregister(self, funcName):
        """
        Unregister RPC call that should no longer be available.

        :param funcName: (str) name of the function that should be unregistered.
        """
        if funcName in self.rpcCallbacks:
            del(self.rpcCallbacks[funcName])
            self._sendPacket([TYPE_RPC_UNREGISTER, funcName])

    def rpcCall(self, funcName, args, answerCallback = None):
        """
        Call a remote function via RPC.

        :param funcName: (str) name of the remote function that should be called.
        :param funcName: (dict) dictionary of named arguments passed to the remote function. The key names have to match the parameter names registered by the remote program.
        :param answerCallback: (function) function to be called when the answer is received.
                                          Two parameters will be given to the function: 1. the funcName, 2. a dictionary containing the result of the function call in the key 'ret' as well as the success status of the function call in the key 'succes' (bool).
        """
        identifier = str(int(time.time()*1000))
        self._sendPacket([TYPE_RPC_REQUEST, funcName, {'args':args, 'id':identifier}])
        self.rpcPendingRequests.update({identifier:answerCallback})

    def rpcInfoRequest(self):
        self._sendPacket([TYPE_INFO, INFO_RPC_LIST])

    def _sendHeader(self):
        hdr = websocket.DefaultHTTPClientHeader()
        nWritten = self._send(hdr.createHeader(),blocking=True)

    def handleEvent(self, topic, data):
        self.receivedEvent.emit(topic, data)
        if topic in self.subscriptionCallbacks: self.subscriptionCallbacks[topic](data)

    def _handleRPCRequest(self, funcName, data):
        if funcName in self.rpcCallbacks:
            try:
                ret = self.rpcCallbacks[funcName](data['args'])
                data.update({'ret':ret})
                data.update({'success':True})
            except Exception, e:
                data.update({'success':False})
                data.update({'error':str(e)})
            self._sendPacket([TYPE_RPC_REPLY,funcName,data])

    def _handleHeaderReceived(self,httpHeader):
        #TODO: check header received from the server
        self.connected.emit()
        pass

    def _handleNewPacket(self, dataRaw):
        try:
            data = jsonEncoder.loads(dataRaw)

            #commands needing 1 argument
            if len(data) < 2:
                raise Exception("packet with insufficient number of args")

            if data[0] == TYPE_NAK:
                raise Exception("server reported: %s" % data[1])

            #command needing 2 arguments
            if len(data) < 3:
                raise Exception("packet with insufficient number of args")

            if data[0] == TYPE_PUBLISH:
                self.handleEvent(data[1], data[2])
                return

            if data[0] == TYPE_INFO:
                self.receivedInfo.emit(data[1], data[2])
                return

            if data[0] == TYPE_RPC_REQUEST:
                self._handleRPCRequest(data[1], data[2])
                return

            if data[0] == TYPE_RPC_REPLY:
                if 'id' in data[2] and data[2]['id'] in self.rpcPendingRequests:
                    if self.rpcPendingRequests[data[2]['id']] != None:
                        self.rpcPendingRequests[data[2]['id']](data[1],data[2])
                    del(self.rpcPendingRequests[data[2]['id']])
                return

        except Exception, e:
            errorstr = type(e).__name__ + ", " + str(e)
            sys.stderr.write(errorstr + "\n")


class ServerClientConnection(MessageBusCommunicator):

    eventPublished  = qtSignal(str, object)
    infoRequested   = qtSignal(str, object)
    rpcRequested    = qtSignal(str, object, object)
    rpcReplied      = qtSignal(str, object)
    disconnected    = qtSignal()

    def __init__(self, connection):
        MessageBusCommunicator.__init__(self)
        self.connection = connection
        self.connection.disconnected.connect(self.disconnected)
        self.connection.readyRead.connect(self._handleReadyRead)
        self.packetSize = 0
        self.subscriptions = set([])
        self.rpcFunctions = {}
        self.rpcPendingRequests = {}

    def forwardEvent(self, topic, data, pkgType=TYPE_PUBLISH):
        try:
            self._sendPacket([pkgType, topic, data])
        except MemoryError:
            print "Out of memory"
            print hp.heap()
            exit()

    def sendRPCRequest(self, func, data, issuer):
        if not 'id' in data:
            data.update({'id':str(int(time.time()*1000))})
        self.rpcPendingRequests.update({data['id']:issuer})
        self.forwardEvent(func, data, pkgType=TYPE_RPC_REQUEST)

    def _handleHeaderReceived(self,httpHeader):
        self._send(httpHeader.buildServerReply().createHeader())

    def _handleNewPacket(self, dataRaw):
        try:
            data = jsonEncoder.loads(dataRaw)

            if len(data) < 2:
                raise Exception("packet with insufficient number of args")

            # add the second arg to the list of rpcFunctions
            if data[0] == TYPE_RPC_REGISTER:
                if len(data) < 3:
                    raise Exception("packet with insufficient number of args")
                if not 'argList' in data[2]:
                    print "Could not register RPC call %s since argList was missing in registration packet"%(data[1])
                    return
                if not 'retCount' in data[2]:
                    print "Could not register RPC call %s since retCount was missing in registration packet"%(data[1])
                    return
                self.rpcFunctions.update({data[1]:data[2]})
                return

            # remove the second arg to the list of rpcFunctions
            if data[0] == TYPE_RPC_UNREGISTER:
                if data[1] in self.rpcFunctions:
                    del(self.rpcFunctions[data[1]])
                return

            # handle info
            if data[0] == TYPE_INFO:
                if len(data) < 2:
                    raise Exception("packet with insufficient number of args")
                if data[1] == INFO_RPC_LIST:
                    self.infoRequested.emit(data[1],self)
                return

            # handle RPC request
            if data[0] == TYPE_RPC_REQUEST:
                if len(data) < 3:
                    raise Exception("packet with insufficient number of args")
                self.rpcRequested.emit(data[1],data[2], self)
                return

            # handle RPC reply
            if data[0] == TYPE_RPC_REPLY:
                if len(data) < 3:
                    raise Exception("packet with insufficient number of args")
                if not data[1] in self.rpcFunctions:
                    print "Sending reply for unregistered Function %s"%(data[1])
                    return
                if 'id' in data[2] and data[2]['id'] in self.rpcPendingRequests:
                    self.rpcPendingRequests[data[2]['id']].forwardEvent(data[1],data[2], pkgType=TYPE_RPC_REPLY)
                self.rpcReplied.emit(data[1],data[2])
                return

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
        client.rpcRequested.connect(self._handleRPCRequest)
        client.infoRequested.connect(self._handleInfoRequest)
        self.clients.append(client)
        self.clientConnected.emit(client)
        print "new client connected (active connections: %d)" % len(self.clients)
        assert (not self.server.hasPendingConnections()) # TODO: do we have to check for multiple connections?

    def _handlePublish(self, topic, data):
        topic = str(topic)
        # search clients for subscribers
        for client in self.clients:
            if topic in client.subscriptions:
                client.forwardEvent(topic, data)
        self.eventPublished.emit(topic, data)

    def _handleRPCRequest(self, func, data, issuer):
        func = unicode(func)
        for client in self.clients:
            if func in client.rpcFunctions:
                if 'args' in data and len(data['args']) == len(client.rpcFunctions[func]['argList']):
                    client.sendRPCRequest(func,data,issuer)
                else:
                    print "Arguments messed up for requested function %s"%(func)

    def _handleInfoRequest(self,typ, issuer):
        rpcFunctions = {}
        for client in self.clients:
            rpcFunctions.update(client.rpcFunctions)
        issuer.forwardEvent(str(typ), rpcFunctions, pkgType=TYPE_INFO)

    def _handleDisconnect(self):
        client = self.sender()
        self.clientDisconnected.emit(client)
        self.clients.remove(client)
        print "client disconnected (active connections: %d)" % len(self.clients)

if __name__ == "__main__":
    # enable CTRL+C break
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # implement basic console server
    class ConsoleServer(MessageBusServer):
        def __init__(self):
            MessageBusServer.__init__(self)
            self.eventPublished.connect(self.printEventPublished)

        def printEventPublished(self, topic, data):
            print "new event: %s" % str(topic)

    print "Starting MessageServer at port %d" % DEFAULT_PORT
    app = QtCore.QCoreApplication([])
    serv = ConsoleServer()
    app.exec_()

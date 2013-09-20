import struct
import time
import websocket

DEFAULT_TIMEOUT=2

class TimeoutException(Exception):
    def __init__(self,estring):
        Exception.__init__(self,estring)

class NoDataException(Exception):
    def __init__(self,estring):
        Exception.__init__(self,estring)
        
class WebSocketCommunicator():
    def __init__(self, connSock=None):
        self.clientSock = connSock
        self.handshaken = False
        self.incompleteData = ''
        self.currentFrame = websocket.Frame()
        self.neededBytes = next(self.currentFrame.parser)
        self.httpHeader = websocket.HTTPHeader()
        self.neededBytes=2
        
    def fileno(self):
        #needed for select
        return self.clientSock.fileno()

    def _send(self,byteArray,blocking=False):
        totalBytesWritten=0
        while totalBytesWritten < len(byteArray):
            if blocking:
                self.clientSock.sendall(byteArray[totalBytesWritten:])
                return
            else:
                bytesWritten = self.clientSock.send(byteArray[totalBytesWritten:])
            totalBytesWritten += bytesWritten
        if totalBytesWritten != len(byteArray): raise Exception("Not all Bytes written!")
    
    def _receive(self,length,timeout=DEFAULT_TIMEOUT,insist=True):
        lenRecv = 0
        recvData = ''
        startTime = time.time()
        while lenRecv < length:
            if time.time()-startTime > timeout: raise TimeoutException("reading from socket timed out")
            currentData = self.clientSock.recv(min(4096,length-lenRecv))
            if len(currentData) == 0: raise NoDataException('receive() called but no data present. Probalby the peer disconnected')
            recvData = "%s%s"%(recvData,currentData)
            if not insist: break
            lenRecv += len(currentData)
            
        return recvData
    
    def _sendPacket(self,data):
        self._send(websocket.Frame(opCode=1,data=data,fin=1).build())
        
    def _sendClientHeader(self):
        hdr = websocket.DefaultHTTPClientHeader()
        nWritten = self._send(hdr.createHeader(),blocking=True)
                
    def connectionClose(self):
        self.clientSock.close()
        
    def _recvData(self):
        if self.handshaken == False:
            try:
                self.incompleteData = "%s%s"%(self.incompleteData,self._receive(16,insist=False))
            except NoDataException, e:
                print str(e)
                self.connectionClose()
                
            if self.incompleteData.find('\r\n') != -1:
                lines = self.incompleteData.split('\r\n')
                try:
                    for line in lines[:-1]:
                        self.httpHeader.parser.send(line)
                    self.incompleteData = lines[-1]
                except StopIteration:
                    self._handleHeaderReceived(self.httpHeader)
                    self.handshaken = True
                    print "handshake sucessfull"
                    self.incompleteData = ''
                    return

        else:
            try:
                self.neededBytes = self.currentFrame.parser.send(self._receive(self.neededBytes))
            except NoDataException, e:
                print str(e)
                self.connectionClose()
                
            except StopIteration:
                self.incompleteData = '%s%s'%(self.incompleteData,self.currentFrame.data)
                if self.currentFrame.fin:
                    if self.currentFrame.opCode == 8:
                        self.connectionClose()
                    elif self.currentFrame.opCode == 1 or self.currentFrame.opCode == 2:
                        self._handleNewPacket(self.incompleteData)
                        self.incompleteData = ''
                    else:
                        raise Exception("Unknown Op Code %x received"%(self.currentFrame.opCode))
                    self.currentFrame=websocket.Frame()
                    self.neededBytes = next(self.currentFrame.parser)
        
    def _handleNewPacket(self,data):
        raise NotImplementedError("Implement _handleNewData()")
    
    def _handleHeaderReceived(self, httpHeader):
        raise NotImplementedError("Implement _handleHeaderReceived()")

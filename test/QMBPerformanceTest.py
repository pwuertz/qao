from qao.io import messageBusPP as messageBus
try:
    from PyQt4 import QtCore
except ImportError:
    from PySide import QtCore

import signal,time
signal.signal(signal.SIGINT, signal.SIG_DFL) 
        
#Variables for testing purpose
i=0
m=1920
n=1080 #High Definition - the future of television
#create huge matrix which should be send
hugematrix = [[None for x in range(m)] for x in range(n)]

def printEventReceived(topic, data):
    global i
    print "%s: %s (Dauer:%.2f)"%(topic,data[0],time.time()-float(data[1]))
    #lets play ping-pong with the server:
    serv.publishEvent("testing",[i,time.time(),hugematrix])
    i +=1

app = QtCore.QCoreApplication([])

#define new client
serv = messageBus.QMessageBusClient()
serv.connectToServer("localhost")

#subscribe
serv.subscribe("testing",printEventReceived)

#publish event to start the game
serv.publishEvent("testing",["foo","1.0"])
app.exec_()


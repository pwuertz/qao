import sys
sys.path.append("../src/qao/io")
import messageBus
from messageBus import QtCore, qtSignal
import signal,time
signal.signal(signal.SIGINT, signal.SIG_DFL)

app = QtCore.QCoreApplication([])

def retFunction(funcName, data):
	if data['success']:
		print "%s(%s): %s"%(funcName,data['args'],data['ret'])
	else:
		print "An Error occured during RPC call: %s"%(data['error'])

def dummyFunction(args):
	print "remote Function call"
	if  not 'count' in args: 
		raise Exception("Missing needed argument count")
	a = args['count']
	return a+1

def infoPrinter(topic, rpcFunctions):
	print "%i RPC functions registered"%(len(rpcFunctions))
	for key, value in rpcFunctions.items():
		print "%s(%s) returns %i parameter"%(key,value['argList'],value['retCount'])
		#print "%s(%s) returns %i parameter"%(key,key['argList'],int(key['retCount']))

#define new client
client = messageBus.MessageBusClient()
client.connectToServer("localhost",9090)
client.receivedInfo.connect(infoPrinter)

#subscribe
client.subscribe("testing")
client.rpcInfoRequest()
#register dummy function
client.rpcRegister('testing.dummy',['count'],1,dummyFunction)
client.rpcInfoRequest()
#call dummy function with some argument
client.rpcCall('testing.dummy',{'count':12},retFunction)

app.exec_()

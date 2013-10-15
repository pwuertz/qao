"""
Datalogger
----------

A Simple dictionary logging to apache couchdb 

The Datalogger will listen to dalog.log on the message bus and add all keys and values within the published dictionary to the database
The Data will be logged within the given time interval and stored to a couchDb

.. note::

    Running this module as main routine starts a datalog server with default
    settings.

A simple log client is an application which uses the MessageBus to communicate with the Datalog server,
publishes information and quits afterwards. The two publish functions will do the same::

    data = {"hello":"world"}
    simpleLogValue("hello","world,"localhost")
    simpleLogData(data,"localhost")


A Client may be used to controll the datalog server.::

    client = DataLogClient()
    client.connectToMessageBus("localhost")
    
    client.key = "time"
    client.log(time.time()) # will log the time
    client.logDict({"time":time.time()}) # will have the same result as the line above 
    
In case you want the server to log a specific topic instead of publishing on daLog.log
here all data published under topic time.clock on the messagebus will be delegated to the time key in database:

    client.tellSubscribe("time.clock", "time")
    ...
    client.tellUnsubscribe("time.clock")
   
    # run qt main loop
"""
from qao.io.messageBus import *
from PyQt4 import QtCore
import couchdb
import random
import time
import numpy


DALOG_COUCH_PORT = 5984
DALOG_COUCH_HOST = "localhost"
DALOG_COUCH_BASE = 'bec_datalog'
DALOG_CMD_SUBSCRIBE = "SUBS"
DALOG_CMD_UNSUBSCRIBE = "UNSUBS"
DALOG_CMD_PUBLISH = "PUB"
DALOG_CMD_REMOVE = "RM"
DALOG_CMD_IGNORE = "IGN"
DALOG_CMD_UNIGNORE = "UIGN"

DALOG_TOPIC = "daLog.log" #logging topic
DALOG_COMMAND = "daLog.command" #command topic 
DALOG_PUBLISH = "daLog.current" #publish topic
DALOG_INTERVAL = 5 #logging interval in seconds

# do not edit this part
DALOG_COUCH_BASE_URI = "http://%s:%i/%s"%(DALOG_COUCH_HOST,DALOG_COUCH_PORT,DALOG_COUCH_BASE)

def simpleLogValue(key,value,messageBus,messageBusPort=DEFAULT_PORT):
    '''
    Tell DataLogger to add the value with keyword key to it's internal storage in order to store it to the database
    :param key: keyword for storage in database
    :param value: value to be stored in database
    :param messageBus: hostname of the messagebus
    :param messageBusPort: port for the messagebus
    '''
    simplePublish(DALOG_TOPIC, {key:value},messageBus,messageBusPort)
    
def simpleLogData(data,messageBus,messageBusPort=DEFAULT_PORT):
    '''
    Tell DataLogger to add the data dictionary to it's internal storage in order to store it to the database
    :param data: dictionary containing keys and values which should be stored into the database
    :param messageBus: hostname of the messagebus
    :param messageBusPort: port for the messagebus
    '''
    simplePublish(DALOG_TOPIC, data, messageBus,messageBusPort)

class DataLogServer(QtCore.QObject):
    __PROTECTEDKEYS__ = ['_rev','_id']
        
    def __init__(self,couchHost=DALOG_COUCH_HOST,couchPort=DALOG_COUCH_PORT,database=DALOG_COUCH_BASE,logTime=DALOG_INTERVAL):
        self.couchHost = couchHost
        self.couchPort = couchPort
        self.database = database
        self.logTime = logTime
        QtCore.QObject.__init__(self)
        self.couch = couchdb.client.Server("http://%s:%i"%(couchHost,couchPort)) 
        self.db = self.couch[database]
        self.data = {"timestamp":0}
        self.subscriptions = {}
        self.mbus = MessageBusClient()
    
    def connectToMessageBus(self,messageBusHost,messageBusPort=DEFAULT_PORT):
        #create the messagbus to listen to
        self.mbus.connectToServer("localhost")
        if(not self.mbus.isConnected()):
            raise Exception('Error: Could not connect to messageBus')
        #data topic where data is published
        self.mbus.subscribe(DALOG_TOPIC, self.addDict)
        self.mbus.subscribe(DALOG_COMMAND, self.commandHandler)
    
    def start(self):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.logTime*1000.0)
        self.timer.timeout.connect(self.log)
        self.timer.start()
        
    @staticmethod
    def setup(couchHost=DALOG_COUCH_HOST,couchPort=DALOG_COUCH_PORT,database=DALOG_COUCH_BASE):
        couch = couchdb.client.Server("http://%s:%i"%(couchHost,couchPort))
        db = None
        for _db in couch:
            if(_db == database):
                db = couch[database]
                print "found db %s"%_db
                break
        if db == None:
            db = couch.create(database)
            print "created db %s"%db.name
            
    def __cleanUp(self):
        '''
        this cleanup is necessary in order to prevent data from being overwritten
        '''
        for key in self.__PROTECTEDKEYS__:
            if(key in self.data):
                del self.data[key]
    
    def log(self):
        ''' assign the current timestamp '''
        self.data["timestamp"] = int(time.time())
        ''' and remove couchdb reserved keys '''
        self.__cleanUp()
        self.db.save(self.data)
        self.logged.emit(self.data)
        ''' reset the data '''
        self.data = {}
        
    def addDict(self,data):
        '''
        adds a dictionary with its contents to the storage
        '''
        for key in data:
            self.data[key] = data[key]
            
    def addData(self,key,value):
        '''
        assigns key and value to the storage dictionary
        :param key:
        :param value:
        '''
        if(key not in self.__PROTECTEDKEYS__):
            self.data[key] = value
        else:
            print('%s is protected. not able to store value %s'%(key,str(value)))
    
    logged = QtCore.pyqtSignal(object)
    
    def commandHandler(self,data):
        cmd = data[0]
        print "%s: %s"%(cmd,str(data))
        if cmd == DALOG_CMD_SUBSCRIBE:
            self.subscribe(data[1],data[2])
        elif cmd == DALOG_CMD_UNSUBSCRIBE:
            self.unsubscribe(data[1])
        elif cmd == DALOG_CMD_PUBLISH:
            self.publish()
        elif cmd == DALOG_CMD_REMOVE:
            self.remove(data[1])
        elif cmd == DALOG_CMD_IGNORE:
            self.ignore(data[1])
    
    def ignore(self,key):
        self.__PROTECTEDKEYS__.append(key)
        
    def unignore(self,key):
        if key in self.__PROTECTEDKEYS__:
            self.__PROTECTEDKEYS__.remove(key)
    
    def remove(self,key):
        if(key in self.data):
            del self.data[key]
            
    def publish(self):
        self.mbus.publishEvent(DALOG_PUBLISH, self.data)
    
    def subscribe(self,topic,key=None):
        if(key == None):
            key = topic
        self.subscriptions[topic] = key
        self.mbus.subscribe(topic,lambda value: self.addData(key,value))
        
    def unsubscribe(self,topic):
        self.mbus.unsubscribe(topic)
        del self.data[self.subscriptions[topic]]
        del self.subscriptions[topic]
        
class DataLogClient(QtCore.QObject):
    '''
    Class for sending data over the messagebus to the dataLog server

    You first need a connection to a messagebus server::
    
        client = DataLogClient()
        client.connectToMessageBus("localhost")
    
    then you are able to send your data::
    
        client.key = "time"
        client.log(time.time()) # will log the time
        client.logDict({"time":time.time()}) # will have the same result as the line above
    
    
    '''
    def __init__(self,key="KEY"):
        QtCore.QObject.__init__(self)
        self.mbus = MessageBusClient()
        self.key = key
        self.callback = None
    
    def connectToMessageBus(self,host,port=DEFAULT_PORT): 
        '''
        Connect the client to a messageBus server.
        
        :param host: (str) Hostname of the server.
        :param port: (int) TCP port of the service.
        '''
        self.mbus.connectToServer(host,port)
    
    def tellSubscribe(self,topic,key):
        '''
        
        tell Datalog server to listen to the specified topic and use the key for identification
        
        :param topic: (str) topic to publish on messagebus
        :param key: (str) key to store data in datbase
        '''
        self.mbus.publishEvent(DALOG_COMMAND,[DALOG_CMD_SUBSCRIBE,topic,key])
        
    def tellUnsubscribe(self,topic):
        '''
        tell Datalog server to stop listening to the specified topic
        
        :param topic: (str) topic to publish on messagebus
        '''
        self.mbus.publishEvent(DALOG_COMMAND,[DALOG_CMD_UNSUBSCRIBE,topic])
        
    def tellIgnore(self,key):
        '''
        tell datalog server to ignore the following key
        :param key:(str) name of keyword to be ignored
        '''
        self.mbus.publishEvent(DALOG_COMMAND,[DALOG_CMD_IGNORE,key])
        
    def tellUnignore(self,key):
        '''
        tell datalog server not to ignore the key any longer
        
        :param key:(str) name of keyword to be removed from ignore list
        '''
        self.mbus.publishEvent(DALOG_COMMAND,[DALOG_CMD_UNIGNORE,key])
        
    def tellRemove(self,key):
        '''
        tell datalog server to remove the given key from current storage (not the database itself)
        
        :param key:(str)
        '''
        self.mbus.publishEvent(DALOG_COMMAND,[DALOG_CMD_REMOVE,key])
        
    def getLastData(self,callback):
        '''
        Sends a query to datalog server to publish it's current available data
        :param callback: (func(dict)) callback function for last dictionary
        '''
        if(self.callback == None):
            self.callback = callback
        elif(type(self.callback) is list):
            self.callback.append(callback)
        else:
            temp = self.callback
            self.callback = [temp,callback]
        self.mbus.subscribe(DALOG_PUBLISH, self.__handleLastLoggedData)
        self.mbus.publishEvent(DALOG_COMMAND,[DALOG_CMD_PUBLISH])
    
    def _publish(self,cmd,data):
        
        self.mbus.publishEvent(cmd,data)
        
    def __handleLastLoggedData(self,data):
        '''
        Internal procedure to invoke stored callbacks
        :param data: (dict) current dictionary with data from datalog server
        '''
        if(self.callback != None):
            self.mbus.unsubscribe(DALOG_PUBLISH)
            if(type(self.callback) is list):
                for func in self.callback:
                    func(data)
            else:
                self.callback(data)
            self.callback = None
    
    @QtCore.pyqtSlot(object)
    def log(self,value):
        '''
        send the value to the datalog server. it will be stored under self.key
        :param value: (object) value to be send to datalog server 
        '''
        self.mbus.publishEvent(DALOG_TOPIC, {self.key:value})
    
    @QtCore.pyqtSlot(object)
    def logDict(self,dict):
        '''
        send the dict to the datalog server. it will be stored under self.key
        :param dict: (dict) dictionary to be stored in database 
        '''
        self.mbus.publishEvent(DALOG_TOPIC,dict)

if __name__ == "__main__":
    # enable CTRL+C break
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # implement basic console server
    class ConsoleServer(DataLogServer):
        def __init__(self):
            DataLogServer.__init__(self)
            self.logged.connect(self.printEventLogged)
            
        def printEventLogged(self, data):
            print "new event: %s" % str(data)
    
    print "Starting Datalogger"
    app = QtCore.QCoreApplication([])
    serv = ConsoleServer()
    
    app.exec_()

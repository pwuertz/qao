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
from qao.gui.qt import QtCore
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
    :param key: (str) keyword for storage in database
    :param value: (str) value to be stored in database
    :param messageBus: (str) hostname of the messagebus
    :param messageBusPort: (int) port for the messagebus
    '''
    simplePublish(DALOG_TOPIC, {key:value},messageBus,messageBusPort)
    
def simpleLogData(data,messageBus,messageBusPort=DEFAULT_PORT):
    '''
    Tell DataLogger to add the data dictionary to it's internal storage in order to store it to the database
    :param data: (dict) dictionary containing keys and values which should be stored into the database
    :param messageBus: (str) hostname of the messagebus
    :param messageBusPort: (int) port for the messagebus
    '''
    simplePublish(DALOG_TOPIC, data, messageBus,messageBusPort)

class DataLogServer(QtCore.QObject):
        
    def __init__(self,couchHost=DALOG_COUCH_HOST,couchPort=DALOG_COUCH_PORT,database=DALOG_COUCH_BASE,logTime=DALOG_INTERVAL):
        self.couchHost = couchHost
        self.couchPort = couchPort
        self.database = database
        self.logTime = logTime
        QtCore.QObject.__init__(self)
        self.couch = couchdb.client.Server("http://%s:%i"%(couchHost,couchPort)) 
        self.db = self.couch[database]
        self.data = {"timestamp":0}
        self.lastStoredData = self.data
        self.subscriptions = {}
        self.mbus = MessageBusClient()
        self.__PROTECTEDKEYS__ = (['_rev','_id'])
    
    def isConnected(self):
        return self.mbus.isConnected()
            
    def connectToMessageBus(self,messageBusHost,messageBusPort=DEFAULT_PORT):
        #create the messagbus to listen to
        self.mbus.connectToServer(messageBusHost)
        if(not self.mbus.isConnected()):
            raise Exception('Error: Could not connect to messageBus')
        #data topic where data is published
        self._subscribe(DALOG_TOPIC, self.addDict)
        self._subscribe(DALOG_COMMAND, self.commandHandler)
        
    def disconnectFromServer(self):
        '''
        disconnect From MessageBus
        '''
        self.mbus.disconnectFromServer()
        
    def _subscribe(self,topic,callback):
        self.mbus.subscribe(topic, callback)
        self.mbus.waitForEventPublished()
        
    def start(self):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.logTime*1000.0)
        self.timer.timeout.connect(self.log)
        self.timer.start()
        
    @staticmethod
    def setup(couchHost=DALOG_COUCH_HOST,couchPort=DALOG_COUCH_PORT,database=DALOG_COUCH_BASE):
        '''
        this method creats a database for logging if not existent
        :param couchHost: (str) hostname for database
        :param couchPort: (int) port for database
        :param database: (str) selected database
        '''
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
            
    def _cleanUp(self):
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
        self.lastStoredData = self.data
        self._cleanUp()
        self.db.save(self.lastStoredData)
        self.logged.emit(self.lastStoredData)
        ''' reset the data '''
        self.data = {}
        
    def addDict(self,data):
        '''
        adds a dictionary with its contents to the storage
        '''
        print 'new Data: %s'%data.keys()
        self.data.update(data)
            
    def addData(self,key,value):
        '''
        assigns key and value to the storage dictionary
        :param key:
        :param value:
        '''
        print 'new Data: %s'%key
        if(key not in self.__PROTECTEDKEYS__):
            self.data[key] = value
        else:
            print('%s is protected. not able to store value %s'%(key,str(value)))
    
    logged = QtCore.pyqtSignal(object)
    
    def commandHandler(self,data):
        '''
        handles all command datalog receives over DALOG_CMD topic on mbus
        :param data: [command, *data]
        '''
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
        elif cmd == DALOG_CMD_UNIGNORE:
            self.unignore(data[1])
    
    def ignore(self,key):
        '''
        will ignore all data with this key
        '''
        self.__PROTECTEDKEYS__.append(key)
        
    def unignore(self,key):
        '''
        Logger will stop ignoring this key 
        '''
        if key in self.__PROTECTEDKEYS__:
            self.__PROTECTEDKEYS__.remove(key)
    
    def remove(self,key):
        '''
        removes currently available data
        '''
        if(key in self.data):
            del self.data[key]
                       
    def publish(self):
        '''
        Publishs current available data
        '''
        self.lastStoredData.update(self.data)
        self.mbus.publishEvent(DALOG_PUBLISH, self.lastStoredData)
    
    def subscribe(self,topic,key=None):
        '''
        Datalogger will subscribe the topic and store it to the key
        :param topic: topic to subscribe
        :param key: keyword for data storage if data is a keyValuePair. Otherwise value is assumed to be a dictionary 
        '''
        if(key == None):
            self.subscriptions[topic] = topic
            self._subscribe(topic,lambda value: self.addDict(value))
        else:
            self.subscriptions[topic] = key
            self._subscribe(topic,lambda value: self.addData(key,value))
            
        
    def unsubscribe(self,topic):
        '''
        will stop the logging of posted data on a specific topic
        '''
        if topic in self.subscriptions:
            self.mbus.unsubscribe(topic)
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
    
    def disconnectFromServer(self):
        '''
        disconnect From MessageBus
        '''
        self.mbus.disconnectFromServer()
        
    def connectToMessageBus(self,host,port=DEFAULT_PORT): 
        '''
        Connect the client to a messageBus server.
        
        :param host: (str) Hostname of the server.
        :param port: (int) TCP port of the service.
        '''
        self.mbus.connectToServer(host,port)
    
    def tellSubscribe(self,topic,key=None):
        '''
        
        tell Datalog server to listen to the specified topic and use the key for identification
        
        :param topic: (str) topic to publish on messagebus
        :param key: (str) key to store data in datbase
        '''
        topic = str(topic)
        self._publish(DALOG_COMMAND,[DALOG_CMD_SUBSCRIBE,topic,key])
        
    def tellUnsubscribe(self,topic):
        '''
        tell Datalog server to stop listening to the specified topic
        
        :param topic: (str) topic to publish on messagebus
        '''
        self._publish(DALOG_COMMAND,[DALOG_CMD_UNSUBSCRIBE,topic])
        
    def tellIgnore(self,key):
        '''
        tell datalog server to ignore the following key
        :param key:(str) name of keyword to be ignored
        '''
        self._publish(DALOG_COMMAND,[DALOG_CMD_IGNORE,key])
        
    def tellUnignore(self,key):
        '''
        tell datalog server not to ignore the key any longer
        
        :param key:(str) name of keyword to be removed from ignore list
        '''
        self._publish(DALOG_COMMAND,[DALOG_CMD_UNIGNORE,key])
        
    def tellRemove(self,key):
        '''
        tell datalog server to remove the given key from current storage (not the database itself)
        
        :param key:(str)
        '''
        self._publish(DALOG_COMMAND,[DALOG_CMD_REMOVE,key])
        
    def getLastData(self,callback):
        '''
        Sends a query to datalog server to publish it's current available data
        :param callback: (func(dict)) callback function for last dictionary
        '''
        if(self.callback == None):
            self.callback = callback
        elif(isinstance(self.callback,list)):
            self.callback.append(callback)
        else:
            self.callback = [self.callback,callback]
        self.mbus.subscribe(DALOG_PUBLISH, self.__handleLastLoggedData)
        self.mbus.waitForEventPublished()
        self._publish(DALOG_COMMAND,[DALOG_CMD_PUBLISH])
    
    def _publish(self,cmd,data):
        self.mbus.publishEvent(cmd,data)
        self.mbus.waitForEventPublished()
        
    def __handleLastLoggedData(self,data):
        '''
        Internal procedure to invoke stored callbacks
        :param data: (dict) current dictionary with data from datalog server
        '''
        if(self.callback != None):
            self.mbus.unsubscribe(DALOG_PUBLISH)
            if(isinstance(self.callback,list)):
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
        self._publish(DALOG_TOPIC, {self.key:value})
    
    @QtCore.pyqtSlot(object)
    def logDict(self,dict):
        '''
        send the dict to the datalog server. it will be stored under self.key
        :param dict: (dict) dictionary to be stored in database 
        '''
        self._publish(DALOG_TOPIC,dict)

if __name__ == "__main__":
    # enable CTRL+C break
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # implement basic console server
    class ConsoleServer(DataLogServer):
        def __init__(self):
            DataLogServer.__init__(self)
            self.logged.connect(self.printEventLogged)
            self.time = 0
            
        def printEventLogged(self, data):
            print "new event: %s took %s" % (str(data),time.time()-self.time)
    
    print "Starting Datalogger"
    app = QtCore.QCoreApplication([])
    serv = ConsoleServer()
    
    serv.connectToMessageBus('localhost')
    print 'connected: ',serv.isConnected()
    if(serv.isConnected()):
        serv.start()
        
    sys.exit(app.exec_())

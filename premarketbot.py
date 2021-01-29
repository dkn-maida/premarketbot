#!/usr/bin/env python


from ibapi.wrapper import *
from ibapi.client import *
from ibapi.contract import *
from ibapi.order import *
from ibapi.contract import Contract
from ibapi.order import Order
from threading import Thread
import queue
import datetime
import time
import math
import argparse


class TestWrapper(EWrapper):

    # error handling methods
    def init_error(self):
        error_queue = queue.Queue()
        self.my_errors_queue = error_queue

    def is_error(self):
        error_exist = not self.my_errors_queue.empty()
        return error_exist

    def get_error(self, timeout=6):
        if self.is_error():
            try:
                return self.my_errors_queue.get(timeout=timeout)
            except queue.Empty:
                return None
        return None

    def error(self, id, errorCode, errorString):
        ## Overrides the native method
        errormessage = "IB returns an error with %d errorcode %d that says %s" % (id, errorCode, errorString)
        self.my_errors_queue.put(errormessage)
    
    # time handling methods
    def init_time(self):
        time_queue = queue.Queue()
        self.my_time_queue = time_queue
        return time_queue

    def currentTime(self, server_time):
        ## Overriden method
        self.my_time_queue.put(server_time)


# Below is the TestClient/EClient Class 

'''Here we will call our own methods, not overriding the api methods'''

class TestClient(EClient):

    def __init__(self, wrapper):
    ## Set up with a wrapper inside
        EClient.__init__(self, wrapper)

    def server_clock(self):
        print("Asking server for Unix time")
        # Creates a queue to store the time
        time_storage = self.wrapper.init_time()
        # Sets up a request for unix time from the Eclient
        self.reqCurrentTime()
        #Specifies a max wait time if there is no connection
        max_wait_time = 10
        try:
            requested_time = time_storage.get(timeout = max_wait_time)
        except queue.Empty:
            print("The queue was empty or max time reached")
            requested_time = None
        while self.wrapper.is_error():
            print("Error:")
            print(self.get_error(timeout=5))
        return requested_time


class TestApp(TestWrapper, TestClient):
    #Intializes our main classes 
    def __init__(self, ipaddress, portid, clientid):
        TestWrapper.__init__(self)
        TestClient.__init__(self, wrapper=self)

        #Connects to the server with the ipaddress, portid, and clientId specified in the program execution area
        self.connect(ipaddress, portid, clientid)
        self.nextorderId = None

        #Initializes the threading
        thread = Thread(target = self.run)
        thread.start()
        setattr(self, "_thread", thread)

        #Starts listening for errors 
        self.init_error()

        


def createContract(symbol: str) -> Contract:
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"
    return contract

def createOrder(action, quantity, stop, target, crash):
    # Fills out the order object 
    order1 = Order()    # Creates an order object from the import
    order1.action = action   # Sets the order action to buy
    order1.orderType = "MKT"    # Sets order type to market buy
    order1.transmit = True
    order1.totalQuantity = quantity   # Setting a static quantity of 10 
    return order1   # Returns the order object 

if __name__ == '__main__':

    argp = argparse.ArgumentParser()
    argp.add_argument("symbol", nargs='+', help="stock list to run the bot on")
    argp.add_argument( "-H","--host", type=str, default="127.0.0.1", help="host adress to connect to")
    args = argp.parse_args()

    contracts = []
    for s in args.symbol:
        contract = createContract(s)
        contracts.append(contract)
        print(contract.symbol)

    print("before start")
    # Specifies that we are on local host with port 7497 (paper trading port number)
    app = TestApp(args.host, 7496, 0)     
    # A printout to show the program began
    print("The program has begun")

    now = datetime.datetime.now()
    openTime=datetime.datetime(year=now.year, month=now.month, day=now.day, hour=8, minute=22)
    openTime=datetime.datetime.timestamp(openTime)
    #assigning the return from our clock method to a variable 
    requested_time = app.server_clock()
    while(requested_time < openTime):
        print("not yet")
        time.sleep(2)
        requested_time = app.server_clock()
    #printing the return from the server
    print("STARTED--> Now passing orders..." )
    # Optional disconnect. If keeping an open connection to the input don't disconnet
    # app.disconnect()


#!/usr/bin/env python
from ibapi.common import *
from ibapi.wrapper import *
from ibapi.client import *
from ibapi.contract import *
from ibapi.order import *
from ibapi.order import Order
from ibapi.order_condition import PriceCondition
from ibapi.order_condition import OrderCondition
from ibapi.order_condition import *
from ibapi import order_condition
from ibapi.contract import Contract
from threading import Thread
import queue
import datetime
import time
import math
import argparse


class Wrapper(EWrapper): 

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
    
    def init_time(self):
        time_queue = queue.Queue()
        self.my_time_queue = time_queue
        return time_queue

    def currentTime(self, server_time):
        ## Overriden method
        self.my_time_queue.put(server_time)

    #contract handling methods
    def init_contract(self):
        contract_queue=queue.Queue()
        self.my_contract_queue=contract_queue
        return contract_queue

    def contractDetails(self, reqId, contractDetails):
        self.my_contract_queue.put(contractDetails)

    #bar handling methods
    def init_bar(self):
        bar_queue = queue.Queue()
        self.my_bar_queue=bar_queue
        return bar_queue

    def historicalData(self, reqId, bar):
        ## Overriden method
        self.my_bar_queue.put(bar)

# Below is the TestClient/EClient Class 

'''Here we will call our own methods, not overriding the api methods'''

class Client(EClient):

    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
        self.request_id = 0

    def server_clock(self):
        print("Asking server for Unix time")
        time_storage = self.wrapper.init_time()
        self.reqCurrentTime()
        max_wait_time = 5
        try:
            requested_time = time_storage.get(timeout = max_wait_time)
        except queue.Empty:
            print("The queue was empty or max time reached")
            requested_time = None
        while self.wrapper.is_error():
            print("Error:")
            print(self.get_error(timeout=5))
        return requested_time

    def getContractDetails(self, contract):
        print("Asking for contracts details")
        contract_storage = self.wrapper.init_contract()
        self.reqContractDetails(self.request_id, contract)
        self.request_id+=1
        max_wait_time = 5
        try:
            contract_details= contract_storage.get(timeout = max_wait_time)
        except queue.Empty:
            print("The queue was empty or max time reached")
            contract_details = None
        while self.wrapper.is_error():
            print("Error:")
            print(self.get_error(timeout=5))
        return contract_details


    def getOpenBar(self, contract):
        print("Asking the first 10 min candle")
        bar_storage = self.wrapper.init_bar()
        end_date=datetime.datetime(year=now.year, month=now.month, day=now.day, hour=15, minute=40)
        end_date=end_date.strftime("%Y%m%d %H:%M:%S")
        self.reqHistoricalData(self.request_id, contract, end_date, "300 S", "10 mins", "TRADES", 1, 1, False, [])
        self.request_id+=1
        max_wait_time = 5
        try:
            requested_bar = bar_storage.get(timeout = max_wait_time)
        except queue.Empty:
            print("The queue was empty or max time reached")
            requested_bar = None
        while self.wrapper.is_error():
            print("Error:")
            print(self.get_error(timeout=5))
        return requested_bar


class Bot(Wrapper, Client):
    #Intializes our main classes 
    def __init__(self, ipaddress, portid, clientid):
        Wrapper.__init__(self)
        Client.__init__(self, wrapper=self)
        
        #Connects to the server with the ipaddress, portid, and clientId specified in the program execution area
        self.connect(ipaddress, portid, clientid)
        
        #Initializes the threading
        thread = Thread(target = self.run)
        thread.start()
        setattr(self, "_thread", thread)

        #Starts listening for errors 
        self.init_error()

# class OrdersList:

#     def __init__(self):
#         self.LongOrdersMap={}
#         self.ShortOrdersMap={}

#     def add_order(self, order: Order, symbol: str):
#         if(order.action == "BUY"):
#             self.LongOrdersMap[symbol]=order.orderId
#         else:
#             self.ShortOrdersMap[symbol]=order.orderId

#     def getOrderId(self, symbol: str, direction: str):
#         if(direction == "BUY"):
#             return self.LongOrdersMap[symbol]
#         else:
#             return self.ShortOrdersMap[symbol]
    

def createContract(symbol: str) -> Contract:
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"
    return contract

def createConditionalOrder(contract, action, quantity, target, stop, start) -> Order:

    priceCondition = order_condition.Create(OrderCondition.Price)
    priceCondition.conId = contract.conId
    priceCondition.exchange = contract.exchange
    priceCondition.isMore = (action=='BUY')
    priceCondition.triggerMethod = PriceCondition.TriggerMethodEnum.Last
    priceCondition.price = start

    orderMain = Order()
    orderMain.orderId=app.request_id
    app.request_id += 1
    orderMain.action = action  
    orderMain.orderType = "MTL"    
    orderMain.transmit = False
    orderMain.totalQuantity = quantity
    orderMain.conditions.append(priceCondition)
    orderMain.ocaGroup=contract.symbol
    orderMain.ocaType=1

    takeProfit = Order()
    takeProfit.orderId = app.request_id
    app.request_id += 1
    takeProfit.action = "SELL" if action == "BUY" else "BUY"
    takeProfit.orderType = "LMT"
    takeProfit.totalQuantity = quantity
    takeProfit.lmtPrice = target
    takeProfit.parentId = orderMain.orderId
    takeProfit.transmit = False

    stopLoss = Order()
    stopLoss.orderId = app.request_id
    app.request_id += 1
    stopLoss.action = "SELL" if action == "BUY" else "BUY"
    stopLoss.orderType = "STP"
    stopLoss.auxPrice = stop
    stopLoss.totalQuantity = quantity
    stopLoss.parentId = orderMain.orderId
    stopLoss.transmit = True

    return [orderMain, takeProfit, stopLoss]


if __name__ == '__main__':

    MAX_RISK = 100

    argp = argparse.ArgumentParser()
    argp.add_argument("symbol", nargs='+', help="stock list to run the bot on")
    argp.add_argument( "-H","--host", type=str, default="127.0.0.1", help="host adress to connect to")
    argp.add_argument( "-p","--port", type=int, default="7497", help="port to connect to")
    args = argp.parse_args()

    contracts = []
    for s in args.symbol:
        contract = createContract(s)
        contracts.append(contract)
        print(contract.symbol)
    try:
        print("before start")
        app = Bot(args.host, args.port, 0)  
        print("The program has begun")
        print("Cancelling all orders...")
        app.reqGlobalCancel()
        print("All orders have been cancelled")
    
        app.request_id=0

        now = datetime.datetime.now()
        openTime=datetime.datetime(year=now.year, month=now.month, day=now.day, hour=15, minute=40)
        openTime=datetime.datetime.timestamp(openTime)
        #assigning the return from our clock method to a variable
        print("requesting server time...")
        requested_time = app.server_clock()
        print(requested_time)
        print("server time requested, waiting for market open...")
        while(requested_time < openTime):
            print("not yet")
            time.sleep(2)
            requested_time = app.server_clock()
        #printing the return from the server
        print("STARTED--> Now firing orders..." )
        #recuperer la valeur de la barre en 5 min
        for c in contracts:

            #contract infos
            contractDetails=app.getContractDetails(c)
            contract=contractDetails.contract
        
            print("ConId=", contract.conId)
            print("Symbol=", contract.symbol)

            #bar infos
            bar = app.getOpenBar(contract)
          
            body= round(abs(bar.close - bar.open), 2)
            range= round( (bar.high - bar.low), 2)
            rangeUp= round((bar.high - max(bar.close, bar.open)), 2)
            rangeDown= round((min(bar.close, bar.open) - bar.low), 2)

            print("High=", bar.high)
            print("Low=", bar.low)
            print("Open=", bar.open)
            print("Body=", body)
            print("Range=", range)
            print("RangeUp=", rangeUp)
            print("RangeDown=", rangeDown)

            #order infos
            move=round(max(body, rangeUp),2)
            quantity= MAX_RISK // move
            target=round((bar.high + move), 2)
            stop=round((bar.high - move), 2)
            print("Quantity is= ", quantity)
            print("Start is= ", bar.high)
            print("Direction is=", "LONG")
            print("Target is=", target)
            print("Stop is=", stop)
            orders=createConditionalOrder(contract, "BUY", quantity, target, stop, bar.high)
            for order in orders:
                app.placeOrder(order.orderId, contract, order)

            move=round(max(body, rangeDown), 2)
            target=round((bar.low - move), 2)
            stop=round((bar.low + move), 2)
            print("Quantity is= ", quantity)
            print("Start is= ", bar.low)
            print("Direction is=", "SHORT")
            print("Target is=", target)
            print("Stop is=", stop)
            orders=createConditionalOrder(contract, "SELL", quantity, target, stop, bar.low)
            for order in orders:
                app.placeOrder(order.orderId, contract, order)

    except Exception as err:
        print("Shit happens: ", type(err).__name__)
        print(err)
    finally:
        app.disconnect()
    
    ####TODO#####
    #gerer auto-cancel
    #mettre en place des logs
    #decoupler le code
    #scheduler le bot
    #mettre en place le crashing ( conditional order ou modifier le stop, ou nouveau stop et cancel l'ancien stop )
    #je peux reussir en conditionnal order avec un oca group sur le stop
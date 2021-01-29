#!/usr/bin/env python

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta

from typing import List, Optional
from collections import defaultdict
from dateutil.parser import parse

import numpy as np
import pandas as pd

from ibapi import wrapper 
from ibapi.common import TickerId, BarData
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.utils import iswrapper

ContractList = List[Contract]


def make_contract(symbol: str) -> Contract:
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"
    return contract

def main():

    argp = argparse.ArgumentParser()
    argp.add_argument("symbol", nargs='+', help="stock list to run the bot on")
    args = argp.parse_args()

    contracts = []
    for s in args.symbol:
        contract = make_contract(s)
        contracts.append(contract)
        print(contract)
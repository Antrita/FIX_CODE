# Simple FIX Simulator with Python and QuickFIX

This repository contains a simple implementation of a FIX (Financial Information eXchange) simulator using Python and the QuickFIX library. The simulator is designed to demonstrate the basic functionality of a market maker application.

## Introduction

The provided code is a basic market maker application that can handle various FIX messages such as New Order Single, Order Cancel Request, and Market Data Request. It simulates the behavior of a market maker by sending back appropriate responses and updating market data.

## Getting Started

1. Install Python 3.9 (https://www.python.org/downloads/)
2. Install QuickFIX (https://github.com/quickfix/quickfix) by following the installation instructions provided in the QuickFIX repository.
3. Clone this repository or download the code.
4. Create a `Server.cfg` and `client.cfg` configuration file in the root directory of the project. 
5. Run the `market_maker.py` and `client.py` script using Python:

```bash
python market_maker.py
python client.py
```

## Tools and Libraries

- Python 3.9: The python version used for the implementation.
- QuickFIX: A C++ library for FIX protocol development and message parsing.
- Make sure to download '[FIX44.xml](https://github.com/quickfix/quickfix/blob/master/spec/FIX44.xml)' and add it to your working directory.

## Menu

A simple menu is displayed after the FIX application has started. You can use this menu to perform various actions:

- 1 -> Place Buy Order
- 2 -> Place Sell Order
- 3 -> Subscribe to Market Data
- 4 -> Cancel Market Data Subscription
- 5 -> Order Cancel Request
- 6 -> Order Status Request
- logout -> Logout and Exit
- d -> Start debugger

Enter the corresponding number or action to perform the desired operation.


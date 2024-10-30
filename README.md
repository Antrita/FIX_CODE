
# FIX Market Simulator with Python and QuickFIX

This repository contains a simple implementation of a FIX (Financial Information eXchange) simulator using Python and the QuickFIX library. The simulator is designed to demonstrate the basic functionality of a market maker application.

## Introduction

The provided code is a basic market maker application that can handle various FIX messages such as New Order Single, Order Cancel Request, and Market Data Request. It simulates the behavior of a market maker by sending back appropriate responses and updating market data.

## Getting Started

1. Install Python 3.9 (https://www.python.org/downloads/)
2. Install QuickFIX (https://github.com/quickfix/quickfix) by following the installation instructions provided in the QuickFIX repository.
3. Clone this repository or download the code.
4. Create a `Server.cfg` and `client.cfg` configuration file in the root directory of the project.
5. Run the `market_maker.py` and `client.py` script using Python to execute the Command Line version:

```bash
python market_maker.py
python client.py
```
6.Run the main.py to work with the GUI version:
```bash
python main.py
```
## Tools and Libraries

- Python 3.9: The python version used for the implementation.
- QuickFIX: A C++ library for FIX protocol development and message parsing.
- Make sure to download '[FIX44.xml](https://github.com/quickfix/quickfix/blob/master/spec/FIX44.xml)' and add it to your working directory.
## Order Types supported
Along with the regular market orders placed by users in the format: [side] [USD/BRL] [Qty] [Price] , This application now supports three other Market order types- Stop Orders, Limit Orders and Stop-Limit Orders.



## CLI Menu

A simple menu is displayed after the FIX application has started. You can use this menu to perform various actions in the CLI version (Market Maker and Client):

- buy -> Place Buy Order
- sell -> Place Sell Order
- subscribe -> Subscribe to Market Data
- unsubscribe -> Cancel Market Data Subscription
- cancel -> Order Cancel Request
- status -> Order Status Request
- quit -> Logout and Exit

## GUI Menu
### Users can now place orders using commands in the form:
 [side-buy/sell] [USD/BRL] [qty] [amount] 



### Conditions for stop, limit, stop_limit  execution
1. Stop order: Stop price must be provided and it must be greater than or equal to the current market price.
2. Limit order: Price must be provided and it must be less than or equal to the current market price.
3. Stop-limit order: Stop price and price must be provided and it must be less than or equal to the current market price and greater than or equal to the stop price.
4.Market orders: users can place orders normally.
Buying and selling rules for stop, limit and stop_limit orders:
1.buying in stop orders: Stop price must be provided and it must be greater than or equal to  current market price provided first.
2. selling in stop orders: Stop price must be provided and it must be less than or equal to the current market price provided first.
3. buying in limit orders: Price must be provided and it must be less than or equal to the current market price provided first.
4. selling in limit orders: Price must be provided and it must be greater than or equal to the current market price provided first.
5. buying in stop_limit orders: Stop price and price must be provided and it must be less than or equal to the current market price provided first, and greater than or equal to the stop price provided.
6. selling in stop_limit orders: Stop price and price must be provided and it must be greater than or equal to the current market price provided first, and less than or equal to the stop price provided.
7. 
## EXAMPLES

### Users can now enter commands like:
( For buy/sell, price can also be added seperately in the CLI Version for regular market orders)

- buy USD/BRL 100  1.10  
- sell USD/BRL 100 limit 1.10 
- buy USD/BRL 100 stop 1.05 1.00
- buy USD/BRL 100 stop_limit 2.4 2.3 [stop price > limit price for buy]
- sell USD/BRL 100 stop_limit 2.3 2.4[stop price < limit price for sell]

Enter the corresponding command or action to perform the desired operation.


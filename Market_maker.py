import sys
import quickfix as fix
import quickfix44 as fix44
import random
import threading
import time
from datetime import datetime

class CustomApplication:
    def format_and_print_message(self, prefix, message):
        try:
            formatted_message = message.toString().replace(chr(1), ' | ')
            print(f"{prefix}: {formatted_message}")
        except Exception as e:
            print(f"Error formatting message: {e}")
            print(f"{prefix}: {message}")

def gen_order_id():
    return str(random.randint(100000, 999999))

class MarketMaker(fix.Application, CustomApplication):
    def __init__(self):
            super().__init__()
            self.session_id = None
            self.symbols = ["USD/BRL"]
            self.prices = {symbol: random.uniform(4.5, 5.5) for symbol in self.symbols}
            self.subscriptions = set()
            self.orders = {}
            self.last_heartbeat_time = None #init heartbeat time

    def onCreate(self, session_id):
        self.session_id = session_id
        print(f"Session created - {session_id}")

    def onLogon(self, session_id):
        self.session_id = session_id
        print(f"Logon - {session_id}")
        print("Market Maker logged on and ready to receive requests.")

    def onLogout(self, session_id):
        print(f"Logout - {session_id}")

    def toAdmin(self, message, session_id):
        msgType = fix.MsgType()
        message.getHeader().getField(msgType)

        if msgType.getValue() == fix.MsgType_Heartbeat:
            print("Sending Heartbeat")

        self.format_and_print_message("Sending admin", message)
    def fromAdmin(self, message, session_id):
        msgType = fix.MsgType()
        message.getHeader().getField(msgType)

        if msgType.getValue() == fix.MsgType_Heartbeat:
            current_time = datetime.now()
            if self.last_heartbeat_time:
                interval = (current_time - self.last_heartbeat_time).total_seconds()
                print(f"Heartbeat received. Interval: {interval:.2f} seconds")
            self.last_heartbeat_time = current_time

        self.format_and_print_message("Received admin", message)

    def toApp(self, message, session_id):
        self.format_and_print_message("Sending app", message)

    def fromApp(self, message, session_id):
        try:
            # Log the raw message first
            self.format_and_print_message("Received raw app message", message)

            msgType = fix.MsgType()
            if message.getHeader().isSetField(msgType):
                message.getHeader().getField(msgType)
            else:
                print("Message type not found in the message")
                return

            # Handle different message types
            if msgType.getValue() == fix.MsgType_NewOrderSingle:
                self.handle_new_order(message, session_id)
            elif msgType.getValue() == fix.MsgType_OrderCancelRequest:
                self.handle_cancel_request(message, session_id)
            elif msgType.getValue() == fix.MsgType_MarketDataRequest:
                self.handle_market_data_request(message, session_id)
            elif msgType.getValue() == fix.MsgType_OrderStatusRequest:
                self.handle_order_status_request(message, session_id)
            else:
                print(f"Unhandled message type: {msgType.getValue()}")

            # Log the processed message
            #self.format_and_print_message("Processed app message", message)

        except fix.FieldNotFound as e:
            print(f"Warning: Field not found in message - {e}")
            print(f"Message content: {message}")
        except Exception as e:
            print(f"Error processing message: {e}")

    def handle_new_order(self, message, session_id):
        order = fix44.ExecutionReport()
        clOrdID = fix.ClOrdID()
        symbol = fix.Symbol()
        side = fix.Side()
        orderQty = fix.OrderQty()

        message.getField(clOrdID)
        message.getField(symbol)
        message.getField(side)
        message.getField(orderQty)

        orderID = gen_order_id()
        self.orders[orderID] = {
            'clOrdID': clOrdID.getValue(),
            'symbol': symbol.getValue(),
            'side': side.getValue(),
            'orderQty': orderQty.getValue(),
            'leavesQty': orderQty.getValue(),
            'cumQty': 0,
            'avgPx': 0
        }

        order.setField(fix.OrderID(orderID))
        order.setField(fix.ExecID(gen_order_id()))
        order.setField(fix.ExecType(fix.ExecType_NEW))
        order.setField(fix.OrdStatus(fix.OrdStatus_NEW))
        order.setField(clOrdID)
        order.setField(symbol)
        order.setField(side)
        order.setField(orderQty)
        order.setField(fix.LeavesQty(orderQty.getValue()))  # Add LeavesQty
        order.setField(fix.CumQty(0))
        order.setField(fix.AvgPx(0))

        fix.Session.sendToTarget(order, session_id)

    def handle_cancel_request(self, message, session_id):
        origClOrdID = fix.OrigClOrdID()
        message.getField(origClOrdID)

        # Find the order
        order = next((order for order in self.orders.values() if order['clOrdID'] == origClOrdID.getValue()), None)

        if order:
            orderID = next(id for id, o in self.orders.items() if o == order)
            cancel = fix44.ExecutionReport()
            cancel.setField(fix.OrderID(orderID))
            cancel.setField(fix.ExecID(gen_order_id()))
            cancel.setField(fix.ExecType(fix.ExecType_CANCELED))
            cancel.setField(fix.OrdStatus(fix.OrdStatus_CANCELED))
            cancel.setField(origClOrdID)
            cancel.setField(fix.Symbol(order['symbol']))
            cancel.setField(fix.Side(order['side']))
            cancel.setField(fix.LeavesQty(0))
            cancel.setField(fix.CumQty(order['cumQty']))
            cancel.setField(fix.AvgPx(order['avgPx']))

            del self.orders[orderID]
            fix.Session.sendToTarget(cancel, session_id)
        else:
            # Order not found, send reject
            reject = fix44.OrderCancelReject()
            reject.setField(fix.OrderID("NONE"))
            reject.setField(fix.ClOrdID(message.getField(fix.ClOrdID())))
            reject.setField(origClOrdID)
            reject.setField(fix.OrdStatus(fix.OrdStatus_REJECTED))
            reject.setField(fix.CxlRejResponseTo(fix.CxlRejResponseTo_ORDER_CANCEL_REQUEST))
            reject.setField(fix.CxlRejReason(fix.CxlRejReason_UNKNOWN_ORDER))

            fix.Session.sendToTarget(reject, session_id)

    def handle_market_data_request(self, message, session_id):
        try:
            # Extract MDReqID
            mdReqID = fix.MDReqID()
            message.getField(mdReqID)

            # Extract SubscriptionRequestType
            subscriptionRequestType = fix.SubscriptionRequestType()
            message.getField(subscriptionRequestType)

            # Extract Symbol
            symbol = fix.Symbol()
            message.getField(symbol)

            # Check for NoMDEntryTypes field
            noMDEntryTypes = fix.NoMDEntryTypes()
            if message.isSetField(noMDEntryTypes):
                message.getField(noMDEntryTypes)
                entryTypes = []
                for i in range(noMDEntryTypes.getValue()):
                    group = fix44.MarketDataRequest().NoMDEntryTypes()
                    message.getGroup(i + 1, group)
                    mdEntryType = fix.MDEntryType()
                    group.getField(mdEntryType)
                    entryTypes.append(mdEntryType.getValue())

                if fix.MDEntryType_BID not in entryTypes or fix.MDEntryType_OFFER not in entryTypes:
                    print("Warning: Bid or Offer entry type not found in the request")
            else:
                print("Warning: NoMDEntryTypes field not found in the request")

            if subscriptionRequestType.getValue() == fix.SubscriptionRequestType_SNAPSHOT_PLUS_UPDATES:
                self.subscriptions.add((mdReqID.getValue(), symbol.getValue()))
                self.send_market_data(mdReqID.getValue(), symbol.getValue(), session_id)
            elif subscriptionRequestType.getValue() == fix.SubscriptionRequestType_DISABLE_PREVIOUS_SNAPSHOT_PLUS_UPDATE_REQUEST:
                self.subscriptions.discard((mdReqID.getValue(), symbol.getValue()))

            print(f"Processed Market Data Request for {symbol.getValue()} with MDReqID: {mdReqID.getValue()}")

        except fix.FieldNotFound as e:
            print(f"Field not found in message: {e}")
        except Exception as e:
            print(f"Error processing Market Data Request: {e}")
    '''def handle_market_data_request(self, message, session_id):
        try:
            # Extract MDReqID, Symbol, and SubscriptionRequestType from the incoming message
            mdReqID = fix.MDReqID()
            subscriptionRequestType = fix.SubscriptionRequestType()
            symbol = fix.Symbol()

            # Ensure the required fields are in the message
            message.getField(mdReqID)
            message.getField(subscriptionRequestType)
            message.getField(symbol)

            # Print out the received market data request
            print(f"Received Market Data Request for MDReqID: {mdReqID.getValue()}, Symbol: {symbol.getValue()}")

            # Fetch market data (prices) based on the symbol from the on_market_data method
            bid_price, offer_price = self.on_market_data(message)

            # Construct the market data message to send back to the client
            if bid_price != "N/A" and offer_price != "N/A":
                # Construct the FIX message in the required format
                message_out = fix.Message()
                header = message_out.getHeader()

                # Set the basic FIX fields in the header
                header.setField(fix.BeginString("FIX.4.4"))
                header.setField(fix.MsgType("W"))  # Market Data Snapshot Full Refresh
                header.setField(fix.SenderCompID("MARKET_MAKER"))
                header.setField(fix.TargetCompID("CLIENT"))
                header.setField(fix.MsgSeqNum(1))  # Sequence number (can be adjusted)
                header.setField(fix.SendingTime("20241008-13:19:00.000"))  # Adjust as needed

                # Set MDReqID and Symbol
                message_out.setField(fix.MDReqID(mdReqID.getValue()))
                message_out.setField(fix.Symbol(symbol.getValue()))

                # Create the market data entries for Bid and Offer
                message_out.setField(fix.MDEntryType(fix.MDEntryType_BID))  # Entry type: BID
                message_out.setField(fix.MDEntryPx(bid_price))  # Bid Price
                message_out.setField(fix.MDEntrySize(100))  # Arbitrary size (adjust as needed)

                message_out.setField(fix.MDEntryType(fix.MDEntryType_OFFER))  # Entry type: OFFER
                message_out.setField(fix.MDEntryPx(offer_price))  # Offer Price
                message_out.setField(fix.MDEntrySize(100))  # Arbitrary size (adjust as needed)

                # Additional fields as per your format
                message_out.setField(fix.MDEntryDate("20241008"))  # Date for the entries
                message_out.setField(fix.MDEntryTime("13:19:00"))  # Time of the entries

                # Hardcoded values for the other fields, adjust as needed
                message_out.setField(fix.MDEntrySize(100))
                message_out.setField(fix.MDEntryDate("20241008"))
                message_out.setField(fix.MDEntryTime("13:19:00"))
                message_out.setField(fix.MDEntrySize(100))
                message_out.setField(fix.MDEntryDate("20241008"))
                message_out.setField(fix.MDEntryTime("13:19:00"))

                # Calculate and add the CheckSum (you may want to recalculate checksum in production)
                message_out.setField(fix.CheckSum(str(fix.CalculateChecksum(message_out))))

                # Send the constructed message to the client
                fix.Session.sendToTarget(message_out, session_id)
                print(f"Sent Market Data Response: {message_out}")

            else:
                print("Error: Market data not found or invalid prices.")

        except fix.FieldNotFound as e:
            print(f"Warning: Field not found in message - {e}")
        except Exception as e:
            print(f"Error processing market data request: {e}")'''

    def send_market_data(self, md_req_id, symbol, session_id):
        message = fix.Message()
        header = message.getHeader()

        header.setField(fix.BeginString("FIX.4.4"))
        header.setField(fix.MsgType("W"))  # Market Data Snapshot Full Refresh
        header.setField(fix.SenderCompID("MARKET_MAKER"))
        header.setField(fix.TargetCompID("CLIENT"))

        # Set sending time
        header.setField(fix.SendingTime(datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]))

        message.setField(fix.Symbol(symbol))
        message.setField(fix.MDReqID(md_req_id))

        bid_price = round(self.prices[symbol] - 0.01, 4)
        ask_price = round(self.prices[symbol] + 0.01, 4)

        # NoMDEntries
        noMDEntries = fix.NoMDEntries(2)
        message.setField(noMDEntries)

        # Add bid
        group = fix44.MarketDataSnapshotFullRefresh().NoMDEntries()
        group.setField(fix.MDEntryType(fix.MDEntryType_BID))
        group.setField(fix.MDEntryPx(bid_price))
        group.setField(fix.MDEntrySize(100000))
        group.setField(fix.MDEntryDate(datetime.utcnow().strftime("%Y%m%d")))
        group.setField(fix.MDEntryTime(datetime.utcnow().strftime("%H:%M:%S")))
        message.addGroup(group)

        # Add offer
        group = fix44.MarketDataSnapshotFullRefresh().NoMDEntries()
        group.setField(fix.MDEntryType(fix.MDEntryType_OFFER))
        group.setField(fix.MDEntryPx(ask_price))
        group.setField(fix.MDEntrySize(100000))
        group.setField(fix.MDEntryDate(datetime.utcnow().strftime("%Y%m%d")))
        group.setField(fix.MDEntryTime(datetime.utcnow().strftime("%H:%M:%S")))
        message.addGroup(group)

        fix.Session.sendToTarget(message, session_id)
    def handle_order_status_request(self, message, session_id):
        clOrdID = fix.ClOrdID()
        message.getField(clOrdID)

        # Find the order
        order = next((order for order in self.orders.values() if order['clOrdID'] == clOrdID.getValue()), None)

        if order:
            orderID = next(id for id, o in self.orders.items() if o == order)
            status = fix44.ExecutionReport()
            status.setField(fix.OrderID(orderID))
            status.setField(fix.ExecID(gen_order_id()))
            status.setField(fix.ExecType(fix.ExecType_ORDER_STATUS))
            status.setField(fix.OrdStatus(fix.OrdStatus_NEW))  # Assuming all orders are still NEW
            status.setField(clOrdID)
            status.setField(fix.Symbol(order['symbol']))
            status.setField(fix.Side(order['side']))
            status.setField(fix.OrderQty(order['orderQty']))
            status.setField(fix.LeavesQty(order['leavesQty']))
            status.setField(fix.CumQty(order['cumQty']))
            status.setField(fix.AvgPx(order['avgPx']))

            fix.Session.sendToTarget(status, session_id)
        else:
            # Order not found, send reject
            reject = fix44.BusinessMessageReject()
            reject.setField(fix.RefMsgType(fix.MsgType_OrderStatusRequest))
            reject.setField(fix.BusinessRejectReason(fix.BusinessRejectReason_UNKNOWN_ID))
            reject.setField(fix.Text("Unknown order"))

            fix.Session.sendToTarget(reject, session_id)



        # Send the message
        self.send_to_client(message, session_id)
    def update_prices(self):
        while True:
            for symbol in self.symbols:
                self.prices[symbol] += random.uniform(-0.05, 0.05)
                self.prices[symbol] = max(4.0, min(self.prices[symbol], 6.0))

            for md_req_id, symbol in self.subscriptions:
                self.send_market_data(md_req_id, symbol, self.session_id)

            time.sleep(6)  # Changed to 6 seconds as requested

    def start(self):
        try:
            settings = fix.SessionSettings("Server.cfg")
            store_factory = fix.FileStoreFactory(settings)
            log_factory = fix.ScreenLogFactory(settings)
            acceptor = fix.SocketAcceptor(self, store_factory, settings, log_factory)

            acceptor.start()

            # Start the price updating thread
            threading.Thread(target=self.update_prices, daemon=True).start()

            print("Market Maker started.")
            while True:
                time.sleep(1)
        except (fix.ConfigError, fix.RuntimeError) as e:
            print(f"Error starting market maker: {e}")
            sys.exit(1)

def main():
    try:
        application = MarketMaker()
        application.start()
    except KeyboardInterrupt:
        print("Market Maker stopped.")
    except Exception as e:
        print(f"Error in Market Maker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
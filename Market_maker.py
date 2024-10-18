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
        self.symbol_value = "USD/BRL"
        self.prices = {self.symbol_value: random.uniform(4.5, 5.5)}
        self.subscriptions = set()
        self.orders = {}
        self.last_heartbeat_time = None
        self.is_running = True

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
            self.format_and_print_message("Received raw app message", message)

            msgType = fix.MsgType()
            if message.getHeader().isSetField(msgType):
                message.getHeader().getField(msgType)
            else:
                print("Message type not found in the message")
                return

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

        except fix.FieldNotFound as e:
            print(f"Warning: Field not found in message - {e}")
            print(f"Message content: {message}")
        except Exception as e:
            print(f"Error processing message: {e}")

    def handle_new_order(self, message, session_id):
        order = fix44.ExecutionReport()
        clOrdID = fix.ClOrdID()
        side = fix.Side()
        orderQty = fix.OrderQty()

        message.getField(clOrdID)
        message.getField(side)
        message.getField(orderQty)

        orderID = gen_order_id()
        self.orders[orderID] = {
            'clOrdID': clOrdID.getValue(),
            'symbol': self.symbol_value,
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
        order.setField(fix.Symbol(self.symbol_value))
        order.setField(side)
        order.setField(orderQty)
        order.setField(fix.LeavesQty(orderQty.getValue()))
        order.setField(fix.CumQty(0))
        order.setField(fix.AvgPx(0))

        fix.Session.sendToTarget(order, session_id)

    def handle_cancel_request(self, message, session_id):
        origClOrdID = fix.OrigClOrdID()
        message.getField(origClOrdID)

        order = next((order for order in self.orders.values() if order['clOrdID'] == origClOrdID.getValue()), None)

        if order:
            orderID = next(id for id, o in self.orders.items() if o == order)
            cancel = fix44.ExecutionReport()
            cancel.setField(fix.OrderID(orderID))
            cancel.setField(fix.ExecID(gen_order_id()))
            cancel.setField(fix.ExecType(fix.ExecType_CANCELED))
            cancel.setField(fix.OrdStatus(fix.OrdStatus_CANCELED))
            cancel.setField(origClOrdID)
            cancel.setField(fix.Symbol(self.symbol_value))
            cancel.setField(fix.Side(order['side']))
            cancel.setField(fix.LeavesQty(0))
            cancel.setField(fix.CumQty(order['cumQty']))
            cancel.setField(fix.AvgPx(order['avgPx']))

            del self.orders[orderID]
            fix.Session.sendToTarget(cancel, session_id)
        else:
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
            md_req_id = fix.MDReqID()
            subscription_type = fix.SubscriptionRequestType()

            message.getField(md_req_id)
            message.getField(subscription_type)

            print(f"Received market data request: MDReqID={md_req_id.getValue()}, "
                  f"SubscriptionType={subscription_type.getValue()}, "
                  f"Symbol={self.symbol_value}")

            if subscription_type.getValue() == fix.SubscriptionRequestType_SNAPSHOT_PLUS_UPDATES:
                self.subscriptions.add((md_req_id.getValue(), self.symbol_value))
                print(f"Added subscription for {self.symbol_value} with MDReqID {md_req_id.getValue()}")
                self.send_market_data(md_req_id.getValue(), session_id, self.symbol_value)
            elif subscription_type.getValue() == fix.SubscriptionRequestType_DISABLE_PREVIOUS_SNAPSHOT_PLUS_UPDATE_REQUEST:
                self.subscriptions = {sub for sub in self.subscriptions if sub[1] != self.symbol_value}
                print(f"Removed subscription for {self.symbol_value}")
            else:
                print(f"Unsupported subscription type: {subscription_type.getValue()}")

        except fix.FieldNotFound as e:
            print(f"Error processing market data request: {e}")

    def send_market_data(self, md_req_id, session_id, symbol):
        if symbol not in self.prices:
            print(f"Symbol {symbol} not found in price data")
            return

        snapshot = fix.Message()
        snapshot.getHeader().setField(fix.MsgType(fix.MsgType_MarketDataSnapshotFullRefresh))
        snapshot.setField(fix.MDReqID(md_req_id))
        snapshot.setField(fix.Symbol(symbol))

        group = fix44.MarketDataSnapshotFullRefresh().NoMDEntries()
        group.setField(fix.MDEntryType(fix.MDEntryType_BID))
        group.setField(fix.MDEntryPx(self.prices[symbol] - 0.01))
        group.setField(fix.MDEntrySize(100))
        snapshot.addGroup(group)

        group.setField(fix.MDEntryType(fix.MDEntryType_OFFER))
        group.setField(fix.MDEntryPx(self.prices[symbol] + 0.01))
        group.setField(fix.MDEntrySize(100))
        snapshot.addGroup(group)

        fix.Session.sendToTarget(snapshot, session_id)
        print(f"Sent market data for {symbol}: Bid={self.prices[symbol] - 0.01}, Offer={self.prices[symbol] + 0.01}")

    def handle_order_status_request(self, message, session_id):
        clOrdID = fix.ClOrdID()
        message.getField(clOrdID)

        order = next((order for order in self.orders.values() if order['clOrdID'] == clOrdID.getValue()), None)

        if order:
            orderID = next(id for id, o in self.orders.items() if o == order)
            status = fix44.ExecutionReport()
            status.setField(fix.OrderID(orderID))
            status.setField(fix.ExecID(gen_order_id()))
            status.setField(fix.ExecType(fix.ExecType_ORDER_STATUS))
            status.setField(fix.OrdStatus(fix.OrdStatus_NEW))
            status.setField(clOrdID)
            status.setField(fix.Symbol(self.symbol_value))
            status.setField(fix.Side(order['side']))
            status.setField(fix.OrderQty(order['orderQty']))
            status.setField(fix.LeavesQty(order['leavesQty']))
            status.setField(fix.CumQty(order['cumQty']))
            status.setField(fix.AvgPx(order['avgPx']))

            fix.Session.sendToTarget(status, session_id)
        else:
            reject = fix44.BusinessMessageReject()
            reject.setField(fix.RefMsgType(fix.MsgType_OrderStatusRequest))
            reject.setField(fix.BusinessRejectReason(fix.BusinessRejectReason_UNKNOWN_ID))
            reject.setField(fix.Text("Unknown order"))

            fix.Session.sendToTarget(reject, session_id)

    def update_prices(self):
        while self.is_running:
            try:
                self.prices[self.symbol_value] += random.uniform(-0.05, 0.05)
                self.prices[self.symbol_value] = max(4.0, min(self.prices[self.symbol_value], 6.0))

                for md_req_id, symbol in list(self.subscriptions):
                    if symbol == self.symbol_value and self.session_id:
                        try:
                            self.send_market_data(md_req_id, self.session_id, self.symbol_value)
                        except fix.SessionNotFound:
                            print(f"Session {self.session_id} not found. Removing subscription for {self.symbol_value}")
                            self.subscriptions.remove((md_req_id, self.symbol_value))
                        except Exception as e:
                            print(f"Error sending market data for {self.symbol_value}: {e}")

                time.sleep(10)
            except Exception as e:
                print(f"Error in update_prices: {e}")
                time.sleep(6)

    def start(self):
        try:
            settings = fix.SessionSettings("Server.cfg")
            store_factory = fix.FileStoreFactory(settings)
            log_factory = fix.ScreenLogFactory(settings)
            acceptor = fix.SocketAcceptor(self, store_factory, settings, log_factory)

            acceptor.start()

            threading.Thread(target=self.update_prices, daemon=True).start()

            print("Market Maker started.")
            while self.is_running:
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
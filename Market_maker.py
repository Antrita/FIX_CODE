import sys
import quickfix as fix
import quickfix44 as fix44
import random
import threading
import time

def gen_order_id():
    return str(random.randint(100000, 999999))

class MarketMaker(fix.Application):
    def __init__(self):
        super().__init__()
        self.session_id = None
        self.symbols = ["USD/BRL"]
        self.prices = {symbol: random.uniform(4.5, 5.5) for symbol in self.symbols}
        self.subscriptions = set()

    def onCreate(self, session_id):
        self.session_id = session_id
        print(f"Session created - {session_id}")

    def onLogon(self, session_id):
        print(f"Logon - {session_id}")

    def onLogout(self, session_id):
        print(f"Logout - {session_id}")

    def toAdmin(self, message, session_id):
        self.format_and_print_message("Sending admin", message)

    def fromAdmin(self, message, session_id):
        self.format_and_print_message("Received admin", message)

    def toApp(self, message, session_id):
        self.format_and_print_message("Sending app", message)

    def fromApp(self, message, session_id):
        self.format_and_print_message("Received app", message)
        msgType = fix.MsgType()
        message.getHeader().getField(msgType)

        if msgType.getValue() == fix.MsgType_NewOrderSingle:
            self.handle_new_order(message, session_id)
        elif msgType.getValue() == fix.MsgType_OrderCancelRequest:
            self.handle_cancel_request(message, session_id)
        elif msgType.getValue() == fix.MsgType_MarketDataRequest:
            self.handle_market_data_request(message, session_id)
        elif msgType.getValue() == fix.MsgType_OrderStatusRequest:
            self.handle_order_status_request(message, session_id)

    def format_and_print_message(self, prefix, message):
        formatted_message = message.toString().replace(chr(1), ' | ')
        print(f"{prefix}: {formatted_message}")

    def handle_new_order(self, message, session_id):
        order = fix44.ExecutionReport()
        order.setField(fix.OrderID(gen_order_id()))
        order.setField(fix.ExecID(gen_order_id()))
        order.setField(fix.ExecType(fix.ExecType_NEW))
        order.setField(fix.OrdStatus(fix.OrdStatus_NEW))

        clOrdID = fix.ClOrdID()
        symbol = fix.Symbol()
        side = fix.Side()
        orderQty = fix.OrderQty()

        message.getField(clOrdID)
        message.getField(symbol)
        message.getField(side)
        message.getField(orderQty)

        order.setField(clOrdID)
        order.setField(symbol)
        order.setField(side)
        order.setField(orderQty)
        order.setField(fix.LastQty(orderQty.getValue()))
        order.setField(fix.LastPx(self.prices[symbol.getValue()]))
        order.setField(fix.CumQty(orderQty.getValue()))
        order.setField(fix.AvgPx(self.prices[symbol.getValue()]))

        fix.Session.sendToTarget(order, session_id)

    def handle_cancel_request(self, message, session_id):
        cancel = fix44.OrderCancelReject()
        cancel.setField(fix.OrderID(gen_order_id()))
        cancel.setField(fix.ClOrdID(gen_order_id()))
        cancel.setField(fix.OrigClOrdID(message.getField(fix.OrigClOrdID())))
        cancel.setField(fix.OrdStatus(fix.OrdStatus_REJECTED))
        cancel.setField(fix.CxlRejResponseTo(fix.CxlRejResponseTo_ORDER_CANCEL_REQUEST))
        cancel.setField(fix.CxlRejReason(fix.CxlRejReason_OTHER))

        symbol = fix.Symbol()
        if message.isSetField(symbol):
            message.getField(symbol)
            cancel.setField(symbol)

        fix.Session.sendToTarget(cancel, session_id)

    def handle_market_data_request(self, message, session_id):
        mdReqID = fix.MDReqID()
        subscriptionRequestType = fix.SubscriptionRequestType()
        symbol = fix.Symbol()
        message.getField(mdReqID)
        message.getField(subscriptionRequestType)
        message.getField(symbol)

        if subscriptionRequestType.getValue() == fix.SubscriptionRequestType_SNAPSHOT_PLUS_UPDATES:
            self.subscriptions.add((mdReqID.getValue(), symbol.getValue()))
            self.send_market_data(mdReqID.getValue(), symbol.getValue(), session_id)
        elif subscriptionRequestType.getValue() == fix.SubscriptionRequestType_DISABLE_PREVIOUS_SNAPSHOT_PLUS_UPDATE_REQUEST:
            self.subscriptions.remove((mdReqID.getValue(), symbol.getValue()))

    def send_market_data(self, md_req_id, symbol, session_id):
        snapshot = fix44.MarketDataSnapshotFullRefresh()
        snapshot.setField(fix.MDReqID(md_req_id))
        snapshot.setField(fix.Symbol(symbol))

        group = fix44.MarketDataSnapshotFullRefresh().NoMDEntries()
        group.setField(fix.MDEntryType(fix.MDEntryType_BID))
        group.setField(fix.MDEntryPx(self.prices[symbol] - 0.01))
        group.setField(fix.MDEntrySize(100000))
        snapshot.addGroup(group)

        group.setField(fix.MDEntryType(fix.MDEntryType_OFFER))
        group.setField(fix.MDEntryPx(self.prices[symbol] + 0.01))
        group.setField(fix.MDEntrySize(100000))
        snapshot.addGroup(group)

        fix.Session.sendToTarget(snapshot, session_id)

    def handle_order_status_request(self, message, session_id):
        status = fix44.ExecutionReport()
        status.setField(fix.OrderID(gen_order_id()))
        status.setField(fix.ExecID(gen_order_id()))
        status.setField(fix.ExecType(fix.ExecType_ORDER_STATUS))
        status.setField(fix.OrdStatus(fix.OrdStatus_NEW))

        clOrdID = fix.ClOrdID()
        symbol = fix.Symbol()
        side = fix.Side()

        message.getField(clOrdID)
        message.getField(symbol)
        message.getField(side)

        status.setField(clOrdID)
        status.setField(symbol)
        status.setField(side)
        status.setField(fix.LeavesQty(0))
        status.setField(fix.CumQty(0))
        status.setField(fix.AvgPx(0))

        fix.Session.sendToTarget(status, session_id)

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
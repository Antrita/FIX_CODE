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
        self.orders = {}
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

    def send_market_data(self, md_req_id, symbol, session_id):  #Added tag <44> for prices
        snapshot = fix44.MarketDataSnapshotFullRefresh()
        snapshot.setField(fix.MDReqID(md_req_id))
        snapshot.setField(fix.Symbol(symbol))

        group = fix44.MarketDataSnapshotFullRefresh().NoMDEntries()
        group.setField(fix.MDEntryType(fix.MDEntryType_BID))
        bid_price = self.prices[symbol] - 0.01
        group.setField(fix.MDEntryPx(bid_price))
        group.setField(fix.MDEntrySize(100000))
        snapshot.addGroup(group)

        group.setField(fix.MDEntryType(fix.MDEntryType_OFFER))
        offer_price = self.prices[symbol] + 0.01
        group.setField(fix.MDEntryPx(offer_price))
        group.setField(fix.MDEntrySize(100000))
        snapshot.addGroup(group)

        # Add the price tag <44>
        snapshot.setField(fix.Price((bid_price + offer_price) / 2))

        fix.Session.sendToTarget(snapshot, session_id)

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

    def update_prices(self):
        while True:
            for symbol in self.symbols:
                self.prices[symbol] += random.uniform(-0.05, 0.05)
                self.prices[symbol] = max(4.0, min(self.prices[symbol], 6.0))

            for md_req_id, symbol in self.subscriptions:
                self.send_market_data(md_req_id, symbol, self.session_id)

            time.sleep(6)

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
#ERRORS------------------------------------------------------>
    # WHERE'S THE PRICE TAG <44> [PRICE_VALUE] ??-->
       # "Received admin/Sending Admin: --->
         # 8=FIX.4.4 | 9=62 | 35=0 | 34=14 | 49=MARKET_MAKER | 52=20241002-04:24:24.000 | 56=CLIENT | 10=069 |

#ERRORS <------------------------------------------------------

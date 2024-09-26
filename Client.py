import sys
import quickfix as fix
import quickfix44 as fix44
import random
from datetime import datetime
#import threading
#import queue

def gen_order_id():
    return str(random.randint(100000, 999999))

#Start session and write to file.
class Client(fix.Application):
    def __init__(self):
        super().__init__()
        self.session_id = None
        self.md_req_id = None


    def onCreate(self, session_id):
        self.session_id = session_id
        print(f"Session created - {session_id}")

    def onLogon(self, session_id):
        print(f"Logon - {session_id}")

    def onLogout(self, session_id):
        print(f"Logout - {session_id}")

    def toAdmin(self, message, session_id):
        pass

    def fromAdmin(self, message, session_id):
        pass

    def toApp(self, message, session_id):
        print(f"Sending message: {message}")

    def fromApp(self, message, session_id):
        print(f"Received message: {message}")
        self.log_message(message)

    def log_message(self, message):
        msg_type = self.get_field_value(message, fix.MsgType())
        symbol = self.get_field_value(message, fix.Symbol())
        side = self.get_field_value(message, fix.Side())
        order_qty = self.get_field_value(message, fix.OrderQty())
        price = self.get_field_value(message, fix.Price())
        order_id = self.get_field_value(message, fix.OrderID())
        exec_type = self.get_field_value(message, fix.ExecType())
        ord_status = self.get_field_value(message, fix.OrdStatus())

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S.%f")[:-3]


    def get_field_value(self, message, field):
        try:
            message.getField(field)
            return field.getString()
        except fix.FieldNotFound:
            return ''

    def place_order(self, side, symbol="USD/BRL", quantity=100):


        order = fix44.NewOrderSingle()
        order.setField(fix.ClOrdID(gen_order_id()))
        order.setField(fix.Symbol(symbol))
        order.setField(fix.Side(side))
        order.setField(fix.OrderQty(quantity))
        order.setField(fix.OrdType(fix.OrdType_MARKET))
        order.setField(fix.TransactTime())

        fix.Session.sendToTarget(order, self.session_id)

    def subscribe_market_data(self, symbol="USD/BRL"):
        self.md_req_id = gen_order_id()
        msg = fix44.MarketDataRequest()
        msg.setField(fix.MDReqID(self.md_req_id))
        msg.setField(fix.SubscriptionRequestType(fix.SubscriptionRequestType_SNAPSHOT_PLUS_UPDATES))
        msg.setField(fix.MarketDepth(0))

        group = fix44.MarketDataRequest().NoMDEntryTypes()
        group.setField(fix.MDEntryType(fix.MDEntryType_BID))
        msg.addGroup(group)
        group.setField(fix.MDEntryType(fix.MDEntryType_OFFER))
        msg.addGroup(group)

        symbol_group = fix44.MarketDataRequest().NoRelatedSym()
        symbol_group.setField(fix.Symbol(symbol))
        msg.addGroup(symbol_group)

        fix.Session.sendToTarget(msg, self.session_id)

    def cancel_market_data(self):
        if self.md_req_id:
            msg = fix44.MarketDataRequest()
            msg.setField(fix.MDReqID(gen_order_id()))
            msg.setField(
                fix.SubscriptionRequestType(fix.SubscriptionRequestType_DISABLE_PREVIOUS_SNAPSHOT_PLUS_UPDATE_REQUEST))

            symbol_group = fix44.MarketDataRequest().NoRelatedSym()
            symbol_group.setField(fix.Symbol("USD/BRL"))
            msg.addGroup(symbol_group)

            fix.Session.sendToTarget(msg, self.session_id)
            self.md_req_id = None

    def cancel_order(self, orig_cl_ord_id, symbol="USD/BRL", side=fix.Side_BUY):
        msg = fix44.OrderCancelRequest()
        msg.setField(fix.OrigClOrdID(orig_cl_ord_id))
        msg.setField(fix.ClOrdID(gen_order_id()))
        msg.setField(fix.Symbol(symbol))
        msg.setField(fix.Side(side))
        msg.setField(fix.TransactTime())

        fix.Session.sendToTarget(msg, self.session_id)

    def order_status_request(self, cl_ord_id, symbol="USD/BRL", side=fix.Side_BUY):
        msg = fix44.OrderStatusRequest()
        msg.setField(fix.ClOrdID(cl_ord_id))
        msg.setField(fix.Symbol(symbol))
        msg.setField(fix.Side(side))

        fix.Session.sendToTarget(msg, self.session_id)






def parse_input(input_string):
    parts = input_string.split()
    action = parts[0]
    tags = {}
    for i in range(1, len(parts), 2):
        tag = parts[i][1:]  # Remove the leading '-'
        value = parts[i + 1]
        tags[tag] = value
    return action, tags


def main():
    try:
        settings = fix.SessionSettings("client.cfg")
        application = Client()
        store_factory = fix.FileStoreFactory(settings)
        log_factory = fix.ScreenLogFactory(settings)
        initiator = fix.SocketInitiator(application, store_factory, settings, log_factory)

        initiator.start()

        print("FIX Client has started...")
        print("Enter commands in the format: action -tag1 value1 -tag2 value2 ...")
        print("Available actions: buy, sell, subscribe, unsubscribe, cancel, status, quit")

        while True:
            user_input = input("[Command]: ")

            if user_input.lower() == 'quit':
                break

            try:
                action, tags = parse_input(user_input)

                if action == "buy":
                    symbol = tags.get('55', 'USD/BRL')
                    quantity = int(tags.get('38', '100'))
                    application.place_order(fix.Side_BUY, symbol, quantity)
                elif action == "sell":
                    symbol = tags.get('55', 'USD/BRL')
                    quantity = int(tags.get('38', '100'))
                    application.place_order(fix.Side_SELL, symbol, quantity)
                elif action == "subscribe":
                    symbol = tags.get('55', 'USD/BRL')
                    application.subscribe_market_data(symbol)
                elif action == "unsubscribe":
                    application.cancel_market_data()
                elif action == "cancel":
                    orig_cl_ord_id = tags.get('41', '')
                    symbol = tags.get('55', 'USD/BRL')
                    side = fix.Side_BUY if tags.get('54', '1') == '1' else fix.Side_SELL
                    application.cancel_order(orig_cl_ord_id, symbol, side)
                elif action == "status":
                    cl_ord_id = tags.get('11', '')
                    symbol = tags.get('55', 'USD/BRL')
                    side = fix.Side_BUY if tags.get('54', '1') == '1' else fix.Side_SELL
                    application.order_status_request(cl_ord_id, symbol, side)
                else:
                    print("Invalid action. Please try again.")
            except Exception as e:
                print(f"Error processing command: {e}")

        initiator.stop()

    except (fix.ConfigError, fix.RuntimeError) as e:
        print(f"Error starting client: {e}")
        sys.exit()


if __name__ == "__main__":
    main()
import sys
import quickfix as fix
import quickfix44 as fix44
import random
from datetime import datetime


def gen_order_id():
    return str(random.randint(100000, 999999))


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
        self.format_and_print_message("Sending admin", message)

    def fromAdmin(self, message, session_id):
        self.format_and_print_message("Received admin", message)

    def toApp(self, message, session_id):
        self.format_and_print_message("Sending app", message)

    def fromApp(self, message, session_id):
        try:
            msgType = fix.MsgType()
            message.getHeader().getField(msgType)


            symbol_required_types = [fix.MsgType_ExecutionReport, fix.MsgType_OrderCancelReject,
                                     fix.MsgType_MarketDataSnapshotFullRefresh]
            if msgType.getValue() in symbol_required_types:
                symbol = fix.Symbol()
                if not message.isSetField(symbol):
                    print(f"Warning: Symbol (55) missing in incoming {msgType.getValue()} message")

                    message.setField(fix.Symbol(55, "USD/BRL"))
                else:
                    message.getField(symbol)
                    print(f"Received message for Symbol: {symbol.getValue()}")

            self.format_and_print_message("Received app", message)

            if msgType.getValue() == fix.MsgType_MarketDataSnapshotFullRefresh:
                self.on_market_data(message)
            elif msgType.getValue() == fix.MsgType_ExecutionReport:
                self.on_execution_report(message)
            # Add handlers for other message types as needed


        except Exception as e:
           print(f"Error processing incoming message: {e}")

    def format_and_print_message(self, prefix, message):
        try:
            formatted_message = message.toString().replace(chr(1), ' | ')
            print(f"{prefix}: {formatted_message}")
        except Exception as e:
            print(f"Error formatting message: {e}")

    def on_execution_report(self, message):
        try:
            exec_type = fix.ExecType()
            message.getField(exec_type)

            cl_ord_id = self.get_field_value(message, fix.ClOrdID())
            order_id = self.get_field_value(message, fix.OrderID())
            symbol = self.get_field_value(message, fix.Symbol())

            print(
                f"Execution Report - ClOrdID: {cl_ord_id}, OrderID: {order_id}, Symbol: {symbol}, ExecType: {exec_type.getValue()}")

            # Handle different execution types
            if exec_type.getValue() == fix.ExecType_NEW:
                print("New order acknowledged")
            elif exec_type.getValue() == fix.ExecType_CANCELED:
                print("Order canceled")
            elif exec_type.getValue() == fix.ExecType_REJECTED:
                print("Order rejected")
            # Add more execution type handlers as needed

        except Exception as e:
            print(f"Error processing execution report: {e}")

    def on_market_data(self, message):
        symbol = self.get_field_value(message, fix.Symbol())
        md_req_id = self.get_field_value(message, fix.MDReqID())

        bid_price = offer_price = "N/A"
        bid_size = offer_size = "N/A"

        no_md_entries = fix.NoMDEntries()
        message.getField(no_md_entries)

        for i in range(no_md_entries.getValue()):
            group = fix44.MarketDataSnapshotFullRefresh().NoMDEntries()
            message.getGroup(i + 1, group)

            entry_type = fix.MDEntryType()
            group.getField(entry_type)

            if entry_type.getValue() == fix.MDEntryType_BID:
                bid_price = self.get_field_value(group, fix.MDEntryPx())
                bid_size = self.get_field_value(group, fix.MDEntrySize())
            elif entry_type.getValue() == fix.MDEntryType_OFFER:
                offer_price = self.get_field_value(group, fix.MDEntryPx())
                offer_size = self.get_field_value(group, fix.MDEntrySize())

        print(f"Market Data - Symbol: {symbol}, MDReqID: {md_req_id}")
        print(f"Bid: {bid_price} (Size: {bid_size}), Offer: {offer_price} (Size: {offer_size})")



    def get_field_value(self, message, field):
        try:
            message.getField(field)
            return field.getString()
        except fix.FieldNotFound:
            return ''

    def place_order(self, side, symbol, quantity):
        order = fix44.NewOrderSingle()
        clOrdID = gen_order_id()
        order.setField(fix.ClOrdID(clOrdID))
        order.setField(fix.Symbol(symbol))
        order.setField(fix.Side(side))
        order.setField(fix.OrderQty(float(quantity)))
        order.setField(fix.OrdType(fix.OrdType_MARKET))
        order.setField(fix.TransactTime())

        fix.Session.sendToTarget(order, self.session_id)
        return clOrdID

    def subscribe_market_data(self, symbol="USD/BRL"):
        self.md_req_id = gen_order_id()
        msg = fix44.MarketDataRequest()
        msg.setField(fix.MDReqID(self.md_req_id))
        msg.setField(fix.SubscriptionRequestType(fix.SubscriptionRequestType_SNAPSHOT_PLUS_UPDATES))
        msg.setField(fix.MarketDepth(0))  # Full book
        msg.setField(fix.MDUpdateType(fix.MDUpdateType_FULL_REFRESH))  # Full refresh

        # Specify the types of market data entries we want
        group = fix44.MarketDataRequest().NoMDEntryTypes()
        group.setField(fix.MDEntryType(fix.MDEntryType_BID))
        msg.addGroup(group)
        group.setField(fix.MDEntryType(fix.MDEntryType_OFFER))
        msg.addGroup(group)

        # Specify the symbol
        symbol_group = fix44.MarketDataRequest().NoRelatedSym()
        symbol_group.setField(fix.Symbol(symbol))
        msg.addGroup(symbol_group)

        print(f"Subscribing to market data for symbol: {symbol}")
        self.format_and_print_message("Sending MarketDataRequest", msg)
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

    def cancel_order(self, orig_cl_ord_id, symbol, side):
        cancel = fix44.OrderCancelRequest()
        cancel.setField(fix.OrigClOrdID(orig_cl_ord_id))
        cancel.setField(fix.ClOrdID(gen_order_id()))
        cancel.setField(fix.Symbol(symbol))
        cancel.setField(fix.Side(side))
        cancel.setField(fix.TransactTime())

        fix.Session.sendToTarget(cancel, self.session_id)

    def order_status_request(self, cl_ord_id, symbol, side):
        status = fix44.OrderStatusRequest()
        status.setField(fix.ClOrdID(cl_ord_id))
        status.setField(fix.Symbol(symbol))
        status.setField(fix.Side(side))

        fix.Session.sendToTarget(status, self.session_id)






def parse_input(input_string):
    parts = input_string.split()
    action = parts[0]
    tags = {}
    if action in ["status", "cancel"]:
        if len(parts) >= 3:
            tags[parts[1]] = parts[2]
    else:
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
        print("For status: status 11 [ClOrdID]")
        print("For cancel order: cancel 41 [OrigClOrdID]")
        print("To quit, enter 'quit'")

        while True:
            try:
                user_input = input("[Command]: ")

                if user_input.lower() == 'quit':
                    break

                action, tags = parse_input(user_input)

                if action == "buy" or action == "sell":
                    symbol = tags.get('55', 'USD/BRL')
                    quantity = tags.get('38')
                    if quantity is None:
                        quantity = input("Enter quantity: ")
                    side = fix.Side_BUY if action == "buy" else fix.Side_SELL
                    cl_ord_id = application.place_order(side, symbol, quantity)
                    print(f"{action.capitalize()} order placed. ClOrdID: {cl_ord_id}")
                elif action == "subscribe":
                    symbol = tags.get('55', 'USD/BRL')
                    application.subscribe_market_data(symbol)
                elif action == "unsubscribe":
                    application.cancel_market_data()
                elif action == "cancel":
                    orig_cl_ord_id = tags.get('41')
                    if orig_cl_ord_id:
                        symbol = tags.get('55', 'USD/BRL')
                        side = tags.get('54', fix.Side_BUY)
                        application.cancel_order(orig_cl_ord_id, symbol, side)
                    else:
                        print("Invalid cancel command. Use format: cancel 41 [OrigClOrdID] 55 [Symbol] 54 [Side]")
                elif action == "status":
                    cl_ord_id = tags.get('11')
                    if cl_ord_id:
                        symbol = tags.get('55', 'USD/BRL')
                        side = tags.get('54', fix.Side_BUY)
                        application.order_status_request(cl_ord_id, symbol, side)
                    else:
                        print("Invalid status command. Use format: status 11 [ClOrdID] 55 [Symbol] 54 [Side]")
                else:
                    print("Invalid action. Please try again.")
            except fix.FieldNotFound as e:
                print(f"Field not found error: {e}")
            except ValueError as e:
                print(f"Value error: {e}")
            except Exception as e:
                print(f"Error processing command: {e}")
                # Continue running even if there's an error

        print("Stopping the FIX client...")
        initiator.stop()
        print("FIX client stopped.")

    except (fix.ConfigError, fix.RuntimeError) as e:
        print(f"Error in FIX client: {e}")
    except KeyboardInterrupt:
        print("FIX client interrupted by user.")
    finally:
        print("Exiting FIX client.")

if __name__ == "__main__":
    main()

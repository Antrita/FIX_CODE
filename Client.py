'''Users can now place orders using commands like:

buy USD/BRL 100 (Market order)
sell USD/BRL 100 limit (Limit order)
buy USD/BRL 100 stop  (Stop order)
sell USD/BRL 100 stop_limit 1.10  (Stop-limit order)'''

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
        self.last_heartbeat_time = None #set heartbt time

    def onCreate(self, session_id):
        self.session_id = session_id
        print(f"Session created - {session_id}")

    def onLogon(self, session_id):
        self.session_id = session_id
        print(f"Logon - {session_id}")
        print("Client logged on and ready to send requests.")

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

        except Exception as e:
            print(f" ")

    '''def format_and_print_message(self, prefix, message):
        try:
            formatted_message = message.toString().replace(chr(1), ' | ')
            print(f"{prefix}: {formatted_message}")
        except Exception as e:
            print(f"Error formatting message: {e}" '''

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

    def format_and_print_message(self, prefix, message):
        try:
            formatted_message = message.toString().replace(chr(1), ' | ')
            print(f"{prefix}: {formatted_message}")
        except Exception as e:
            print(f"Error formatting message: {e}")
            print(f"{prefix}: {message}")

    def on_market_data(self, message):
        try:
            symbol = "USD/BRL"
            md_req_id = fix.MDReqID()
            message.getField(md_req_id)

            no_md_entries = fix.NoMDEntries()
            message.getField(no_md_entries)

            print(f"Received market data for {symbol}, MDReqID: {md_req_id.getValue()}")

            for i in range(no_md_entries.getValue()):
                group = fix44.MarketDataSnapshotFullRefresh().NoMDEntries()
                message.getGroup(i + 1, group)

                entry_type = fix.MDEntryType()
                price = fix.MDEntryPx()
                size = fix.MDEntrySize()

                group.getField(entry_type)
                group.getField(price)
                group.getField(size)

                print(f"  {entry_type.getValue()}: Price={price.getValue()}, "
                      f"Size={size.getValue()}")

        except fix.FieldNotFound as e:
            print(f"Error processing market data: {e}")

    def get_field_value(self, message, field):
        try:
            message.getField(field)
            return field.getString()
        except fix.FieldNotFound:
            return ''

    def place_order(self, side, symbol, quantity, order_type, price=None, stop_price=None):
        order_details = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'orderType': order_type,
            'price': price,
            'stopPrice': stop_price
        }
        return self.send_order(order_details)

    def send_order(self, order_details):
        new_order = fix44.NewOrderSingle()
        cl_ord_id = gen_order_id()
        new_order.setField(fix.ClOrdID(cl_ord_id))
        new_order.setField(fix.Symbol(order_details['symbol']))
        new_order.setField(fix.Side(order_details['side']))
        new_order.setField(fix.OrderQty(float(order_details['quantity'])))
        new_order.setField(fix.OrdType(order_details['orderType']))
        new_order.setField(fix.TransactTime())

        if order_details['orderType'] != fix.OrdType_MARKET:
            new_order.setField(fix.Price(float(order_details['price'])))

        if order_details['orderType'] in [fix.OrdType_STOP, fix.OrdType_STOP_LIMIT]:
            new_order.setField(fix.StopPx(float(order_details['stopPrice'])))

        try:
            fix.Session.sendToTarget(new_order, self.session_id)
            print(f"Order sent: ClOrdID={cl_ord_id}, Symbol={order_details['symbol']}, "
                  f"Side={'Buy' if order_details['side'] == fix.Side_BUY else 'Sell'}, "
                  f"Quantity={order_details['quantity']}, OrderType={order_details['orderType']}")
            return cl_ord_id
        except fix.RuntimeError as e:
            print(f"Error sending order: {e}")
            return None
    def subscribe_market_data(self, symbol="USD/BRL"):
        self.md_req_id = gen_order_id()
        request = fix44.MarketDataRequest()
        request.setField(fix.MDReqID(self.md_req_id))
        request.setField(fix.SubscriptionRequestType(fix.SubscriptionRequestType_SNAPSHOT_PLUS_UPDATES))
        request.setField(fix.MarketDepth(0))
        request.setField(fix.MDUpdateType(fix.MDUpdateType_FULL_REFRESH))

        group = fix44.MarketDataRequest().NoMDEntryTypes()
        group.setField(fix.MDEntryType(fix.MDEntryType_BID))
        request.addGroup(group)
        group.setField(fix.MDEntryType(fix.MDEntryType_OFFER))
        request.addGroup(group)

        symbol_group = fix44.MarketDataRequest().NoRelatedSym()
        symbol_group.setField(fix.Symbol(symbol))
        request.addGroup(symbol_group)

        print(f"Subscribing to market data for symbol: {symbol}")
        self.format_and_print_message("Sending MarketDataRequest", request)
        fix.Session.sendToTarget(request, self.session_id)

    def on_market_data(self, message):

            symbol = fix.Symbol()
            md_req_id = fix.MDReqID()
            message.getField(symbol)
            message.getField(md_req_id)

            no_md_entries = fix.NoMDEntries()
            message.getField(no_md_entries)

            print(f"Received market data for {symbol.getValue()}, MDReqID: {md_req_id.getValue()}")

            for i in range(no_md_entries.getValue()):
                group = fix44.MarketDataSnapshotFullRefresh().NoMDEntries()
                message.getGroup(i + 1, group)

                entry_type = fix.MDEntryType()
                price = fix.MDEntryPx()
                size = fix.MDEntrySize()
                date = fix.MDEntryDate()
                time = fix.MDEntryTime()

                group.getField(entry_type)
                group.getField(price)
                group.getField(size)
                group.getField(date)
                group.getField(time)

                print(f"  {entry_type.getValue()}: Price={price.getValue()}, "
                      f"Size={size.getValue()}, Date={date.getValue()}, Time={time.getValue()}")


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
        print("Enter commands in the following format:")
        print("  buy/sell symbol quantity [order_type] [price] [stop_price]")
        print("Order types: market (default), limit, stop, stop_limit")
        print("Examples:")
        print("  buy USD/BRL 100")
        print("  sell USD/BRL 100 limit ")
        print("  buy USD/BRL 100 stop")
        print("  sell USD/BRL 100 stop_limit [stop price; ex-1.15]")
        print("Other commands: subscribe, unsubscribe, cancel, status, quit")
        print("For status: status [ClOrdID]")
        print("For cancel order: cancel [OrigClOrdID]")

        while True:
            try:
                user_input = input("[Command]: ")

                if user_input.lower() == 'quit':
                    break

                parts = user_input.split()
                action = parts[0].lower()

                if action in ["buy", "sell"]:
                    if len(parts) < 3:
                        print(
                            "Invalid order command. Use format: buy/sell symbol quantity [order_type] [price] [stop_price]")
                        continue

                    symbol = parts[1]
                    quantity = parts[2]
                    order_type = fix.OrdType_MARKET
                    price = None
                    stop_price = None

                    if len(parts) > 3:
                        order_type_str = parts[3].lower()
                        if order_type_str == "limit":
                            order_type = fix.OrdType_LIMIT
                            price = parts[4] if len(parts) > 4 else input("Enter limit price: ")
                        elif order_type_str == "stop":
                            order_type = fix.OrdType_STOP
                            stop_price = parts[4] if len(parts) > 4 else input("Enter stop price: ")
                        elif order_type_str == "stop_limit":
                            order_type = fix.OrdType_STOP_LIMIT
                            stop_price = parts[4] if len(parts) > 4 else input("Enter stop price: ")
                            price = parts[5] if len(parts) > 5 else input("Enter limit price: ")
                        elif order_type_str != "market":
                            print("Invalid order type. Using market order.")

                    side = fix.Side_BUY if action == "buy" else fix.Side_SELL

                    cl_ord_id = application.place_order(side, symbol, quantity, order_type, price, stop_price)
                    if cl_ord_id:
                        print(f"{action.capitalize()} order placed. ClOrdID: {cl_ord_id}")
                    else:
                        print("Failed to place order.")
                elif action == "subscribe":
                    symbol = parts[1] if len(parts) > 1 else 'USD/BRL'
                    application.subscribe_market_data(symbol)
                elif action == "unsubscribe":
                    application.cancel_market_data()
                elif action == "cancel":
                    if len(parts) < 2:
                        print("Invalid cancel command. Use format: cancel [OrigClOrdID]")
                    else:
                        orig_cl_ord_id = parts[1]
                        symbol = 'USD/BRL'  # Default symbol
                        side = fix.Side_BUY  # Default side
                        application.cancel_order(orig_cl_ord_id, symbol, side)
                elif action == "status":
                    if len(parts) < 2:
                        print("Invalid status command. Use format: status [ClOrdID]")
                    else:
                        cl_ord_id = parts[1]
                        symbol = 'USD/BRL'
                        side = fix.Side_BUY
                        application.order_status_request(cl_ord_id, symbol, side)
                else:
                    print("Invalid action. Please try again.")
            except Exception as e:
                print(f" ")


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
import asyncio
import uvicorn
import threading
import logging
import time
import quickfix as fix
from contextlib import asynccontextmanager
from Market_maker import MarketMaker
from Client import Client
from fastapi_app import app, manager
import signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GlobalState:
    def __init__(self):
        self.market_maker = None
        self.client = None
        self.command_queue = None
        self.loop = None
        self.running = True
        self.market_maker_thread = None
        self.client_thread = None
        self.initiator = None

state = GlobalState()


def client_message_handler(prefix, message):
    try:
        raw_message = message.toString()
        formatted_message = raw_message.replace(chr(1), ' | ')
        print(f"{prefix}: {formatted_message}")

        if state.loop:
            asyncio.run_coroutine_threadsafe(
                manager.broadcast_order_update(formatted_message),
                state.loop
            )
    except Exception as e:
        logger.error(f"Error in client message handler: {e}")


def market_maker_message_handler(prefix, message):
    try:
        raw_message = message.toString()
        formatted_message = raw_message.replace(chr(1), ' | ')
        print(f"{prefix}: {formatted_message}")

        if state.loop:
            asyncio.run_coroutine_threadsafe(
                manager.broadcast_maker_output(formatted_message),
                state.loop
            )
    except Exception as e:
        logger.error(f"Error in market maker message handler: {e}")


def run_market_maker():
    try:
        market_maker = MarketMaker()
        market_maker.format_and_print_message = market_maker_message_handler
        state.market_maker = market_maker

        # Start MarketMaker
        market_maker.start()
    except Exception as e:
        logger.error(f"Error in market maker thread: {e}")
    finally:
        logger.info("Market maker thread ending")


def run_client():
    try:
        client = Client()
        client.format_and_print_message = client_message_handler
        state.client = client

        # Start Client
        settings = fix.SessionSettings("client.cfg")
        store_factory = fix.FileStoreFactory(settings)
        log_factory = fix.ScreenLogFactory(settings)
        state.initiator = fix.SocketInitiator(client, store_factory, settings, log_factory)
        state.initiator.start()

        # Keep the thread alive
        while state.running:
            time.sleep(1)
    except Exception as e:
        logger.error(f"Error in client thread: {e}")
    finally:
        if state.initiator:
            state.initiator.stop()
        logger.info("Client thread ending")


def start_fix_threads():
    try:
        # Start MarketMaker in a thread
        state.market_maker_thread = threading.Thread(target=run_market_maker, daemon=True)
        state.market_maker_thread.start()

        # Start Client in a thread
        state.client_thread = threading.Thread(target=run_client, daemon=True)
        state.client_thread.start()

        # Give threads time to initialize
        time.sleep(2)

        return True
    except Exception as e:
        logger.error(f"Error starting FIX threads: {e}")
        return False


def stop_fix_threads():
    try:
        state.running = False
        if state.market_maker:
            state.market_maker.is_running = False
        if state.initiator:
            state.initiator.stop()

        # Wait for threads to finish
        if state.market_maker_thread and state.market_maker_thread.is_alive():
            state.market_maker_thread.join(timeout=5)
        if state.client_thread and state.client_thread.is_alive():
            state.client_thread.join(timeout=5)
    except Exception as e:
        logger.error(f"Error stopping FIX threads: {e}")


@asynccontextmanager
async def lifespan(app):
    # Startup: Initialize state and FIX system
    state.loop = asyncio.get_running_loop()
    state.command_queue = asyncio.Queue()
    state.running = True

    if not start_fix_threads():
        logger.error("Failed to initialize FIX system")
        exit(1)

    # Start command processor
    asyncio.create_task(command_processor())

    yield

    # Cleanup
    logger.info("Shutting down FIX system...")
    stop_fix_threads()
    logger.info("System shutdown complete")


app.router.lifespan_context = lifespan


@app.post("/api/command")
async def handle_command(command: dict):
    try:
        cmd = command["command"]
        if state.command_queue:
            await state.command_queue.put(cmd)
            return {"status": "success", "message": f"Command received: {cmd}"}
        else:
            return {"status": "error", "message": "Command queue not initialized"}
    except Exception as e:
        logger.error(f"Error handling command: {e}")
        return {"status": "error", "message": str(e)}


async def command_processor():
    while state.running:
        try:
            command = await state.command_queue.get()

            parts = command.split()
            action = parts[0].lower()

            # Format as FIX message
            formatted_command = []
            if action in ["status", "cancel"]:
                if len(parts) >= 2:
                    formatted_command.append(f"35={action}")
                    formatted_command.append(f"11={parts[1]}")  # ClOrdID
            else:
                formatted_command.append(f"35={action}")
                for i in range(1, len(parts), 2):
                    if i + 1 < len(parts):
                        formatted_command.append(f"{parts[i]}={parts[i + 1]}")

            formatted_message = " | ".join(formatted_command)

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: process_command_sync(command, formatted_message)
            )
        except Exception as e:
            logger.error(f"")
        await asyncio.sleep(0.1)


def process_command_sync(command):
    try:
        if state.client and state.client.session_id:
            # Format the command here before processing
            formatted_message = format_fix_command(command)
            state.client.process_command(command)

            # Broadcast the formatted command to UI
            if state.loop:
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast_order_update(formatted_message),
                    state.loop
                )
    except Exception as e:
        logger.error(f"Error processing command synchronously: {e}")


def format_fix_command(command: str) -> str:
    """Format command into FIX message format with delimiters"""
    try:
        parts = command.split()
        action = parts[0].lower()
        formatted_parts = []

        if action in ["status", "cancel"]:
            if len(parts) >= 2:
                formatted_parts.append(f"35={action}")
                formatted_parts.append(f"11={parts[1]}")  # ClOrdID
        else:
            formatted_parts.append(f"35={action}")
            # Handle order commands (buy/sell)
            if action in ["buy", "sell"]:
                if len(parts) >= 3:
                    formatted_parts.append(f"54={'1' if action == 'buy' else '2'}")  # Side
                    formatted_parts.append(f"55={parts[1]}")  # Symbol
                    formatted_parts.append(f"38={parts[2]}")  # Quantity

                    # Handle order type and price
                    if len(parts) > 3:
                        order_type = parts[3].lower()
                        if order_type == "limit" and len(parts) > 4:
                            formatted_parts.append("40=2")  # Order Type = Limit
                            formatted_parts.append(f"44={parts[4]}")  # Price
                        elif order_type == "market":
                            formatted_parts.append("40=1")  # Order Type = Market
                        elif order_type == "stop" and len(parts) > 4:
                            formatted_parts.append("40=3")  # Order Type = Stop
                            formatted_parts.append(f"99={parts[4]}")  # StopPx
                        elif order_type == "stop_limit" and len(parts) > 5:
                            formatted_parts.append("40=4")  # Order Type = Stop Limit
                            formatted_parts.append(f"99={parts[4]}")  # StopPx
                            formatted_parts.append(f"44={parts[5]}")  # Price

        return " | ".join(formatted_parts)
    except Exception as e:
        logger.error(f"Error formatting command: {e}")
        return command

async def command_processor():
    while state.running:
        try:
            command = await state.command_queue.get()
            await asyncio.get_event_loop().run_in_executor(None, process_command_sync, command)
        except Exception as e:
            logger.error(f"")
        await asyncio.sleep(0.1)


def signal_handler(signum, frame):
    logger.info("Received shutdown signal")
    state.running = False


if __name__ == "__main__":
    try:
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        stop_fix_threads()
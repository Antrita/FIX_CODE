from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import json

# Initialize FastAPI app
app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add ConnectionManager class
class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.market_maker_output = []

    def format_fix_message(self, message: str) -> str:
        """Format FIX message with proper delimiters and clean structure"""
        try:
            # Split the message into parts
            parts = message.split(chr(1))
            # Filter out empty parts and format each tag-value pair
            formatted_parts = []
            for part in parts:
                if part.strip():
                    if '=' in part:
                        tag, value = part.split('=', 1)
                        formatted_parts.append(f"{tag.strip()}={value.strip()}")
            # Join with proper delimiter
            return " | ".join(formatted_parts)
        except Exception as e:
            logger.error(f"Error formatting FIX message: {e}")
            return message

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")
        # Send initial market maker output history with formatted messages
        for message in self.market_maker_output:
            await websocket.send_json({
                "type": "maker_output",
                "message": self.format_fix_message(message)
            })



    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast_market_data(self, data: dict):
        message = {
            "type": "market_data",
            "data": data["data"],
            "prefix": data["prefix"]
        }
        await self.broadcast(json.dumps(message))

    async def broadcast_maker_output(self, message: str):
        self.market_maker_output.append(message)
        ws_message = {
            "type": "maker_output",
            "message": message
        }
        await self.broadcast(json.dumps(ws_message))

    async def broadcast_order_update(self, message: str):
        ws_message = {
            "type": "order_update",
            "order": message
        }
        await self.broadcast(json.dumps(ws_message))

    async def broadcast(self, message: str):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.add(connection)

        for connection in disconnected:
            self.active_connections.remove(connection)

# Create manager instance
manager = ConnectionManager()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get():
    with open('static/index.html', 'r') as f:
        return HTMLResponse(content=f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message from WebSocket: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
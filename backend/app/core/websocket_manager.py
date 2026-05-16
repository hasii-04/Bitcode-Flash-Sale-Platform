from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        # Maps event_id to a list of connected WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, event_id: int):
        await websocket.accept()
        if event_id not in self.active_connections:
            self.active_connections[event_id] = []
        self.active_connections[event_id].append(websocket)

    def disconnect(self, websocket: WebSocket, event_id: int):
        if event_id in self.active_connections and websocket in self.active_connections[event_id]:
            self.active_connections[event_id].remove(websocket)

    async def broadcast_stock_update(self, event_id: int, item_id: int, new_stock: int):
        if event_id in self.active_connections:
            message = json.dumps({
                "type": "STOCK_UPDATE",
                "item_id": item_id,
                "new_stock": new_stock
            })
            for connection in self.active_connections[event_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    pass

manager = ConnectionManager()

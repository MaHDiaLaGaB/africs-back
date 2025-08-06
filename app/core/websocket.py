import json
from collections import defaultdict
from typing import Union
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """
        Accepts a WebSocket connection and registers it under the given user_id.
        """
        await websocket.accept()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """
        Removes a WebSocket connection for the given user_id.
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal(self, data: Union[str, dict], user_id: str) -> None:
        """
        Sends a message to all WebSocket connections for a specific user_id.
        Accepts either a raw JSON string or a Python dict.
        """
        # Serialize dicts to JSON strings
        message = data if isinstance(data, str) else json.dumps(data)
        for connection in self.active_connections.get(user_id, []):
            await connection.send_text(message)

    async def broadcast(self, data: Union[str, dict]) -> None:
        """
        Broadcasts a message to every connected WebSocket across all user_ids.
        Accepts either a raw JSON string or a Python dict.
        """
        message = data if isinstance(data, str) else json.dumps(data)
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_text(message)


manager = ConnectionManager()

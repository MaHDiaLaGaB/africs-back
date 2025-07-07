# app/core/websocket.py
from jose import jwt
from fastapi import WebSocket, WebSocketDisconnect, Depends, status
from typing import Dict, Set

SECRET_KEY = "…"  # match your JWT secret
ALGORITHM = "HS256"

class ConnectionManager:
    def __init__(self):
        # map user_id → set of WebSocket
        self.active: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, token: str):
        # 1) accept the connection
        await websocket.accept()

        # 2) decode and authorize
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 3) register
        self.active.setdefault(user_id, set()).add(websocket)
        return user_id

    def disconnect(self, user_id: int, websocket: WebSocket):
        sockets = self.active.get(user_id)
        if sockets and websocket in sockets:
            sockets.remove(websocket)
            if not sockets:
                self.active.pop(user_id, None)

    async def send_personal_message(self, user_id: int, message: dict):
        """Send JSON to all sockets for this user."""
        for ws in list(self.active.get(user_id, [])):
            try:
                await ws.send_json(message)
            except:
                # drop broken socket
                await ws.close()
                self.disconnect(user_id, ws)

manager = ConnectionManager()

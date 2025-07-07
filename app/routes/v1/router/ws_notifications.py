# app/routes/ws_notifications.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket import manager

router = APIRouter()

@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,               # client must supply ?token=…
):
    user_id = await manager.connect(websocket, token)
    if not user_id:
        return
    try:
        while True:
            # keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

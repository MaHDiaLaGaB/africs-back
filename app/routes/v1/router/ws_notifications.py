# app/routes/ws_notifications.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket import manager

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


# Test endpoints
@router.post("/notify/{user_id}")
async def notify_user(user_id: str, message: str):
    await manager.send_personal(json.dumps({"message": message}), user_id)
    return {"status": "sent"}

@router.post("/broadcast")
async def broadcast_message(message: str):
    await manager.broadcast(json.dumps({"message": message}))
    return {"status": "broadcasted"}

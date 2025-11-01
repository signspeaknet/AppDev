import asyncio
import json
import websockets
from datetime import datetime

# Store connected clients: {websocket: {"username": str, "user_id": str}}
connected_clients = {}

# Store username to websocket mapping for easy lookup
username_to_ws = {}


async def broadcast_online_users():
    """Broadcast the list of online users to all connected clients."""
    if not connected_clients:
        return
    
    online_users = [
        {"username": data["username"], "user_id": data["user_id"]}
        for ws, data in connected_clients.items()
    ]
    
    message = {
        "type": "online_users",
        "users": online_users,
        "timestamp": datetime.now().isoformat()
    }
    
    # Send to all connected clients
    websockets_to_remove = []
    for ws in connected_clients:
        try:
            await ws.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            websockets_to_remove.append(ws)
    
    # Clean up closed connections
    for ws in websockets_to_remove:
        await remove_client(ws)


async def remove_client(websocket):
    """Remove a client from the connected clients list."""
    if websocket in connected_clients:
        user_data = connected_clients[websocket]
        username = user_data["username"]
        
        # Remove from both dictionaries
        del connected_clients[websocket]
        if username in username_to_ws:
            del username_to_ws[username]
        
        print(f"User disconnected: {username}")
        
        # Notify all other users
        await broadcast_online_users()


async def handle_client(websocket):
    """Handle a single client connection."""
    print(f"New connection from {websocket.remote_address}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                
                # Handle user registration/login
                if msg_type == "register":
                    username = data.get("username")
                    user_id = data.get("user_id")
                    
                    if not username or not user_id:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Username and user_id required"
                        }))
                        continue
                    
                    # Check if username already taken
                    if username in username_to_ws and username_to_ws[username] != websocket:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Username already taken"
                        }))
                        continue
                    
                    # Register the user
                    connected_clients[websocket] = {
                        "username": username,
                        "user_id": user_id
                    }
                    username_to_ws[username] = websocket
                    
                    print(f"User registered: {username} (ID: {user_id})")
                    
                    # Send success response
                    await websocket.send(json.dumps({
                        "type": "registered",
                        "username": username,
                        "user_id": user_id
                    }))
                    
                    # Broadcast updated online users list
                    await broadcast_online_users()
                
                # Handle call initiation
                elif msg_type == "call_request":
                    caller = connected_clients.get(websocket)
                    target_username = data.get("target_username")
                    
                    if not caller:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Not registered"
                        }))
                        continue
                    
                    # Find target user
                    target_ws = username_to_ws.get(target_username)
                    if not target_ws or target_ws not in connected_clients:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "User not found or offline"
                        }))
                        continue
                    
                    # Forward call request to target
                    await target_ws.send(json.dumps({
                        "type": "incoming_call",
                        "caller_username": caller["username"],
                        "caller_id": caller["user_id"]
                    }))
                    
                    print(f"Call request: {caller['username']} -> {target_username}")
                
                # Handle call acceptance
                elif msg_type == "call_accepted":
                    accepter = connected_clients.get(websocket)
                    caller_username = data.get("caller_username")
                    
                    if not accepter:
                        continue
                    
                    # Notify caller that call was accepted
                    caller_ws = username_to_ws.get(caller_username)
                    if caller_ws:
                        await caller_ws.send(json.dumps({
                            "type": "call_accepted",
                            "accepter_username": accepter["username"]
                        }))
                    
                    print(f"Call accepted: {caller_username} <-> {accepter['username']}")
                
                # Handle call rejection
                elif msg_type == "call_rejected":
                    rejecter = connected_clients.get(websocket)
                    caller_username = data.get("caller_username")
                    
                    if not rejecter:
                        continue
                    
                    # Notify caller that call was rejected
                    caller_ws = username_to_ws.get(caller_username)
                    if caller_ws:
                        await caller_ws.send(json.dumps({
                            "type": "call_rejected",
                            "rejecter_username": rejecter["username"]
                        }))
                    
                    print(f"Call rejected: {caller_username} X {rejecter['username']}")
                
                # Handle WebRTC signaling messages (offer, answer, ICE candidates)
                elif msg_type in ["offer", "answer", "ice_candidate"]:
                    sender = connected_clients.get(websocket)
                    target_username = data.get("target_username")
                    
                    if not sender:
                        continue
                    
                    # Forward signaling message to target
                    target_ws = username_to_ws.get(target_username)
                    if target_ws:
                        forward_data = {
                            "type": msg_type,
                            "from_username": sender["username"],
                            "data": data.get("data")
                        }
                        await target_ws.send(json.dumps(forward_data))
                        print(f"Forwarded {msg_type}: {sender['username']} -> {target_username}")
                
                # Handle call end
                elif msg_type == "call_ended":
                    sender = connected_clients.get(websocket)
                    target_username = data.get("target_username")
                    
                    if not sender:
                        continue
                    
                    # Notify the other party
                    target_ws = username_to_ws.get(target_username)
                    if target_ws:
                        await target_ws.send(json.dumps({
                            "type": "call_ended",
                            "from_username": sender["username"]
                        }))
                    
                    print(f"Call ended: {sender['username']} <-> {target_username}")
                
                else:
                    print(f"Unknown message type: {msg_type}")
            
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {message}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
            except Exception as e:
                print(f"Error handling message: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed: {websocket.remote_address}")
    finally:
        await remove_client(websocket)


async def health_check(path, request_headers):
    """Handle HTTP health checks from Render."""
    if path == "/" or path == "/health":
        return (200, [], b"OK\n")
    return None  # Let WebSocket handle other paths


async def main():
    """Start the WebSocket server."""
    # Use 0.0.0.0 to accept connections from any IP (needed for Render)
    # Port 8765 by default, but Render will set PORT env variable
    import os
    port = int(os.environ.get("PORT", 8765))
    
    print(f"Starting WebSocket server on port {port}...")
    
    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        port,
        process_request=health_check  # Handle HTTP health checks
    ):
        print(f"WebSocket server running on ws://0.0.0.0:{port}")
        print("Server ready for WebSocket connections and HTTP health checks")
        print("Waiting for connections...")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")


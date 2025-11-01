# WebRTC Video Call Signaling Server

A WebSocket-based signaling server for coordinating peer-to-peer video calls between mobile clients.

## Features

- User registration and authentication
- Real-time online users list
- Call initiation and management
- WebRTC signaling (offer/answer/ICE candidates exchange)
- Call acceptance/rejection handling
- Automatic cleanup on disconnect

## Local Development

### Requirements

- Python 3.11+
- pip

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python main.py
```

The server will start on `ws://localhost:8765` by default.

### Testing Locally

You can test the server using a WebSocket client or the Flet mobile app.

Example connection:
```python
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8765") as ws:
        # Register user
        await ws.send(json.dumps({
            "type": "register",
            "username": "testuser",
            "user_id": "unique-id-123"
        }))
        
        # Receive response
        response = await ws.recv()
        print(response)
```

## Deployment to Render

### Method 1: Using Render Dashboard

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository or upload files
4. Configure:
   - **Name**: video-call-signaling-server
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free
5. Click "Create Web Service"

### Method 2: Using render.yaml (Infrastructure as Code)

1. Push this `server_code` folder to your GitHub repository
2. In Render Dashboard, click "New +" → "Blueprint"
3. Connect your repository
4. Render will automatically detect and use `render.yaml`

### Important Notes for Render

- Render will automatically set the `PORT` environment variable
- The server is configured to use `0.0.0.0` to accept external connections
- Free tier will spin down after inactivity (15 min); expect cold start delays
- WebSocket URL will be: `wss://your-app-name.onrender.com`

### Environment Variables (Optional)

You can set these in Render Dashboard if needed:
- `PORT`: Server port (automatically set by Render)

## API Protocol

### Message Types

#### Client → Server

1. **Register User**
```json
{
  "type": "register",
  "username": "john_doe",
  "user_id": "unique-uuid"
}
```

2. **Call Request**
```json
{
  "type": "call_request",
  "target_username": "jane_doe"
}
```

3. **Call Accepted**
```json
{
  "type": "call_accepted",
  "caller_username": "john_doe"
}
```

4. **Call Rejected**
```json
{
  "type": "call_rejected",
  "caller_username": "john_doe"
}
```

5. **WebRTC Offer**
```json
{
  "type": "offer",
  "target_username": "jane_doe",
  "data": { "sdp": "...", "type": "offer" }
}
```

6. **WebRTC Answer**
```json
{
  "type": "answer",
  "target_username": "john_doe",
  "data": { "sdp": "...", "type": "answer" }
}
```

7. **ICE Candidate**
```json
{
  "type": "ice_candidate",
  "target_username": "jane_doe",
  "data": { "candidate": "...", "sdpMLineIndex": 0 }
}
```

8. **End Call**
```json
{
  "type": "call_ended",
  "target_username": "jane_doe"
}
```

#### Server → Client

1. **Registration Confirmation**
```json
{
  "type": "registered",
  "username": "john_doe",
  "user_id": "unique-uuid"
}
```

2. **Online Users List**
```json
{
  "type": "online_users",
  "users": [
    {"username": "john_doe", "user_id": "uuid1"},
    {"username": "jane_doe", "user_id": "uuid2"}
  ],
  "timestamp": "2025-11-01T14:30:00"
}
```

3. **Incoming Call**
```json
{
  "type": "incoming_call",
  "caller_username": "john_doe",
  "caller_id": "uuid1"
}
```

4. **Call Accepted**
```json
{
  "type": "call_accepted",
  "accepter_username": "jane_doe"
}
```

5. **Call Rejected**
```json
{
  "type": "call_rejected",
  "rejecter_username": "jane_doe"
}
```

6. **WebRTC Signaling (Forwarded)**
```json
{
  "type": "offer|answer|ice_candidate",
  "from_username": "john_doe",
  "data": { ... }
}
```

7. **Call Ended**
```json
{
  "type": "call_ended",
  "from_username": "john_doe"
}
```

8. **Error**
```json
{
  "type": "error",
  "message": "Error description"
}
```

## Security Considerations

**Note**: This is a basic signaling server for demonstration purposes.

For production use, consider adding:
- User authentication (JWT tokens, OAuth)
- Rate limiting
- HTTPS/WSS encryption (Render provides this automatically)
- Message validation and sanitization
- Database for persistent user data
- Logging and monitoring

## Troubleshooting

### Server won't start
- Check if port 8765 is already in use
- Ensure Python 3.11+ is installed
- Verify dependencies are installed

### Clients can't connect
- Check firewall settings
- Verify the correct WebSocket URL (ws:// for local, wss:// for Render)
- Check server logs for error messages

### Calls not connecting
- Ensure both clients are registered
- Check WebRTC signaling messages are being forwarded
- Verify STUN servers are accessible from client devices

## License

MIT License - Feel free to use and modify for your projects.


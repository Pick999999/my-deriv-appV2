# api/server-time.py
from http.server import BaseHTTPRequestHandler
import json
import asyncio
import websockets
from datetime import datetime
import time

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # เรียก async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.get_server_time())
            loop.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {
                "error": str(e),
                "success": False
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    async def get_server_time(self):
        websocket = None
        try:
            # เชื่อมต่อ WebSocket
            websocket = await asyncio.wait_for(
                websockets.connect("wss://ws.binaryws.com/websockets/v3"),
                timeout=5
            )
            
            # ขอเวลาจาก server
            time_request = {
                "time": 1,
                "req_id": 1
            }
            
            await websocket.send(json.dumps(time_request))
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)
            
            if "time" in data:
                server_time = data["time"]
                
                # แปลงเป็นรูปแบบ hh:mm:ss
                dt = datetime.fromtimestamp(server_time)
                formatted_time = dt.strftime("%H:%M:%S")
                
                # คำนวณเวลาที่เหลือจนถึงวินาที 0
                current_seconds = dt.second
                microseconds = dt.microsecond / 1000000
                seconds_to_next_minute = 60 - current_seconds - microseconds
                
                return {
                    "success": True,
                    "server_time": server_time,
                    "formatted_time": formatted_time,
                    "seconds_to_next_minute": round(seconds_to_next_minute, 2),
                    "local_time": datetime.now().strftime("%H:%M:%S")
                }
            else:
                return {
                    "success": False,
                    "error": "Cannot get server time"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if websocket:
                await websocket.close()
# api/candle-history.py
from http.server import BaseHTTPRequestHandler
import json
import asyncio
import websockets
from datetime import datetime
import urllib.parse as urlparse

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse query parameters
            query = urlparse.urlparse(self.path).query
            params = urlparse.parse_qs(query)
            
            symbol = params.get('symbol', ['R_50'])[0]
            count = int(params.get('count', ['10'])[0])
            
            # เรียก async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.get_candle_history(symbol, count))
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
    
    async def get_candle_history(self, symbol="R_50", count=10):
        websocket = None
        try:
            # เชื่อมต่อ WebSocket
            websocket = await asyncio.wait_for(
                websockets.connect("wss://ws.binaryws.com/websockets/v3"),
                timeout=5
            )
            
            # ขอข้อมูล candle history
            candle_request = {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": count,
                "end": "latest",
                "start": 1,
                "style": "candles",
                "granularity": 60,  # 1 นาที
                "req_id": 2
            }
            
            await websocket.send(json.dumps(candle_request))
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            
            if "candles" in data:
                candles = data["candles"]
                
                # แปลงข้อมูล candles
                formatted_candles = []
                for candle in candles:
                    formatted_candles.append({
                        "time": datetime.fromtimestamp(candle["epoch"]).strftime("%Y-%m-%d %H:%M:%S"),
                        "epoch": candle["epoch"],
                        "open": candle["open"],
                        "high": candle["high"],
                        "low": candle["low"],
                        "close": candle["close"]
                    })
                
                return {
                    "success": True,
                    "symbol": symbol,
                    "count": len(formatted_candles),
                    "candles": formatted_candles,
                    "latest_candle": formatted_candles[-1] if formatted_candles else None
                }
            else:
                return {
                    "success": False,
                    "error": "Cannot get candle history",
                    "response": data
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if websocket:
                await websocket.close()
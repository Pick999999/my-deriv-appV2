# api/candle-history.py
import json
import asyncio
import websockets
from datetime import datetime
import urllib.parse as urlparse

async def get_candle_history(symbol="R_50", count=10):
    websocket = None
    try:
        # เชื่อมต่อ WebSocket พร้อม app_id
        # app_id 1089 สำหรับ testing (public app_id)
        websocket_url = "wss://ws.derivws.com/websockets/v3?app_id=1089"
        websocket = await asyncio.wait_for(
            websockets.connect(websocket_url),
            timeout=8
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
                "error": "Cannot get candle history from response",
                "raw_response": str(data)
            }
            
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "WebSocket connection timeout"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}"
        }
    finally:
        if websocket:
            try:
                await websocket.close()
            except:
                pass

def handler(request, context):
    """Main handler for Vercel"""
    
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    try:
        # Handle preflight OPTIONS request
        if request.get('httpMethod') == 'OPTIONS' or request.get('method') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({"message": "CORS preflight"})
            }
        
        # Parse query parameters
        query_string = request.get('queryStringParameters') or {}
        symbol = query_string.get('symbol', 'R_50')
        count = int(query_string.get('count', '10'))
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_candle_history(symbol, count))
        loop.close()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Handler error: {str(e)}",
            "error_type": type(e).__name__
        }
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps(error_result)
        }

# สำหรับ local testing
if __name__ == "__main__":
    import asyncio
    async def test():
        result = await get_candle_history("R_50", 5)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test())

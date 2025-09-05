# api/server-time.py
import json
import asyncio
import websockets
from datetime import datetime

async def get_server_time():
    websocket = None
    try:
        # เชื่อมต่อ WebSocket
        websocket = await asyncio.wait_for(
            websockets.connect("wss://ws.binaryws.com/websockets/v3?app_id=1089"),
            timeout=8
        )
        
        # ขอเวลาจาก server
        time_request = {
            "time": 1,
            "req_id": 1
        }
        
        await websocket.send(json.dumps(time_request))
        response = await asyncio.wait_for(websocket.recv(), timeout=8)
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
                "error": "Cannot get server time from response",
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
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_server_time())
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
    # Test locally
    import asyncio
    async def test():
        result = await get_server_time()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test())


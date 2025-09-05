# api/server-time.py
import json
import time
import threading
from datetime import datetime
import websocket
import queue

class DerivWebSocketClient:
    def __init__(self):
        self.ws_url = "wss://ws.derivws.com/websockets/v3?app_id=1089"
        self.websocket = None
        self.is_connected = False
        self.response_queue = queue.Queue()
        self.current_req_id = 1
        
    def on_open(self, ws):
        """เมื่อ WebSocket เชื่อมต่อสำเร็จ"""
        self.is_connected = True
        
    def on_message(self, ws, message):
        """เมื่อได้รับ message จาก server"""
        try:
            data = json.loads(message)
            self.response_queue.put(data)
        except json.JSONDecodeError:
            pass
            
    def on_error(self, ws, error):
        """เมื่อเกิด error"""
        self.response_queue.put({"error": str(error), "req_id": self.current_req_id})
        
    def on_close(self, ws, close_status_code, close_msg):
        """เมื่อปิดการเชื่อมต่อ"""
        self.is_connected = False
        
    def connect(self, timeout=8):
        """เชื่อมต่อกับ Deriv WebSocket"""
        try:
            # สร้าง WebSocket connection
            self.websocket = websocket.WebSocketApp(
                self.ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # รัน WebSocket ใน thread แยก
            ws_thread = threading.Thread(
                target=self.websocket.run_forever,
                daemon=True
            )
            ws_thread.start()
            
            # รอจนกว่าจะเชื่อมต่อสำเร็จ
            start_time = time.time()
            while not self.is_connected:
                if time.time() - start_time > timeout:
                    return False
                time.sleep(0.1)
                
            return True
            
        except Exception as e:
            return False
    
    def send_request(self, request_data, timeout=5):
        """ส่ง request และรอ response"""
        if not self.is_connected:
            return None
            
        try:
            # ตั้ง req_id
            self.current_req_id = request_data.get('req_id', 1)
            
            # ส่ง request
            self.websocket.send(json.dumps(request_data))
            
            # รอ response
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = self.response_queue.get(timeout=0.1)
                    if response.get('req_id') == self.current_req_id:
                        return response
                except queue.Empty:
                    continue
                    
            return {"error": "Response timeout"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_server_time(self):
        """ดึงเวลาจาก server"""
        request_data = {
            "time": 1,
            "req_id": 1
        }
        
        response = self.send_request(request_data)
        
        if response and "time" in response:
            server_time = response["time"]
            
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
                "local_time": datetime.now().strftime("%H:%M:%S"),
                "method": "WEBSOCKET_CLIENT"
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Unknown error"),
                "raw_response": str(response)
            }
    
    def close(self):
        """ปิดการเชื่อมต่อ"""
        if self.websocket:
            self.websocket.close()
            self.is_connected = False

def handler(request, context=None):
    """Main handler for Vercel"""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    client = None
    
    try:
        # Handle preflight OPTIONS
        method = request.get('httpMethod') or request.get('method', 'GET')
        if method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({"message": "CORS OK"})
            }
        
        # สร้าง WebSocket client
        client = DerivWebSocketClient()
        
        # เชื่อมต่อ
        if not client.connect(timeout=6):
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    "success": False,
                    "error": "Cannot connect to Deriv WebSocket"
                })
            }
        
        # ดึงเวลาจาก server
        result = client.get_server_time()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                "success": False,
                "error": f"Handler error: {str(e)}",
                "error_type": type(e).__name__
            })
        }
    finally:
        # ปิดการเชื่อมต่อ
        if client:
            client.close()

# สำหรับ local testing
if __name__ == "__main__":
    client = DerivWebSocketClient()
    if client.connect():
        result = client.get_server_time()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        client.close()
    else:
        print("Cannot connect to WebSocket")

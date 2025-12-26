import asyncio
import websockets
import base64
import os
import sys
import ssl
import numpy as np
from urllib.parse import urlencode
from websockets.exceptions import InvalidStatusCode

async def test_websocket_VAD():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost:8000"  # 默认值为 localhost:8000
    host = host.removeprefix("http://").removeprefix("https://")
    is_ssl = sys.argv[2] == "ssl" if len(sys.argv) > 2 else False  # 默认值为 localhost:8000

    token = os.environ.get("TOKEN")  # 从环境变量获取

    if not token:
        sys.exit("Please set the TOKEN environment variable.")

    query_params = urlencode({"token": token})
    uri = "wss:" if is_ssl else "ws:" + f"//{host}/ws?{query_params}"
    print(f"Connecting to {uri}...")

    # 禁用 SSL 验证
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(uri, ssl=ssl_context if is_ssl else None) as websocket:
            print("Connected to WebSocket server")        

            # Simulate 30ms PCM chunks (480 samples, 16kHz, 16-bit mono)
            sample_rate = 16000
            frame_duration_ms = 30
            samples_per_frame = int(sample_rate * frame_duration_ms / 1000)  # 480

            # Simulate speech (1*2 second of random noise to mimic voice)        
            speech_frames = 33*2  # 33 frames ≈ 1 second
            for _ in range(speech_frames):
                # Generate a 200 Hz sine wave (mimicking voice pitch) + random noise
                t = np.linspace(0, frame_duration_ms / 1000, samples_per_frame, endpoint=False)
                sine_wave = 15000 * np.sin(2 * np.pi * 200 * t)  # 200 Hz, amplitude ±15000
                noise = np.random.randint(-5000, 5000, samples_per_frame)  # Random noise ±5000
                pcm_data = np.clip(sine_wave + noise, -20000, 20000).astype(np.int16)
                pcm_data = pcm_data.tobytes()
                base64_chunk = base64.b64encode(pcm_data).decode('utf-8')
                await websocket.send(base64_chunk)
                await asyncio.sleep(frame_duration_ms / 1000)  # 30ms

            # Send chunks to simulate 1.5 seconds of silence (50 chunks * 30ms)
            pcm_data = b'\x00' * 960  # 480 samples * 2 bytes
            base64_chunk = base64.b64encode(pcm_data).decode('utf-8')
            for _ in range(50):
                await websocket.send(base64_chunk)
                print("Sent silient PCM chunk")
                # Wait 30ms to simulate real-time streaming
                await asyncio.sleep(0.03)
                
                # Check for server response
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    print(f"Received: {message}")
                    if message == "stop_recording":
                        print("Test sucessfully")
                        break
                except asyncio.TimeoutError:
                    continue
            
            await websocket.close()

    except Exception as e:
        error_msg = str(e)
        if "HTTP 403" in error_msg:
            print("HTTP 403: Forbidden. Maybe your token expired or permission denied.")
        else:
            print(f"Other error occurred: {error_msg}")

    sys.exit(1)
  
asyncio.run(test_websocket_VAD())

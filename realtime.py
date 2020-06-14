import websockets
import pathlib
import time
import ssl
import asyncio

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
# localhost_pem = pathlib.Path(__file__).with_name("localhost.pem")
# ssl_context.load_verify_locations(localhost_pem)

def on_message(ws, msg):
    if len(msg) == 2 and int(msg) == 40:
        ws.send('42["action",{"type":"RUP"}]')
    print(msg)

async def main():
    gameid = sys.argv[1]
    uri = f"wss://www.pokernow.club/socket.io/?gameID={gameid}&EIO=3&transport=websocket"
    async with websockets.connect(uri) as websocket:
        greeting = await websocket.recv()
        print(f"< {greeting}")
        await websocket.send('42["action",{"type":"RUP"}]')
        print("sent")
        next = await websocket.recv()
        print(next)
        next = await websocket.recv()
        print(next)
        next = await websocket.recv()
        print(next)



asyncio.get_event_loop().run_until_complete(main())


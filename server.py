import os
import asyncio
import websockets
import json
print("파일 실행 시작")

rooms = {}


async def handler(websocket):

    room_code = await websocket.recv()

    if room_code not in rooms:
        rooms[room_code] = set()

    rooms[room_code].add(websocket)

    print(f"{room_code} 방 접속")

    try:
        async for message in websocket:

            dead_clients = []

            for client in rooms[room_code]:

                if client != websocket:
                    try:
                        await client.send(message)
                    except:
                        dead_clients.append(client)

            for dead in dead_clients:
                rooms[room_code].remove(dead)

    finally:
        rooms[room_code].remove(websocket)


async def main():

    port = int(os.environ.get("PORT", 8765))

    async with websockets.serve(
        handler,
        "0.0.0.0",
        port
    ):

        print(f"서버 실행 중: {port}")

        await asyncio.Future()


try:
    asyncio.run(main())

except Exception as e:
    print("에러 발생:")
    print(e)
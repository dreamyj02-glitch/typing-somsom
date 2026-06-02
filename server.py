import os
import asyncio
import websockets
import json

print("파일 실행 시작")

rooms = {}
usernames = {}


async def broadcast(room_code, sender, message):
    dead_clients = []

    for client in list(rooms.get(room_code, [])):
        if client != sender:
            try:
                await client.send(message)
            except:
                dead_clients.append(client)

    for dead in dead_clients:
        rooms[room_code].discard(dead)


async def handler(websocket):
    first_message = await websocket.recv()
    first_data = json.loads(first_message)

    room_code = first_data["room"]
    username = first_data["user"]

    usernames[websocket] = username

    if room_code not in rooms:
        rooms[room_code] = set()

    rooms[room_code].add(websocket)

    print(f"{room_code} 방 접속: {username}")

    try:
        async for message in websocket:
            data = json.loads(message)

            await broadcast(room_code, websocket, message)

    finally:
        rooms[room_code].discard(websocket)

        username = usernames.pop(websocket, None)

        if username:
            disconnect_message = json.dumps({
                "type": "disconnect",
                "user": username
            })

            await broadcast(room_code, websocket, disconnect_message)

        print(f"{room_code} 방 퇴장: {username}")


async def main():
    port = int(os.environ.get("PORT", 8765))

    async with websockets.serve(
        handler,
        "0.0.0.0",
        port,
        ping_interval=20,
        ping_timeout=20
    ):
        print(f"서버 실행 중: {port}")
        await asyncio.Future()


try:
    asyncio.run(main())

except Exception as e:
    print("에러 발생:")
    print(e)
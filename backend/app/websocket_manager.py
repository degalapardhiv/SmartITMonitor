from fastapi import WebSocket
import asyncio


class ConnectionManager:

    def __init__(self):
        self.connections = []
        self.loop = None


    async def connect(self, websocket: WebSocket):

        await websocket.accept()

        self.connections.append(websocket)

        self.loop = asyncio.get_running_loop()

        print(
            "WebSocket connected:",
            len(self.connections)
        )


    def disconnect(self, websocket: WebSocket):

        if websocket in self.connections:
            self.connections.remove(websocket)


    async def broadcast(self, message: dict):

        print(
            "Broadcasting to:",
            len(self.connections),
            "clients"
        )

        disconnected = []

        for connection in self.connections:

            try:
                await connection.send_json(message)

            except Exception:

                disconnected.append(connection)


        for connection in disconnected:
            self.disconnect(connection)


    def broadcast_from_thread(self, message: dict):

        if self.loop:

            asyncio.run_coroutine_threadsafe(
                self.broadcast(message),
                self.loop
            )


manager = ConnectionManager()

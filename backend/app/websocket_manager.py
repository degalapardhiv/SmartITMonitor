from fastapi import WebSocket
import asyncio
import threading


class ConnectionManager:

    def __init__(self):
        self.connections = []
        self.loop = None
        self._lock = threading.Lock()


    async def connect(self, websocket: WebSocket):

        await websocket.accept()

        with self._lock:
            self.connections.append(websocket)

        self.loop = asyncio.get_running_loop()


    def disconnect(self, websocket: WebSocket):

        with self._lock:
            if websocket in self.connections:
                self.connections.remove(websocket)


    async def broadcast(self, message: dict):

        with self._lock:
            connections = list(self.connections)

        disconnected = []

        for connection in connections:

            try:
                await connection.send_json(message)

            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


    def broadcast_from_thread(self, message: dict):

        loop = self.loop

        if loop is None or loop.is_closed():
            return

        try:

            future = asyncio.run_coroutine_threadsafe(
                self.broadcast(message),
                loop
            )

            future.result(timeout=5)

        except Exception:
            pass


    def send_ping(self):

        self.broadcast_from_thread(
            {"type": "ping"}
        )


manager = ConnectionManager()

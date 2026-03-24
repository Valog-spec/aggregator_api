import asyncio

import grpc

from src.grpc_service.protos import kvstore_pb2_grpc
from src.grpc_service.servicers.cache_servicer import CacheService


class KVStoreGrpcServer:
    """gRPC сервер для KeyValueStore"""

    def __init__(self, port: int = 8000, max_size: int = 10):
        self.port = port
        self.max_size = max_size
        self.server: grpc.aio.Server | None = None

    async def start(self):
        """Запуск сервера"""
        self.server = grpc.aio.server(
            options=[
                ("grpc.max_send_message_length", 10 * 1024 * 1024),
                ("grpc.max_receive_message_length", 10 * 1024 * 1024),
                ("grpc.keepalive_time_ms", 30000),
            ]
        )

        kvstore_pb2_grpc.add_KeyValueStoreServicer_to_server(
            CacheService(max_size=self.max_size), self.server
        )

        self.server.add_insecure_port(f"[::]:{self.port}")

        await self.server.start()

        await self.server.wait_for_termination()


async def main():
    server = KVStoreGrpcServer(port=8000, max_size=10)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())

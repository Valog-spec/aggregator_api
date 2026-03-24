import grpc

from src.cache.lru_cache import LruCache
from src.grpc_service.protos.kvstore_pb2 import (
    DeleteRequest,
    DeleteResponse,
    GetRequest,
    GetResponse,
    KeyValue,
    ListRequest,
    ListResponse,
    PutRequest,
    PutResponse,
)
from src.grpc_service.protos.kvstore_pb2_grpc import KeyValueStoreServicer


class CacheService(KeyValueStoreServicer):
    def __init__(self, max_size: int = 10):
        self._cache = LruCache(max_size=max_size)

    async def Put(self, request: PutRequest, context) -> PutResponse:
        """
        Добавить или обновить значение.

        Args:
            request: PutRequest с key, value, ttl_seconds
            context: gRPC контекст
        """
        if not request.key:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Ключ не должен быть пустым")
            return PutResponse()
        if not request.value:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Значение не должно быть пустым")
            return PutResponse()
        if request.ttl_seconds < 0:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("ttl_seconds не должен быть отрицательным")
            return PutResponse()
        try:
            await self._cache.put(request.key, request.value, request.ttl_seconds)
        except Exception:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return PutResponse()

    async def Get(self, request: GetRequest, context) -> GetResponse:
        """
        Получить значение по ключу.

        Args:
            request: GetRequest с key
            context: gRPC контекст
        """
        if not request.key:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Ключ не должен быть пустым")
            return GetResponse()

        try:
            value = await self._cache.get(request.key)

            if value is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Ключ '{request.key}' не найден или истек")
                return GetResponse()

            return GetResponse(value=value)
        except Exception:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return GetResponse()

    async def Delete(self, request: DeleteRequest, context) -> DeleteResponse:
        """
        Удалить ключ.

        Args:
            request: DeleteRequest с key
            context: gRPC контекст
        """
        if not request.key:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Ключ не должен быть пустым")
            return DeleteResponse()

        try:
            deleted = await self._cache.delete(request.key)
            if not deleted:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Ключ '{request.key}' не найден")
                return DeleteResponse()

            return DeleteResponse()
        except Exception:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return DeleteResponse()

    async def List(self, request: ListRequest, context) -> ListResponse:
        """
        Получить все ключи и значения с указанным префиксом.

        Args:
            request: ListRequest с prefix
            context: gRPC контекст
        """
        try:
            items = await self._cache.list_by_prefix(request.prefix)

            response = ListResponse()
            for key, value in items:
                response.items.append(KeyValue(key=key, value=value))
            return response

        except Exception:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return ListResponse()

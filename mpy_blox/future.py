from asyncio import Event


class InvalidStateError(Exception):
    pass


class Future:
    def __init__(self):
        self.event = Event()
        self._result = None
        self._exception = None
        self._gen = None

    def set_exception(self, new_exception):
        self._exception = new_exception
        self.event.set()

    def set_result(self, new_result):
        self._result = new_result
        self.event.set()

    def result(self):
        _exception = self._exception
        if _exception:
            raise _exception

        _result = self._result
        if _result is None:
            raise InvalidStateError
            
        return _result

    async def wait_for_result(self):
        await self.event.wait()
        return self.result()

    # Coroutine compatibility interface
    def send(self, value):
        if not self._gen:
            self._gen = self.wait_for_result()
        return self._gen.send(value)

    def throw(self, typ, val=None, tb=None):
        if self._gen:
            return self._gen.throw(typ, val, tb)

    def close(self):
        if self._gen:
            return self._gen.close()

    # Awaitable compatibility interface
    def __await__(self):
        yield from self.wait_for_result()

class ErrorWithMQTTReason(Exception):
    def __init__(self, reason_code, *args: object) -> None:
        super().__init__(*args)
        self.reason_code = reason_code

    def __str__(self) -> str:
        return "{}, reason code {}".format(self.__class__, self.reason_code)


class MQTTConnectionRefused(ErrorWithMQTTReason):
    pass


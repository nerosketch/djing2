import sys
from typing import Union

from pexpect.pty_spawn import spawn, TIMEOUT

from devices.device_config.base import DeviceTimeoutError


class ExpectValidationError(ValueError):
    pass


IP4_ADDR_REGEX = (
    r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


class MySpawn(spawn):
    def __init__(self, *args, **kwargs):
        super().__init__(encoding="utf-8", timeout=120, *args, **kwargs)
        self.logfile = sys.stdout

    def do_cmd(self, c: str, prompt: Union[str, list[str]]):
        try:
            self.sendline(c)
            return self.expect_exact(prompt)
        except TIMEOUT as err:
            raise DeviceTimeoutError('PExpec timeout error') from err

    def get_lines(self):
        return self.buffer.split("\r\n")

    def get_lines_before(self):
        return self.before.split("\r\n")

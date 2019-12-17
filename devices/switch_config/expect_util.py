import sys
from pexpect import spawn


class ExpectValidationError(ValueError):
    pass


IP4_ADDR_REGEX = (
    r'^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
    r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
    r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
    r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)


class MySpawn(spawn):
    def __init__(self, *args, **kwargs):
        super(MySpawn, self).__init__(encoding='utf-8', *args, **kwargs)
        self.logfile = sys.stdout

    def do_cmd(self, c, prompt):
        self.sendline(c)
        return self.expect_exact(prompt)

    def get_lines(self):
        return self.buffer.split('\r\n')

    def get_lines_before(self):
        return self.before.split('\r\n')

import os
from collections import namedtuple
from multiprocessing import Process
from contextlib import contextmanager

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from djing2.lib.logger import logger


Credentials = namedtuple('Credentials', 'username password')

credentials = Credentials(username='testuname', password='testpassw')


def _ftp_server():
    # Instantiate a dummy authorizer for managing 'virtual' users
    authorizer = DummyAuthorizer()

    # Define a new user having full r/w permissions and a read-only
    # anonymous user
    authorizer.add_user(
        credentials.username,
        credentials.password,
        '/tmp', perm='elradfmwMT'
    )
    authorizer.add_anonymous(os.getcwd())

    # Instantiate FTP handler class
    handler = FTPHandler
    handler.authorizer = authorizer

    # Define a customized banner (string returned when client connects)
    handler.banner = "pyftpdlib based ftpd ready."

    # Specify a masquerade address and the range of ports to use for
    # passive connections.  Decomment in case you're behind a NAT.
    #handler.masquerade_address = '151.25.42.11'
    #handler.passive_ports = range(60000, 65535)

    # Instantiate FTP server class and listen on 127.0.0.1:2121
    try:
        address = ('127.0.0.1', 2122)
        server = FTPServer(address, handler)

        # set a limit for connections
        server.max_cons = 16
        server.max_cons_per_ip = 5

        # start ftp server
        server.serve_forever()
    except OSError as e:
        logger.error(str(e))


@contextmanager
def ftp_test():
    p = Process(target=_ftp_server)
    try:
        p.start()
        yield p
    finally:
        if p is not None:
            p.terminate()
            p.join()


class FtpTestCaseMixin:
    def assertFtpFile(self, fname: str, content: str):
        with open(fname, 'r') as f:
            file_content = f.read()
        self.assertEqual(
            file_content.strip(),
            content
        )


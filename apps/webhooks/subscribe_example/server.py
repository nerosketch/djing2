#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO


class SimpleHttpHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Example response')


    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        print(body)
        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(b'This is POST request. ')
        response.write(b'Received: ')
        response.write(body)
        self.wfile.write(response.getvalue())



def main():
    httpd = HTTPServer(('localhost', 8083), SimpleHttpHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    main()


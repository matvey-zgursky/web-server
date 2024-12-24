import socket
import json
import sys
from typing import Optional

from email.parser import Parser
from functools import lru_cache
from urllib.parse import parse_qs, urlparse, ParseResult


MAX_LINE = 64 * 1024
MAX_HEADERS = 100


class HTTPError(Exception):
    def __init__(self,
                 status: int,
                 reason: str,
                 body: Optional[str] = None) -> None:
        super().__init__()
        self.status = status
        self.reason = reason
        self.body = body


class Request:
    def __init__(self,
                 method: str,
                 target: str,
                 version: str,
                 headers: dict[str, str],
                 rfile: socket.SocketIO) -> None:
        self.method = method
        self.target = target
        self.version = version
        self.headers = headers
        self.rfile = rfile

    @property
    @lru_cache(maxsize=None)
    def url(self) -> ParseResult:
        return urlparse(self.target)

    @property
    @lru_cache(maxsize=None)
    def query(self) -> dict[str, list[str]]:
        return parse_qs(self.url.query)

    @property
    def path(self) -> str:
        return self.url.path

    def read_body(self) -> Optional[bytes]:
        size = self.headers.get('Content-Length')
        if not size:
            return None

        return self.rfile.read(int(size))


class Response:
    def __init__(self,
                 status: int,
                 reason: str,
                 headers: Optional[list[tuple[str, str | int]]] = None,
                 body: Optional[bytes] = None) -> None:
        self.status = status
        self.reason = reason
        self.headers = headers
        self.body = body


class MyHTTPServer:
    def __init__(self, host: str, port: int, server_name: str) -> None:
        self._host = host
        self._port = port
        self._server_name = server_name
        self._users: dict[int, dict[str, int | str]] = {}

    def send_error(self, conn: socket.socket, error: HTTPError) -> None:
        try:
            status = error.status
            reason = error.reason
            body = (error.body or error.reason).encode('utf-8')
        except:
            status = 500
            reason = b'Internal Server Error'
            body = b'Internal Server Error'

        response = Response(status,
                            reason, [('Content-Length', len(body))],
                            body)
        self.send_response(conn, response)

    def send_response(self, conn: socket.socket, response: Response) -> None:
        wfile = conn.makefile('wb')
        status_line = f'HTTP/1.1 {response.status} {response.reason}\r\n'
        wfile.write(status_line.encode('iso-8859-1'))

        if response.headers:
            for (key, value) in response.headers:
                header_line = f'{key}: {value}\r\n'
                wfile.write(header_line.encode('iso-8859-1'))

        wfile.write(b'\r\n')

        if response.body:
            wfile.write(response.body)

        wfile.flush()
        wfile.close()

    def parse_request_line(self,
                           rfile: socket.SocketIO) -> tuple[str, str, str]:
        raw = rfile.readline(MAX_LINE + 1) 
        if len(raw) > MAX_LINE:
            raise HTTPError(400, 'Bad request', 'Request line is too long')

        request_line = str(raw, 'iso-8859-1')
        words = request_line.split()  
        if len(words) != 3:  
            raise HTTPError(400, 'Bad request', 'Malformed request line')

        method, target, version = words
        if version != 'HTTP/1.1':
            raise HTTPError(505, 'HTTP Version Not Supported')

        return method, target, version

    def parse_headers(self, rfile: socket.SocketIO) -> dict[str, str]:
        headers = []

        while True:
            line = rfile.readline(MAX_LINE + 1)
            if len(line) > MAX_LINE:
                raise HTTPError(494, 'Request header too large')
            if line in (b'\r\n', b'\n', b''):
                break
            headers.append(line)
            if len(headers) > MAX_HEADERS:
                raise HTTPError(494, 'Too many headers')

        sheaders = b''.join(headers).decode('iso-8859-1')

        return dict(Parser().parsestr(sheaders).items())

    def parse_request(self, conn: socket.socket) -> Request:
        rfile = conn.makefile('rb')

        method, target, version = self.parse_request_line(rfile)
        headers = self.parse_headers(rfile)

        host = headers.get('Host')
        if not host:
            raise HTTPError(400, 'Bad request', 'Host header is missing')

        if host not in (self._server_name,
                        f'{self._server_name}:{self._port}'):
            raise HTTPError(404, 'Not found')

        return Request(method, target, version, headers, rfile)

    def handle_post_users(self, request: Request) -> Response:
        user_id = len(self._users) + 1
        self._users[user_id] = {
            'id': user_id,
            'name': request.query['name'][0],
            'age': request.query['age'][0]
        }

        return Response(204, 'Created')

    def handle_get_users(self, request: Request) -> Response:
        accept = request.headers.get('Accept')
        if 'text/html' in accept:
            contentType = 'text/html; charset=utf-8'
            body = '<html><head></head><body>'
            body += f'<div>Пользователи ({len(self._users)})</div>'
            body += '<ul>'
            for user in self._users.values():
                body += f'<li>#{user["id"]} {user["name"]}, {user["age"]}</li>'
            body += '</ul>'
            body += '</body></html>'

        elif 'application/json' in accept:
            contentType = 'application/json; charset=utf-8'
            body = json.dumps(self._users)

        else:
            return Response(406, 'Not Acceptable')

        body = body.encode('utf-8')
        headers = [('Content-Type', contentType),
                   ('Content-Length', len(body))]
        return Response(200, 'OK', headers, body)

    def handle_get_user(self, request: Request, user_id: str) -> Response:
        user = self._users.get(int(user_id))
        if not user:
            raise HTTPError(404, 'Not found')

        accept = request.headers.get('Accept')
        if 'text/html' in accept:
            contenttype = 'text/html; charset=utf-8'
            body = f'<html><head></head><body>'
            body += f'Пользователь #{user["id"]} {user["name"]}, {user["age"]}'
            body += '</body></html>'

        elif 'application/json' in accept:
            contenttype = 'application/json; charset=utf-8'
            body = json.dumps(user)

        else:
            return Response(406, 'Not Acceptable')

        body = body.encode('utf-8')
        headers = [('Content-Type', contenttype),
                   ('Content-Length', len(body))]

        return Response(200, 'OK', headers, body)

    def handle_request(self, request: Request) -> Response:
        if request.path == '/users' and request.method == 'POST':
            return self.handle_post_users(request)

        if request.path == '/users' and request.method == 'GET':
            return self.handle_get_users(request)

        if request.path.startswith('/users/'):
            user_id = request.path[len('/users/'):]
            if user_id.isdigit():
                return self.handle_get_user(request, user_id)

        raise HTTPError(404, 'Not found')

    def serve_client(self, conn: socket.socket) -> None:
        request = None
        try:
            request = self.parse_request(conn)
            response = self.handle_request(request)
            self.send_response(conn, response)
        except ConnectionResetError:
            conn = None
        except Exception as ex:
            self.send_error(conn, ex)

        if conn:
            if request and request.rfile:
                request.rfile.close()
            conn.close()

    def serve_forever(self) -> None:
        serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto=0)

        try:
            serv_sock.bind((self._host, self._port))
            serv_sock.listen()

            while True:
                conn, _ = serv_sock.accept()
                try:
                    self.serve_client(conn)
                except Exception as ex:
                    print('Client serving failed', ex)
        finally:
            serv_sock.close()


if __name__ == '__main__':
    host = sys.argv[1]
    port = int(sys.argv[2])
    server_name = sys.argv[3]

    server = MyHTTPServer(host, port, server_name)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

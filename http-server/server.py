import socket
import json
import sys

from email.parser import Parser
from functools import lru_cache
from urllib.parse import parse_qs, urlparse


MAX_LINE = 64 * 1024
MAX_HEADERS = 100


class Request:
    def __init__(self, method, target, version, headers, rfile) -> None:
        self.method = method
        self.target = target
        self.version = version
        self.headers = headers
        self.rfile = rfile

    @property
    @lru_cache(maxsize=None)
    def url(self):
        return urlparse(self.target)

    @property
    @lru_cache(maxsize=None)
    def query(self):
        return parse_qs(self.url.query)

    @property
    def path(self):
        return self.url.path

    def read_body(self):
        pass


class Response:
    def __init__(self, status, phrase, headers=None, body=None) -> None:
        self.status = status
        self.phrase = phrase
        self.headers = headers
        self.body = body 


class MyHTTPServer:
    def __init__(self, host, port, server_name) -> None:
        self._host = host
        self._port = port
        self._server_name = server_name
        self._users = {}

    def send_error(self, conn, error):
        pass

    def send_response(self, conn, response):
        pass

    def parse_request_line(self, rfile):
        raw = rfile.readline(MAX_LINE + 1)  # эффективно читаем строку целиком
        if len(raw) > MAX_LINE:
            raise Exception('Request line is too long')

        req_line = str(raw, 'iso-8859-1')
        words = req_line.split()  # разделяем по пробелу
        if len(words) != 3:  # и ожидаем ровно 3 части
            raise Exception('Malformed request line')

        method, target, ver = words
        if ver != 'HTTP/1.1':
            raise Exception('Unexpected HTTP version')

        return method, target, ver

    def parse_headers(self, rfile):
        headers = []

        while True:
            line = rfile.readline(MAX_LINE + 1)
            if len(line) > MAX_LINE:
                raise Exception('Header line is too long')
            if line in (b'\r\n', b'\n', b''):
                break
            headers.append(line)
            if len(headers) > MAX_HEADERS:
                raise Exception('Too many headers')

        sheaders = b''.join(headers).decode('iso-8859-1')

        return Parser().parsestr(sheaders)

    def parse_request(self, conn):
        rfile = conn.makefile('rb')

        method, target, ver = self.parse_request_line(rfile)
        headers = self.parse_headers(rfile)

        host = headers.get('Host')
        if not host:
            raise Exception('Bad request')

        if host not in (self._server_name,
                        f'{self._server_name}:{self._port}'):
            raise Exception('Not found')

        return Request(method, target, ver, headers, rfile)

    def handle_post_users(self, request):
        user_id = len(self._users) + 1
        self._users[user_id] = {
            'id': user_id,
            'name': request.query['name'][0],
            'age': request.query['age'][0]
        }
        
        return Response(204, 'Created')

    def handle_get_users(self, request):
        accept = request.headers.get('Accept')
        if 'text/html' in accept:
            contenttype = 'text/html; charset=utf-8'
            body = '<html><head></head></html>'
            body += f'<div>Пользователи ({len(self._users)})</div>'
            body += '<ul>'
            for user in self._users.values():
                body += f'<li>#{user["id"]} {user["name"]}, {user["age"]}</li>'
            body += '</ul>'
            body += '</body></html>'

        elif 'application/json' in accept:
            contenttype = 'application/json; charset=utf-8'
            body = json.dumps(self._users)
        
        else:
            return Response(406, 'Not Acceptable')
        
        body = body.encode('utf-8')
        headers = [('Content-Type', contenttype),
                   ('Content-Length', len(body))]
            
        return Response(200, 'OK', headers, body)

    def handle_get_user(self, request, user_id):
        user = self._users.get(int(user_id))
        if not user:
            return Response(404, 'Not Found')

        accept = request.headers.get('Accept')
        if 'text/html' in accept:
            contenttype = 'text/html; charset=utf-8'
            body = f'<html><head></head></html>'
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

    def handle_request(self, request):
        if request.path == '/users' and request.method == 'POST':
            return self.handle_post_users(request)

        if request.path == '/users' and request.method == 'GET':
            return self.handle_get_users(request)

        if request.path.startswith('/users/'):
            user_id = request.path[len('/users/'):]
            if user_id.isdigit():
                return self.handle_get_user(request, user_id)

        raise Exception('Not found')

    def serve_client(self, conn: socket.socket) -> None:
        request = None
        try:
            request = self.parse_request(conn)
            response = self.handle_request(request)
            print(response)
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
    name = sys.argv[3]

    server = MyHTTPServer(host, port, name)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

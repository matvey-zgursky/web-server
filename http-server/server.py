import socket
import sys

MAX_LINE = 64*1024
MAX_HEADERS = 100


class Request:
    def __init__(self, method, target, version, headers, rfile) -> None:
        self.method = method
        self.target = target
        self.version = version
        self.headers = headers
        self.rfile = rfile

    def read_body(self):
        pass


class MyHTTPServer:
    def __init__(self, host, port, server_name) -> None:
        self._host = host
        self._port = port
        self._server_name = server_name

    def send_error(self, conn, error):
        pass

    def send_response(self, conn, response):
        pass

    def parse_request_line(self, rfile):
        raw = rfile.readline(MAX_LINE + 1)  # эффективно читаем строку целиком
        if len(raw) > MAX_LINE:
            raise Exception('Request line is too long')

        req_line = str(raw, 'iso-8859-1')
        req_line = req_line.rstrip('\r\n')
        words = req_line.split()            # разделяем по пробелу
        if len(words) != 3:                 # и ожидаем ровно 3 части
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
        
        return headers

    def parse_request(self, conn):
        rfile = conn.makefile('rb')
        method, target, ver = self.parse_request_line(rfile)
        headers = self.parse_headers(rfile)
        print(method, target, ver)
        print(headers)
        
        return Request(method, target, ver, headers, rfile)

    def serve_client(self, conn: socket.socket) -> None:
        try:
            request = self.parse_request(conn)
            response = self.handle_request(request)
            self.send_response(conn, response)
        except ConnectionResetError:
            conn = None
        except Exception as ex:
            self.send_error(conn, ex)

        if conn:
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

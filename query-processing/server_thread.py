import socket, sys, time, threading


def write_response(client_sock: socket.socket,
                   response: bytearray,
                   client_id: int) -> None:
    client_sock.sendall(response)
    client_sock.close()
    print(f'Client #{client_id} has been served')


def handler_request(request: bytearray) -> bytearray:
    time.sleep(20)
    return request[::-1]


def read_request(client_sock: socket.socket,
                 delimiter: bytes = b'!') -> bytearray | None:
    request = bytearray()
    try:
        while True:
            chunk = client_sock.recv(4)
            if not chunk:  # клиент преждевременно отключился
                return

            request += chunk
            if delimiter in request:
                return request
    except ConnectionResetError:  # соединение было неожиданно разорвано
        return
    except:
        raise


def serve_client(client_sock: socket.socket, client_id: int) -> None:
    request = read_request(client_sock)
    if request is None:
        print(f'Client #{client_id} unexpectedly disconnected')
    else:
        response = handler_request(request)
        write_response(client_sock, response, client_id)


def accept_client_conn(serv_sock: socket.socket,
                       client_id: int) -> socket.socket:
    client_sock, client_addr = serv_sock.accept()
    print(f'Client #{client_id} connected '
          f'{client_addr[0]}:{client_addr[1]}')
    return client_sock


def create_serv_sock(serv_port: int) -> socket.socket:
    serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto=0)
    serv_sock.bind(('', serv_port))
    serv_sock.listen()
    return serv_sock


def run_server(port: int = 53210) -> None:
    serv_sock = create_serv_sock(port)
    client_id = 0
    while True:
        client_sock = accept_client_conn(serv_sock, client_id)
        thread = threading.Thread(target=serve_client, args=(client_sock, client_id))
        thread.start()
        client_id += 1


if __name__ == '__main__':
    run_server(port=int(sys.argv[1]))

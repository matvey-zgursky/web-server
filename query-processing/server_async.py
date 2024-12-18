import asyncio, sys
from asyncio import StreamReader, StreamWriter


counter = 0


async def write_response(writer: StreamWriter, response: bytearray, client_id: int) -> None:
    writer.write(response)
    await writer.drain()
    writer.close()
    print(f'Client #{client_id} has been served')


async def handle_request(request: bytearray) -> bytearray:
    await asyncio.sleep(5)
    return request[::-1]


async def read_request(reader: StreamReader, deliniiter=b'!')  -> bytearray | None:
    request = bytearray()
    while True:
        chunk = await reader.read(4)
        if not chunk:
            break # Клиент преждевременно отключился.

        request += chunk
        if deliniiter in request:
            return request


async def serve_client(reader: StreamReader, writer: StreamWriter) -> None:
    global counter
    client_id = counter
    counter += 1 # Потоко-безопасно, т.k все выполняется в одном потоке
    print(f'Client {client_id} connected')

    request = await read_request(reader)
    if request is None:
        print(f'Client #{client_id} unexpectedly disconnected')
    else:
        response = await handle_request(request)
        await write_response(writer, response, client_id)


async def run_server(host: str, port: int = 53210) -> None:
    server = await asyncio.start_server(serve_client, host, port)
    await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(run_server('127.0.0.1', int(sys.argv[1])))

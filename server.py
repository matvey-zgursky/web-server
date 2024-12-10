import socket


serv_sock = socket.socket(socket.AF_INET,      # задамем семейство протоколов 'Интернет' (INET)
                          socket.SOCK_STREAM,  # задаем тип передачи данных 'потоковый' (TCP)
                          proto=0)             # выбираем протокол 'по умолчанию' для TCP, т.е. IP
serv_sock.bind(('127.0.0.1', 53210)) # указываем на каком IP и порту сервер будет слушать
backlog = 10 # размер очереди входящих соединений 
serv_sock.listen(backlog) # включаем режим слушания 


def main():
    while True: # Бесконечно обрабатываем входящие подключения
        client_sock, client_addr = serv_sock.accept() # передаем управление коду, когда появляется соединение в очереди
        print('Connected by', client_addr)

        while True: # Пока клиент не отключился, читаем передаваемые им данные и отправляем их обратно
            data = client_sock.recv(1024) # получаем сообщение 
            if not data:
                break # Клиент отключился
            client_sock.sendall(data) # отправляем сообщение клиенту
            print(data.decode('utf-8'))

        client_sock.close() # закрываем соединение 


if __name__ == '__main__':
    main()

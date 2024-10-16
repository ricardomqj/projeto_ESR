import socket
import sys

connectionsIP = []

def cliente():
    if len(sys.argv) != 2:
        print("Uso: python3 client.py <IP_SERVIDOR>")
        sys.exit(1)

    # IP do servidor como argumento
    server_ip = sys.argv[1]

    # Criação do socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Definir o endereço e a porta do servidor
    server_address = (server_ip, 65432)

    try:
        # Conectar ao servidor
        print(f"Conectando ao servidor {server_address}")
        client_socket.connect(server_address)

        # Obter o próprio IP do cliente
        client_ip = client_socket.getsockname()[0]

        # Enviar o IP para o servidor
        client_socket.sendall(client_ip.encode())
        print(f"IP {client_ip} enviado ao servidor.")

        while True:
            # Receber os dados do servidor (os IPs para se conectar)
            data = client_socket.recv(1024)
            if data:
                mensagem = data.decode()
                print(f"Mensagem do servidor: {mensagem}")

                connectionsIP = mensagem.split(', ')
            else:
                # Se não houver mais dados (servidor fechou a conexão), quebrar o loop
                print("Conexão com o servidor encerrada.")
                print(connectionsIP)
                break

    finally:
        client_socket.close()

if __name__ == "__main__":
    cliente()


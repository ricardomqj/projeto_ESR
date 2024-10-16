import socket
import threading

# Dicionário com os IPs de cada nó e os IPs para os quais o nó deve se conectar
nodes_conections = {
    '10.0.0.1': ['10.0.1.2'],
    '10.0.1.2': ['10.0.0.1', '10.0.10.1'],
    '10.0.10.1': ['10.0.10.2', '10.0.6.2'],
    '10.0.6.2': ['10.0.6.1', '10.0.12.20'],
    '10.0.12.20': ['10.0.12.1']
}

# Função que lida com o cliente em uma thread separada
def handle_client(connection, client_address):
    try:
        print(f"Conexão recebida de {client_address}")

        # Recebe a mensagem do cliente
        data = connection.recv(1024)
        if data:
            ip_cliente = data.decode()
            print(f"IP recebido: {ip_cliente}")

            # Verifica se o IP recebido está no dicionário
            if ip_cliente in nodes_conections:
                # Obtém os IPs aos quais o nó deve se conectar
                ips_a_ligar = nodes_conections[ip_cliente]

                # Envia os IPs para o nó
                mensagem = ', '.join(ips_a_ligar)  # Converte a lista de IPs para uma string separada por vírgulas
                print(f"Mensagem enviada para {client_address}: {mensagem}")

                # Envia a string para o cliente
                connection.sendall(mensagem.encode())
            else:
                print(f"IP {ip_cliente} não encontrado nas conexões.")
    finally:
        # Fecha a conexão após lidar com o cliente
        connection.close()

# Função do servidor que aceita conexões
def servidor():
    # Criação do socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Definir o endereço e a porta do servidor
    server_address = ('0.0.0.0', 65432)  # O servidor vai aceitar conexões de qualquer IP
    server_socket.bind(server_address)

    # Coloca o socket no modo de escuta
    server_socket.listen(5)
    print(f"Servidor ouvindo em {server_address}")

    while True:
        # Espera por uma conexão
        connection, client_address = server_socket.accept()

        client_thread = threading.Thread(target=handle_client, args=(connection, client_address))
        client_thread.start()

if __name__ == "__main__":
    servidor()

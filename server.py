import socket
import threading

# Dicionário com os IPs de cada nó e os IPs para os quais o nó deve se conectar
nodes_conections = {
    '10.0.0.1': ['10.0.0.10', '10.0.1.2'],
    '10.0.1.2': ['10.0.0.1', '10.0.10.1'],
    '10.0.10.1': ['10.0.1.2', '10.0.6.2'],
    '10.0.6.2': ['10.0.10.1', '10.0.12.20']
}

# Função que lida com o cliente em uma thread separada
def handle_client(client_address, server_socket, mensagem):
    try:
        if mensagem == "connecting":
            ip_cliente = client_address[0]
            print(f"IP recebido de {client_address}: {ip_cliente}")

            # Verifica se o IP recebido está no dicionário
            if ip_cliente in nodes_conections:
                # Obtém os IPs aos quais o nó deve se conectar
                ips_a_ligar = nodes_conections[ip_cliente]

                # Converte a lista de IPs para uma string separada por vírgulas
                mensagem = ', '.join(ips_a_ligar)
                print(f"Mensagem enviada para {client_address}: {mensagem}")

                # Envia a string de volta ao cliente
                server_socket.sendto(mensagem.encode(), client_address)
            else:
                print(f"IP {ip_cliente} não encontrado nas conexões.")
        else:
            print(mensagem)
    except Exception as e:
        print(f"Erro ao processar o cliente {client_address}: {e}")

# Função do servidor que aceita conexões
def servidor():
    # Criação do socket UDP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Definir o endereço e a porta do servidor
    server_address = ('0.0.0.0', 9090)  # O servidor vai aceitar conexões de qualquer IP
    server_socket.bind(server_address)

    print(f"Servidor UDP ouvindo em {server_address}")

    while True:
        # Recebe a mensagem do cliente e o endereço de onde veio
        data, client_address = server_socket.recvfrom(1024)

        mensagem = data.decode()
        print(mensagem)

        # Cria uma thread para lidar com o cliente
        client_thread = threading.Thread(target=handle_client, args=(client_address, server_socket, mensagem))
        client_thread.start()

if __name__ == "__main__":
    servidor()

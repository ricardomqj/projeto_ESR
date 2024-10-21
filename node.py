import socket
import sys
import threading

connectionsIP = []

def handle_connections(node_ip, forward_ip, porta):
    # Cria um socket UDP para este nó
    connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind do socket a um IP e porta locais (o nó vai ouvir nesta porta)
    local_address = ('0.0.0.0', porta) 
    connection_socket.bind(local_address)

    print(f"Esperando mensagens de {node_ip} para reencaminhar para {forward_ip}...")

    assigned_port = connection_socket.getsockname()[1]
    print(f"Socket vinculado a porta: {assigned_port}")

    while True:
        # Receber a mensagem do nó atual
        data, sender_address = connection_socket.recvfrom(1024)
        mensagem = data.decode()

        print(f"Mensagem recebida de {sender_address}: {mensagem}")

        # Enviar a mensagem para o nó com o qual está conectado
        connection_socket.sendto(mensagem.encode(), (forward_ip, porta))
        print(f"Mensagem reencaminhada para {forward_ip}")


def cliente():
    if len(sys.argv) != 2:
        print("Uso: python3 client.py <IP_SERVIDOR>")
        sys.exit(1)

    # IP do servidor como argumento
    server_ip = sys.argv[1]

    # Criação do socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
 
    client_ip = "connecting"

    try:
        mensagem = client_ip.encode()
        
        client_socket.sendto(mensagem, (server_ip, 9090))
        
        print(f"IP {client_ip} enviado ao servidor.")
        data, server = client_socket.recvfrom(1024)
        mensagem = data.decode()
        connectionsIP = mensagem.split(', ')

        
        mesage_thread = threading.Thread(target =handle_connections, args=(connectionsIP[0], connectionsIP[1], 9091))
        mesage_thread.start()

        mesage_thread = threading.Thread(target =handle_connections, args=(connectionsIP[1], connectionsIP[0], 9090))
        mesage_thread.start()

        while True:
            # Receber os dados do servidor (os IPs para se conectar)
            
            data, sender_address = client_socket.recvfrom(1024)

    finally:
        client_socket.close()

if __name__ == "__main__":
    cliente()

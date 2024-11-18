
import socket
import threading
from RtpPacket import RtpPacket
import ast, fcntl, struct

server_ip = "10.0.0.10"

clients_ip = ["10.0.17.20", "10.0.18.20", "10.0.19.20", "10.0.20.20"]

neighbors = []

def get_local_ip():
    """Get the local IP address of the client"""
    try:
        ifname = 'eth0'
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915, # SIOCGIFADDR
            struct.pack('256s', ifname.encode('utf-8')[:15])
        )[20:24])
        print(f"local ip obtained -> {ip}")
        return ip
    except Exception as e:
        print(f"Exception: {e}")

def is_rtp_packet(data):
    if len(data) < 22: # HEADER_SIZE IS CURRENTLY 22
        return False
    version = (data[0] >> 6) & 0x03
    return version == 2

def main():
    global neighbors
    local_ip = get_local_ip()
    if not local_ip:
        print("Failed to get local ip address. Exiting...")
        return
    node_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    node_socket.bind((local_ip, 9090))
    request = f"NODE REQUEST IP {local_ip}"
    try:
        node_socket.sendto(request.encode(), (server_ip, 9090))
        while True:
            response, addr = node_socket.recvfrom(20480)
            if response:
                #print(f"Received response -> {response}")
                if is_rtp_packet(response):
                    print(f"É um pacote RTP")
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(response)
                    packet_dest_ip = rtpPacket.getClientDestIP()
                    packet_frame_nbr = rtpPacket.seqNum()
                    print(f"Packet frame number -> {packet_frame_nbr}")
                    if packet_dest_ip in neighbors: # se o destinatário for um vizinho do node
                        print(f"Sending the RTP packet to the following address -> {(packet_dest_ip, 9090)}")
                        node_socket.sendto(response, (packet_dest_ip, 9090))
                        #print(f"IP do destinatário é meu vizinho, enviei o pacote para -> {(packet_dest_ip, 9090)}")
                    else: # se o destinatário não for vizinho deste node
                        for neighbor in neighbors:
                            if not addr[0] == neighbor: # não mandar o pacote de volta ao gajo que lhe mandou
                                try:
                                    node_socket.sendto(response, (neighbor, 9090))
                                    #print(f"Forwarding RTP packet to the address -> {(neighbor, 9090)}")
                                except: # caso o neighbor não esteja ligado prossegue e tenta mandar ao outro vizinho
                                    continue 

                elif response.decode().startswith("NP"): # se recebi uma resposta do servidor com os vizinhos
                    print(f"The response received starts with NP from the addr -> {addr}")
                    node_ip_dest = response.decode().split('|')[2]
                    if node_ip_dest == local_ip: # se for para mim
                        lista_vizinhos_str = response.decode().split('|')[1]
                        lista_vizinhos = ast.literal_eval(lista_vizinhos_str)
                        print(f"A minha lista de vizinhos é a seguinte: {lista_vizinhos}")
                        neighbors = lista_vizinhos
                    else: # se não for para mim redirecionar (usar addr )
                        for neighbor in neighbors:
                            if not addr[0] == neighbor:
                                try:
                                    node_socket.sendto(response, (neighbor, 9090))
                                    print(f"Forwarded RTP packet to the address -> {(neighbor, 9090)}")

                                except:
                                    continue

                elif response.decode().startswith("connecting"): # pedido de um cliente para enviar para o server
                    print(f"The response received starts with connecting from the addr -> {addr}")
                    print(f"->{response.decode()}<-")
                    server_addr = response.decode().split('|')[1]
                    filename = response.decode().split('|')[2]
                    client_ip = response.decode().split('|')[3]
                    if client_ip in neighbors and not client_ip == addr[0]:
                        node_socket.sendto(response, (client_ip, 9090))
                    else:
                        print("client_ip not in neighbours")
                        for neighbor in neighbors:
                            if not addr[0] == neighbor: # não mandar de volta
                                try:
                                    node_socket.sendto(response, (neighbor, 9090))
                                    print(f"Forwarded RTP packet to the address -> {(neighbor, 9090)}")
                                except:
                                    continue
                elif response.decode().startswith("NODE"): # caso receba um NODE REQUEST de um outro node
                    print(f"The response received starts with NODE from the addr -> {addr}")
                    for neighbor in neighbors: 
                        if not addr[0] == neighbor:
                            try:
                                node_socket.sendto(response, (neighbor, 9090))
                                print(f"Forwarded NODE REQUEST to the address -> {(neighbor, 9090)}")
                            except Exception as e:
                                print(f"Exception: {e}")
                                continue
                """
                else: # se for um pacote RTP vindo do server, do cliente e do nodo
                    print(f"The response received is probably an RTP packet from the addr -> {addr}")
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(response)
                    packet_dest_ip = rtpPacket.getClientDestIP()
                    if packet_dest_ip in neighbors: # se o destinatário for um vizinho do node
                        node_socket.sendto(response, (packet_dest_ip, 9090))
                        print(f"IP do destinatário é meu vizinho, enviei o pacote para -> {(packet_dest_ip, 9090)}")
                    else: # se o destinatário não for vizinho deste node
                        for neighbor in neighbors:
                            if not addr[0] == neighbor: # não mandar o pacote de volta ao gajo que lhe mandou
                                try:
                                    node_socket.sendto(response, (neighbor, 9090))
                                    print(f"Forwarding RTP packet to the address -> {(neighbor, 9090)}")
                                except: # caso o neighbor não esteja ligado prossegue e tenta mandar ao outro vizinho
                                    continue """
                
    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    main()
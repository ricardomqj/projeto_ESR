import socket, sys, threading
from RtpPacket import RtpPacket
from VideoStream import VideoStream
import os
import struct, fcntl
from random import randint

connections = {
    "10.0.0.10": ["10.0.0.1"],
    "10.0.0.1": ["10.0.0.10", "10.0.1.2", "10.0.2.2"],
    "10.0.2.2": ["10.0.0.1", "10.0.1.2", "10.0.5.2"],
    "10.0.1.2": ["10.0.0.1", "10.0.2.2", "10.0.5.2"],
    "10.0.5.2": ["10.0.2.2", "10.0.1.2", "10.0.10.2", "10.0.9.2"],
    "10.0.9.2": ["10.0.5.2", "10.0.17.20", "10.0.18.20", "10.0.19.20", "10.0.20.20"],
    "10.0.10.2": ["10.0.5.2", "10.0.17.20", "10.0.18.20", "10.0.19.20", "10.0.20.20"]
}

movies_list = {}

MOVIES_DIRECTORY = "movies/"
local_ip = None

def makeRtp(payload, frameNbr, ip_source, ip_dest, is_movie_request, file_found, sessionNumber):
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26 # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()
        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload, ip_dest, ip_source, is_movie_request, file_found, sessionNumber)

        return rtpPacket.getPacket()

def send_video_frame(filename, socket, ip_client, addr):
    videoStream = VideoStream(filename)
    data_frame = videoStream.nextFrame()
    sessionNumber = randint(100000, 999999)
    while data_frame:
        frameNumber = videoStream.frameNbr()
        try:
            rtpPacket = makeRtp(data_frame, frameNumber, local_ip, ip_client, False, True, sessionNumber)
            
            temp_packet = RtpPacket()
            temp_packet.decode(rtpPacket)
            temp_packet.printheader()
            
            print(f"[send_video_frame]sending the RTP packet to the follwing address -> {addr}")
            
            socket.sendto(rtpPacket, addr)
        except Exception as e:
            print(f"Failed to send RTP packet: {e}")
            continue
        data_frame = videoStream.nextFrame()

def get_local_ip():
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

def handle_connection(data, addr, local_ip):
    print(f"Starting handle connection with {data}, {addr}, {local_ip}")
    connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    connection_socket.bind((local_ip, 9091))
    if data.startswith("connecting"):
        print(f"Received a connecting request")
        message_fields = data.split('|')
        server_addr = message_fields[1]
        filename = message_fields[2]
        client_ip = message_fields[3]
        print(f"[handle_connection] message_fields -> {message_fields}")
        if not os.path.exists(filename): # o ficheiro pedido não existe
            print(f"O ficheiro {filename} pedido por {client_ip} não existe")
            rtpPacket = makeRtp('', 0, server_addr, client_ip, False, False, -1)
            print(f"Number of bytes that the RTP packet has -> {len(rtpPacket)}")
            connection_socket.sendto(rtpPacket, addr)
        else: # o ficheiro existe
            send_video_frame(filename, connection_socket, client_ip, addr)
    elif data.startswith("NODE"):
        print("Received a node connect request")
        node_ip = data.split()[3]
        print(f"[handle_connection] node_ip extracted -> ({node_ip})")
        if node_ip in connections:
            neighbors = connections[node_ip]
            neighbors_str = str(neighbors)
            res = f"NP|{neighbors_str}|{node_ip}"
            dest_ip = connections[local_ip][0]
            print(f"[handle_connection] sending -> ({res}) to the follwing addr -> ({(dest_ip, 9090)})")
            connection_socket.sendto(res.encode(), (dest_ip, 9090))
    else: # recebeu outra coisa sem ser pedido de conexão do servidor e do cliente
        print(f"Pedido recebido com formato inválido -> {data}")
    
def main():
    global local_ip
    local_ip = get_local_ip()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((local_ip, 9090))
    while True:
        data, addr = server_socket.recvfrom(2048)
        if data:
            print(f"Received on PORT 9090: -> {data}")
            threading.Thread(target=handle_connection, args=(data.decode(), addr, local_ip)).start()

if __name__ == "__main__":
    main()

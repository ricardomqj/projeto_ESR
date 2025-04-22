from asyncio import sleep
import socket, os
import threading
from random import randint
import heapq
from typing import Dict, Set, List, Tuple
import logging
import time
from RtpPacket import RtpPacket
from VideoStream import VideoStream
import threading

class NetworkManager:
    def __init__(self, port: int = 9090):
        self.port = port
        self.nodes_network: Set[str] = {"10.0.0.10"}  # IP do server na topologia !!!
        self.server_socket = None
        
        self.stream_statuses: Dict[str, Dict[str, Dict[str, str]]] = {}
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.nodes_connections: Dict[str, Dict[str, float]] = {
            "10.0.0.10":{
                "10.0.0.1":1.0
            },
            "10.0.0.1": {
                "10.0.0.10": 1.0,  
                "10.0.1.2": 1.0,
                "10.0.3.2":1.0 
            },
            "10.0.1.2": {
                "10.0.0.1": 1.0,  
                "10.0.11.2": 1.0 ,
                "10.0.2.1": 1.0,
                "10.0.3.2": 1.0  
            },
            "10.0.2.1": {
                "10.0.1.2": 1.0,  
                "10.0.11.2": 1.0,
                "10.0.3.2": 1.0,
                "10.0.20.2": 1.0   
            },
            "10.0.11.2": {
                "10.0.2.1": 1.0,  
                "10.0.1.2": 1.0,
                "10.0.3.2": 1.0,
                "10.0.4.2": 1.0,
                "10.0.6.2": 1.0  
            },
            "10.0.3.2": {
                "10.0.1.2": 1.0,
                "10.0.11.2": 1.0,  
                "10.0.4.2": 1.0, 
                "10.0.6.2": 1.0,
                "10.0.2.1": 1.0
            },
            "10.0.4.2": {
                "10.0.3.2": 1.0,
                "10.0.11.2": 1.0
            },
            "10.0.6.2": {
                "10.0.11.2": 1.0,
                "10.0.3.2": 1.0,
                "10.0.21.2":1.0
            },
            "10.0.20.2" : {
                "10.0.2.1": 1.0,
                "10.0.21.2": 1.0
            },
            "10.0.21.2": {
                "10.0.20.2": 1.0,
                "10.0.6.2": 1.0
            }
        }
        self.nodes_acess_points = {"10.0.6.2": [[],[]], "10.0.4.2": [[],[]]} 

    def dijkstra(self, graph: Dict[str, Dict[str, float]], start_node: str) -> Tuple[Dict[str, float], Dict[str, str]]:
        """Implementation of Dijkstra's algorithm for finding shortest paths."""
        print("Inside dijkstra")
        distances = {node: float('inf') for node in graph}
        distances[start_node] = 0
        priority_queue = [(0, start_node)]
        predecessors = {node: None for node in graph}

        while priority_queue:
            print("[dijkstra] Inside while loop")
            current_distance, current_node = heapq.heappop(priority_queue)
            print(f"current_distance: {current_distance}, current_node: {current_node}")

            if current_distance > distances[current_node]:
                continue

            for neighbor, weight in graph[current_node].items():
                if neighbor in self.nodes_network:
                    
                    print(f"Inside dijkstra(if neighb...), current_node: {current_node}, neighbor: {neighbor}, weight: {weight}")
                    distance = current_distance + weight
                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        predecessors[neighbor] = current_node
                        heapq.heappush(priority_queue, (distance, neighbor))

        print(f"Returning distances: {distances} and predecessors: {predecessors}")
        return distances, predecessors

    def makeRtp(self, payload, frameNbr, ip_source, ip_dest, is_movie_request, file_found, sessionNumber, filename):
        # Check if payload is a fragmented frame
        if payload and b'|' in payload[:50]:
            try:
                # Split the payload into fragments
                parts = payload.split(b'|', 3)
                
                # Ensure we have enough parts
                if len(parts) < 4:
                    print(f"Invalid fragment format. Parts: {len(parts)}")
                    # Return a default RTP packet or handle the error
                    return self._create_default_rtp_packet(
                        frameNbr, ip_source, ip_dest, 
                        is_movie_request, file_found, 
                        sessionNumber, filename
                    )
                
                # Parse fragment metadata
                total_fragments = int(parts[0])
                fragment_index = int(parts[1])
                total_frame_size = int(parts[2])
                actual_payload = parts[3]
                
                # Create RTP packet with fragmentation details
                rtpPacket = RtpPacket()
                rtpPacket.encode(2, 0, 1, 0, frameNbr, 1 if fragment_index == total_fragments - 1 else 0, 26, 0, actual_payload, ip_dest, ip_source, is_movie_request, file_found, sessionNumber, filename)
                return rtpPacket.getPacket()
            
            except (ValueError, IndexError) as e:
                print(f"Error processing fragment: {e}")
                # Create a default RTP packet if parsing fails
                return self._create_default_rtp_packet(
                    frameNbr, ip_source, ip_dest, 
                    is_movie_request, file_found, 
                    sessionNumber, filename
                )
        
        # For non-fragmented payloads, use existing packet creation
        rtpPacket = RtpPacket()
        rtpPacket.encode(2, 0, 0, 0, frameNbr, 0, 26, 0, payload, ip_dest, ip_source, is_movie_request, file_found, sessionNumber, filename)
        return rtpPacket.getPacket()

    def _create_default_rtp_packet(self, frameNbr, ip_source, ip_dest, is_movie_request, file_found, sessionNumber, filename):
        """
        Create a default RTP packet when fragment parsing fails.
        """
        rtpPacket = RtpPacket()
        rtpPacket.encode(2, 0, 0, 0, frameNbr, 0, 26, 0, b'', ip_dest, ip_source, is_movie_request, False, sessionNumber, filename)
        return rtpPacket.getPacket()

    def send_predecessors_along_path(self, path: List[str], predecessors: Dict[str, str], stream_name, ip_dest) -> None:
        
        print("inside send_predecessors_along_path function")
        print(f"path: {path}")
        print(f"predecessors: {predecessors}")
        for node in path:
            # Get the predecessor for this node
            predecessor = predecessors.get(node)
            
            if predecessor:
                # Create the message with predecessor information
                node_address = (node, 9091)

                message = f"{stream_name}|{predecessor}|{ip_dest}"
                
                try:
                    self.logger.info(f"[send_predecessors_along_path] Sending message {message} to {node_address}")    
                    self.server_socket.sendto(message.encode(), node_address)
                    self.logger.info(f"Sent predecessor {predecessor} to node {node}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to send predecessor to {node}: {e}")
            else:
                self.logger.info(f"No predecessor for node {node}")


    def create_tree(self) -> Dict[str, Dict[str, float]]:
        connections = {}

        for node in self.nodes_network:
            connections[node] = {
                neighbor: weight 
                for neighbor, weight in self.nodes_connections[node].items()
                if neighbor in self.nodes_network
            }
            
        return connections

    def connect_new_node(self, client_ip):
        self.logger.info(f"New connection from {client_ip}")

        # Add node to network and initialize connections
        self.nodes_network.add(client_ip)
        self.logger.info(f"Node added to nodes_network list! Current list -> {self.nodes_network}")

        # Create connection tree
        connection_tree = self.create_tree()

        print(f"A connection_tree está {connection_tree}")
        
        node_adress = (client_ip , 9091)   
        response = 'sucesso'

        self.server_socket.sendto(response.encode(), node_adress)
        
        for node_acess_point in self.nodes_acess_points:

            if client_ip == node_acess_point:  
                distances, predecessors = self.dijkstra(connection_tree, "10.0.0.10") # Aqui temos o IP fixo porque já sabemos que vai sair sempre do node do server
                
                # Debug prints
                print("Full predecessors dictionary:")
                for node, pred in predecessors.items():
                    print(f"{node} -> {pred}")

                path = []

                current_node = client_ip
                while current_node is not None:
                    print(f"current _node está {current_node} com prodecessor {predecessors[current_node]}")
                    path.insert(0, current_node)
                    current_node = predecessors[current_node]
                
                print(f"O access point {client_ip} ficou com o caminho  {path}")

                self.nodes_acess_points[client_ip] = [path,predecessors]

            elif len(self.nodes_acess_points[node_acess_point][0]) > 0:
                distances, predecessors = self.dijkstra(connection_tree, "10.0.0.10") # Aqui temos o IP fixo porque já sabemos que vai sair sempre do node do server

                path = []
                current_node = node_acess_point
                
                while current_node is not None:

                    if current_node not in predecessors:
                        print(f"[ERROR] Nó {current_node} não tem predecessor. Caminho inválido!")
                        path = []  # Limpa o caminho inválido
                        break
                    path.insert(0, current_node)
                    current_node = predecessors[current_node]

                # Validar se o caminho reconstrói até o nó inicial
                if path and path[0] != "10.0.0.10":
                    print(f"[ERROR] Caminho reconstruído não conecta ao servidor: {path}")
                    path = []

                elif len(self.nodes_acess_points[node_acess_point][0]) > len(path):
                    print(f"O access point {node_acess_point} ficou com o caminho  {path}")
                    self.nodes_acess_points[node_acess_point] = [path,predecessors]

                    #self.send_predecessors_along_path(path, predecessors)


    def handle_client(self, client_address: Tuple[str, int], message: str) -> None:
        """Handle incoming client connections and messages."""

        sessionNumber = None
        first_packet_sent = False

        print(f"Received message from {client_address}: {message}")
        if message == "connecting":
            client_ip = client_address[0]
            self.connect_new_node(client_ip)

        elif '|' in message:
            message_info = message.split("|")
            print(f"Message info: {message_info}")
            client_ip = client_address[0]

            if message_info[0] == "start_stream":
                #print("Recebi um start stream request")
                stream_name = message_info[1]
                client_requested_ip  = message_info[2]
                print(f"Recebi um start_stream request de {client_address[0]}:{client_address[1]} para o stream {stream_name} para o ip {client_requested_ip}")
                self.send_predecessors_along_path(self.nodes_acess_points[client_ip][0],self.nodes_acess_points[client_ip][1], stream_name, client_requested_ip)

            elif message_info[0] == "teardown":
                # Handle teardown request
                stream_name = message_info[1]
                client_ip = message_info[2]

                # Update stream status to NOT_PLAYING
                if stream_name in self.stream_statuses:
                    if client_ip in self.stream_statuses[stream_name]:
                        self.stream_statuses[stream_name][client_ip]['status'] = 'NOT_PLAYING'
                        print(f"Stream {stream_name} for client {client_ip} set to NOT_PLAYING")

            elif message_info[0] == "stream_request":
                client_requested_ip = message_info[2]

                stream_name = message_info[1]

                filename = "movie.Mjpeg"

                node_adress = (client_ip , 9090)  

                print(f"Recebi um start_stream request de {client_address[0]}:{client_address[1]} para a stream {stream_name} para o ip {client_requested_ip}")

                if sessionNumber is None and not first_packet_sent:
                    sessionNumber = randint(100000, 999999)
                    first_packet_sent = True
                
                if stream_name not in self.stream_statuses:
                    self.stream_statuses[stream_name] = {}

                self.stream_statuses[stream_name][client_requested_ip] = {
                    'status': 'PLAYING',
                    'sessionNumber': sessionNumber
                }

                if os.path.exists(stream_name):
                    print(f"Vou começar a enviar os frames do ficheiro {filename} para {node_adress}")
                    videoStream = VideoStream(stream_name)
                    data_frame = videoStream.nextFrame()
                    while data_frame:
                        # Check if stream status is still PLAYING for this client
                        stream_status = self.stream_statuses[stream_name].get(client_requested_ip, {}).get('status', 'NOT_PLAYING')
                        if stream_status != 'PLAYING':
                            print(f"Stopping stream for {client_requested_ip} - status is {stream_status}")
                            break
                        
                        frameNumber = videoStream.frameNbr()
                        try:
                            rtpPacket = self.makeRtp(data_frame, frameNumber, '10.0.0.10', client_requested_ip, False, True, sessionNumber, stream_name)

                            print(f"[handle_client] Sending RTP packet {frameNumber} to {client_ip} | asked by {client_address} | Thread -> |{threading.current_thread().name}|")

                            temp_rtp_packet = RtpPacket()
                            temp_rtp_packet.decode(rtpPacket)
                            
                            print(f"Frame {temp_rtp_packet.seqNum()} gerado, tamanho, {len(temp_rtp_packet.getPayload())} bytes")

                            total_bytes = len(rtpPacket)
                            print(f"Total nbr of bytes of the packet that is being sent: {total_bytes} bytes!")
                            if (temp_rtp_packet.getSessionNumber() == sessionNumber and
                                self.stream_statuses[stream_name][client_requested_ip]['status'] == 'PLAYING'):
                                self.server_socket.sendto(rtpPacket, node_adress)

                            time.sleep(1/30)

                        except Exception as e:
                            print(f"Failed to send RTP packet: {e}")
                            continue
                        data_frame = videoStream.nextFrame()
                else:
                    try:
                        print(f"O ficheiro {filename} pedido por {client_ip} não foi encontrado")
                    except Exception as e:
                        print(f"Failed to send response to {client_ip}: {e}")

        else:
            self.logger.info(f"Received message from {client_address}: {message}")


    def handle_teardown_requests(self):
        while True:
            try:
                data, client_address = self.teardown_socket.recvfrom(1024)
                message = data.decode()
                message_info = message.split('|')

                if message_info[0] == "teardown":
                    stream_name = message_info[1]
                    client_ip = message_info[2]

                    # Update stream status to NOT_PLAYING
                    if stream_name in self.stream_statuses:
                        if client_ip in self.stream_statuses[stream_name]:
                            self.stream_statuses[stream_name][client_ip]['status'] = 'NOT_PLAYING'
                            print(f"Stream")

            except Exception as e:
                self.logger.error(f"Error in teardown request handler: {str(e)}")

    def start_server(self) -> None:
        """Start the UDP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = ('10.0.0.10', self.port)
        self.server_socket.bind(server_address)
        self.logger.info(f"UDP Server listening on port {self.port}")

        self.teardown_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.teardown_socket.bind(('10.0.0.10', 9091))

        # Criar uma thread para lidar com pedidos na porta 9091
        teardown_thread = threading.Thread(target=self.handle_teardown_requests)
        teardown_thread.daemon = True
        teardown_thread.start()

        while True:
            try:
                data, client_address = self.server_socket.recvfrom(1024)
                message = data.decode()
                print(f"Received message from {client_address}: {message}")
                if not client_address[0] == "10.0.0.10":
                    # Create a thread to handle the client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_address, message)
                    )
                    client_thread.daemon = True
                    print(f"starting -> {client_thread.name} with the message {message} from {client_address}")
                    client_thread.start()

            except Exception as e:
                self.logger.error(f"Server error: {str(e)}")

if __name__ == "__main__":
    network_manager = NetworkManager()
    network_manager.start_server()
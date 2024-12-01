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
                "10.0.11.2": 1.0   
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
                "10.0.3.2": 1.0 
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
                distances, predecessors = self.dijkstra(connection_tree, node_acess_point)

                path = []
                current_node = client_ip
                while current_node is not None:
                    path.insert(0, current_node)
                    current_node = predecessors[current_node]

                if len(self.nodes_acess_points[node_acess_point][0]) > len(path):
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
                #print(message)

                #print(f"Sending the path to the send_predecessors_along_path function:")
                #print(f"path: {self.nodes_acess_points[client_ip][0]}")
                #print("_________________________________________________________")
                #print(f"full nodes_acess_points: {self.nodes_acess_points}")
                #print("_________________________________________________________")
                self.send_predecessors_along_path(self.nodes_acess_points[client_ip][0],self.nodes_acess_points[client_ip][1], stream_name, client_requested_ip)
                
                #print("IPs enviados para os nodes")

            if message_info[0] == "stream_request":
                #print("Recebi um stream request")
                #print(f"Message info: {message_info}")
                client_requested_ip = message_info[2]

                stream_name = message_info[1]

                # FAZ AQUI O CODIGO PARA ELE COMEÇAR A MANDAR AS CENAS PARA O NODE QUE LHE PEDIU, DEPOIS TRATAR DE NO NODE ELE ENVIAR A QUEM PEDIU
                #response = "movie.Mjpeg"

                #print(f"Sending the text {response} to {client_ip}")

                filename = "movie.Mjpeg"

                node_adress = (client_ip , 9090)  

                if sessionNumber is None and not first_packet_sent:
                    sessionNumber = randint(100000, 999999)
                    first_packet_sent = True
                
                if os.path.exists(stream_name):
                    print(f"Vou começar a enviar os frames do ficheiro {filename} para {node_adress}")
                    videoStream = VideoStream(stream_name)
                    data_frame = videoStream.nextFrame()
                    while data_frame:
                        frameNumber = videoStream.frameNbr()
                        try:
                            #print(f"frameNumber: {frameNumber}|client_requested_ip: {client_requested_ip}|sessionNumber: {sessionNumber}")
                            rtpPacket = self.makeRtp(data_frame, frameNumber, '10.0.0.10', client_requested_ip, False, True, sessionNumber, stream_name)

                            print(f"[handle_client] Sending RTP packet {frameNumber} to {client_ip} | asked by {client_address} | Thread -> |{threading.current_thread().name}|")

                            temp_rtp_packet = RtpPacket()
                            temp_rtp_packet.decode(rtpPacket)
                            
                            total_bytes = len(rtpPacket)
                            print(f"Total nbr of bytes of the packet that is being sent: {total_bytes} bytes!")
                            if temp_rtp_packet.getSessionNumber() == sessionNumber:
                                self.server_socket.sendto(rtpPacket, node_adress)

                            time.sleep(1/30)

                        except Exception as e:
                            print(f"Failed to send RTP packet: {e}")
                            continue
                        data_frame = videoStream.nextFrame()
                else:
                    try:
                        print(f"O ficheiro {filename} pedido por {client_ip} não foi encontrado")
                        #response = self.makeRtp('', 0, '10.0.0.10', client_requested_ip, False, False, sessionNumber)
                        #self.server_socket.sendto(response, node_adress)
                        #print(f"Sent response {response} to {client_ip}")
                    except Exception as e:
                        print(f"Failed to send response to {client_ip}: {e}")

        else:
            self.logger.info(f"Received message from {client_address}: {message}")


    def start_server(self) -> None:
        """Start the UDP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = ('10.0.0.10', self.port)
        self.server_socket.bind(server_address)
        self.logger.info(f"UDP Server listening on port {self.port}")

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

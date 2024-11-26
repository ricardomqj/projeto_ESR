import socket
import threading
import heapq
from typing import Dict, Set, List, Tuple
import logging
import time

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
        distances = {node: float('inf') for node in graph}
        distances[start_node] = 0
        priority_queue = [(0, start_node)]
        predecessors = {node: None for node in graph}

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_distance > distances[current_node]:
                continue

            for neighbor, weight in graph[current_node].items():
                distance = current_distance + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    predecessors[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))

        return distances, predecessors

    def send_predecessors_along_path(self, path: List[str], predecessors: Dict[str, str], stream_name) -> None:

        for node in path:
            # Get the predecessor for this node
            predecessor = predecessors.get(node)
            
            if predecessor:
                # Create the message with predecessor information
                node_address = (node, 9091)

                message = f"{stream_name}|{predecessor}"
                
                try:
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

        # Create connection tree
        connection_tree = self.create_tree()

        print(f"A connection_tree está {connection_tree}")
        
        node_adress = (client_ip , 9091)   
        response = 'sucesso'

        self.server_socket.sendto(response.encode(), node_adress)
        
        for node_acess_point in self.nodes_acess_points:

            if client_ip == node_acess_point:  
                distances, predecessors = self.dijkstra(connection_tree, "10.0.0.10") # Aqui temos o IP fixo porque já sabemos que vai sair sempre do node do server
                
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

        if message == "connecting":
            client_ip = client_address[0]
            self.connect_new_node(client_ip)

        if '|' in message:
            message_info = message.split("|")
            
            if message_info[0] == "start_stream":
                client_ip = client_address[0]

                stream_name = message_info[1]
                client_requested_ip  = message_info[2]

                print(message)

                self.send_predecessors_along_path(self.nodes_acess_points[client_ip][0],self.nodes_acess_points[client_ip][1], stream_name)
                
                print("IPs enviados para os nodes")

            if message_info[0] == "stream_request":
                client_ip = client_address[0]

                # FAZ AQUI O CODIGO PARA ELE COMEÇAR A MANDAR AS CENAS PARA O NODE QUE LHE PEDIU, DEPOIS TRATAR DE NO NODE ELE ENVIAR A QUEM PEDIU
                while True:
                    response = "movie.Mjpeg"

                    node_adress = (client_ip , 9090)   
                    self.server_socket.sendto(response.encode(), node_adress)
                    
                    time.sleep(4)

        else:
            self.logger.info(f"Received message from {client_address}: {message}")


    def start_server(self) -> None:
        """Start the UDP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = ('0.0.0.0', self.port)
        self.server_socket.bind(server_address)
        self.logger.info(f"UDP Server listening on port {self.port}")

        while True:
            try:
                data, client_address = self.server_socket.recvfrom(1024)
                message = data.decode()
                
                # Create a thread to handle the client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_address, message)
                )
                client_thread.start()

            except Exception as e:
                self.logger.error(f"Server error: {str(e)}")

if __name__ == "__main__":
    network_manager = NetworkManager()
    network_manager.start_server()

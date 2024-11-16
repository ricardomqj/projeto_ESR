import socket
import threading
import heapq
from typing import Dict, Set, List, Tuple
import logging

class NetworkManager:
    def __init__(self, port: int = 9090):
        self.port = port
        self.nodes_network: Set[str] = {"10.0.0.10"}  # IP do server na topologia !!!
        self.server_socket = None
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.nodes_connections: Dict[str, Dict[str, float]] = {
            "10.0.0.1": {
                "10.0.0.10": 1.0,  
                "10.0.1.2": 1.0   
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
                "10.0.6.2": 1.0
            },
            "10.0.3.2": {
                "10.0.1.2": 1.0,
                "10.0.11.2": 1.0,  
                "10.0.4.2": 1.0, 
                "10.0.6.2": 1.0
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

    def create_tree(self) -> Dict[str, List[str]]:
        """Create a connection tree for all nodes in the network."""
        connections = {}
        for node in self.nodes_network:
            connections[node] = [
                neighbor for neighbor in self.nodes_connections[node]
                if neighbor in self.nodes_network
            ]
        return connections

    def handle_client(self, client_address: Tuple[str, int], message: str) -> None:
        """Handle incoming client connections and messages."""
        try:
            if message == "connecting":
                client_ip = client_address[0]
                self.logger.info(f"New connection from {client_ip}")

                # Add node to network and initialize connections
                self.nodes_network.add(client_ip)

                # Create connection tree
                connection_tree = self.create_tree()

                print(f"A connection_tree está {connection_tree}")
                
                for node in self.nodes_network:
                    # Get neighbors for the new node
                    neighbors = connection_tree.get(node, [])
                    
                    # Send neighbor information back to client
                    if neighbors:
                        node_adress = (node , 9091)
                        
                        response = ','.join(neighbors)
                        self.server_socket.sendto(response.encode(), node_adress)
                        self.logger.info(f"Sent neighbors to {node}: {response}")
                    else:
                        node_adress = (node , 9091)
                        self.logger.info(f"No neighbors found for {client_ip}")
                        self.server_socket.sendto(b"no_neighbors", node_adress)

            else:
                self.logger.info(f"Received message from {client_address}: {message}")

        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {str(e)}")

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

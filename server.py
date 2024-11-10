import socket
import threading
import heapq
from typing import Dict, Set, List, Tuple
import logging

class NetworkManager:
    def __init__(self, port: int = 9090):
        self.port = port
        self.nodes_network: Set[str] = set()  # Set of IP addresses
        self.nodes_connections: Dict[str, Dict[str, float]] = {}  # Graph representation
        self.server_socket = None
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def initialize_node_connections(self, new_node: str) -> None:
        """Initialize connections for a new node with default weights."""
        if new_node not in self.nodes_connections:
            self.nodes_connections[new_node] = {}
            
        # Connect new node to all existing nodes with a default weight
        for existing_node in self.nodes_network:
            if existing_node != new_node:
                # Add bidirectional connections with default weight of 1
                self.nodes_connections[new_node][existing_node] = 1
                if existing_node not in self.nodes_connections:
                    self.nodes_connections[existing_node] = {}
                self.nodes_connections[existing_node][new_node] = 1

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
            distances, predecessors = self.dijkstra(self.nodes_connections, node)
            # Get direct neighbors for each node
            connections[node] = [
                neighbor for neighbor, pred in predecessors.items()
                if pred == node or predecessors[neighbor] == node
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
                self.initialize_node_connections(client_ip)

                # Create connection tree
                connection_tree = self.create_tree()
                
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

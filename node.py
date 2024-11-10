import socket
import sys
import threading
import time

class NetworkClient:
    def __init__(self):
        self.connections_ip = []
        self.server_socket = None
        self.connection_socket = None
        self.is_connected = False

    def handle_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_address = ('0.0.0.0', 9091)
        self.server_socket.bind(local_address)

        while True:
            try:
                data, server = self.server_socket.recvfrom(1024)
                message = data.decode()

                if message == "connected":
                    self.is_connected = True
                    print("Successfully connected to network")
                    continue

                self.connections_ip = message.split(',')
                print(f"Updated connections: {self.connections_ip}")
            except Exception as e:
                print(f"Error in server handler: {e}")

    def handle_connections(self):
        self.connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_address = ('0.0.0.0', 9090)
        self.connection_socket.bind(local_address)

        while True:
            try:
                data, sender_address = self.connection_socket.recvfrom(1024)
                message = data.decode()
                print(f"Message received from {sender_address}: {message}")

                # Forward message to first available connection
                for ip in self.connections_ip:
                    if ip.strip() != sender_address[0]:
                        self.connection_socket.sendto(message.encode(), (ip.strip(), 9090))
                        print(f"Message forwarded to {ip}")
                        break
            except Exception as e:
                print(f"Error in connection handler: {e}")

    def start(self, server_ip: str):
        if not server_ip:
            print("Usage: python3 client.py <SERVER_IP>")
            return

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # Start server handler thread
            server_thread = threading.Thread(target=self.handle_server)
            server_thread.daemon = True
            server_thread.start()

            # Start connection handler thread
            connection_thread = threading.Thread(target=self.handle_connections)
            connection_thread.daemon = True
            connection_thread.start()

            # Send initial connection message
            client_socket.sendto(b"connecting", (server_ip, 9090))
            print("Connection request sent to server")

            # Wait for connection confirmation
            timeout = 10
            start_time = time.time()
            while not self.is_connected and time.time() - start_time < timeout:
                time.sleep(0.1)


            # Keep main thread alive
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nShutting down client...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 client.py <SERVER_IP>")
        sys.exit(1)

    client = NetworkClient()
    client.start(sys.argv[1])

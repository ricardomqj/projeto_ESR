import socket
import sys
import threading
import time
import asyncio

class NetworkClient:
    def __init__(self):
        self.connections_ip = {}
        self.stream_requests = {}
        self.server_socket = None
        self.connection_socket = None
        self.is_connected = False
        self.server_ip = 0

    def request_streams(self, stream_name):
        try:

            current_connection = self.connections_ip[stream_name]
            
            try:
                message = f"stream_request|{stream_name}"

                print(f"Requesting stream {stream_name} from {current_connection}")
                
                # Send request to the target node
                if current_connection == "10.0.0.10":
                    self.connection_socket.sendto(message.encode(), (current_connection, 9090)) # verificação feita porque o server está ouvir numa porta diferente dos nodes
                else:
                    self.connection_socket.sendto(message.encode(), (current_connection, 9091))
                
            except Exception as e:
                print(f"Error requesting stream {stream_name}: {e}")
            
        except Exception as e:
            print(f"Error in stream request handler: {e}")
            time.sleep(1)  # Wait before retrying if there's an error

    def handle_server_client(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_address = ('0.0.0.0', 9091)
        self.server_socket.bind(local_address)

        while True:
            data, sender_address = self.server_socket.recvfrom(1024)
            message = data.decode()
            sender_ip, sender_port = sender_address  

            if message == "sucesso":
                print('Adicionado com sucesso')

            else:
                message_info = message.split('|')

                if message_info[0] == "request":
                    stream_name = message_info[1]
                    client_ip = message_info[2]
                    message = f"start_stream|{stream_name}|{client_ip}"
                    print(f"-> {message}<-")

                    self.server_socket.sendto(message.encode(), (self.server_ip, 9090))

                    if stream_name not in self.stream_requests:
                        self.stream_requests[stream_name] = [client_ip]

                    else:
                        self.stream_requests[stream_name].append(client_ip)
                        
                elif message_info[0] == "stream_request":
                    stream_name = message_info[1]

                    if stream_name not in self.stream_requests:

                        connection_thread = threading.Thread(target=self.request_streams(stream_name))
                        connection_thread.daemon = True
                        connection_thread.start()

                        self.stream_requests[stream_name] = [sender_ip]
                    
                    else:
                        self.stream_requests[stream_name].append([sender_ip])
                    
                else:
                    stream_name = message_info[0] 

                    if stream_name not in self.connections_ip:

                        self.connections_ip[stream_name] = message_info[1]
                        print(f"Adicionada a nova conexão: {self.connections_ip}")

                        connection_thread = threading.Thread(target=self.request_streams(stream_name))
                        connection_thread.daemon = True
                        connection_thread.start()
                        
                    else:
                        print("Já estou a transmitir essa stream")


    def handle_requests(self):
        self.connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_address = ('0.0.0.0', 9090)
        self.connection_socket.bind(local_address)

        while True:
            try:
                data, sender_address = self.connection_socket.recvfrom(1024)
                message = data.decode()

                if message in self.stream_requests:
                    for node_ip in self.stream_requests[message]:
                        
                        node_adress = (node_ip , 9090)  
                        print(f"mensagem --> {message}") 
                        
                        message_enconded = message.encode()
                        self.connection_socket.sendto(message_enconded, node_adress)

                        #print(f"Enviei agora para {node_address}")
                else:
                    print(f"A stream {message} não está presente")
            except Exception as e:
                print(f"Error in connection handler: {e}")

    def start(self, server_ip: str):
        if not server_ip:
            print("Usage: python3 node.py <SERVER_IP>")
            return

        self.server_ip = server_ip

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # Start server handler thread
            server_thread = threading.Thread(target=self.handle_server_client)
            server_thread.daemon = True
            server_thread.start()

            # Start connection handler thread
            connection_thread = threading.Thread(target=self.handle_requests)
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

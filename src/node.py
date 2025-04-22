import socket
import sys
import threading
import time
import asyncio
from RtpPacket import RtpPacket

class NetworkClient:
    def __init__(self):
        self.connections_ip = {}
        self.stream_requests = {}
        self.server_socket = None
        self.connection_socket = None
        self.is_connected = False
        self.server_ip = 0
        self.predecessor_ip = ''

    def request_streams(self, stream_name, ip_dest):
        # client dest_ip é usado apenas se for um pedido de stream
            print(f"[request_streams] received_predecessor: True")
            current_connection = self.connections_ip[stream_name]
            try:
                message = f"stream_request|{stream_name}|{ip_dest}"
                print(f"Requesting stream {stream_name} to {(current_connection, 9090)}")
                print(f"Whit  stream request: {self.stream_requests}\n ")
                # send request to the target node
                print(f"self.connections_ip[stream_name] == {self.connections_ip[stream_name]}")

                if self.connections_ip[stream_name] == "10.0.0.10":
                    self.connection_socket.sendto(message.encode(), (self.connections_ip[stream_name], 9090))
                    pass
                else:
                    self.connection_socket.sendto(message.encode(), (self.connections_ip[stream_name], 9091))

            except Exception as e:
                print(f"Error requesting stream {stream_name}: {e}")

    def is_rtp_packet(self, data):
        if len(data) < 90: # HEADER_SIZE IS CURRENTLY 26
            #print(f"is_rtp_packet: false because len(data) < 90 -> len(data) = {len(data)}")
            return False

        version = (data[0] >> 6) & 0x03

        #print(f"is_rtp_packet: true because version == 2 -> version = {version == 2}")
        return version == 2

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

                if message_info[0] == "request": # request|{filename}|{client_ip} só recebe se for um AccPoint
                    stream_name = message_info[1]
                    client_ip = message_info[2]


                    if stream_name not in self.stream_requests:
                        self.stream_requests[stream_name] = [client_ip]
                        
                        message = f"start_stream|{stream_name}|{client_ip}"
                        print(f"Sending {message} to {(self.server_ip, 9090)}")
                        self.server_socket.sendto(message.encode(), (self.server_ip, 9090))

                    else:
                        self.stream_requests[stream_name].append(client_ip)

                        print(f"Adicionei o cliente à lista para enviar,{self.stream_requests} \n")
                        
                elif message_info[0] == "stream_request": # stream_request|{filename}|{client_ip} -> não faz nada apenas adiciona quem lhe mandou no self.stream_requests
                    print("ESTOUUUU AQUIIII\n")
                    
                    stream_name = message_info[1]
                    client_ip = message_info[2]

                    if stream_name not in self.stream_requests:
                        print(f"before self.stream_requests[stream_name] = {[sender_ip]}")
                        self.stream_requests[stream_name] = [sender_ip]

                        
                    else:
                        print(f"Appending {sender_ip} to {self.stream_requests[stream_name]}")
                        self.stream_requests[stream_name].append(sender_ip)

                elif message_info[0] == "teardown": # teardown|{filename}|{client_ip}
                    stream_name = message_info[1]
                    client_ip = message_info[2]

                    self.stream_requests[stream_name].remove(client_ip)

                    if len(self.stream_requests[stream_name]) == 0:
                        self.stream_requests.remove(stream_name)
                        print(self.stream_requests)

                    self.connection_socket.sendto(data, (self.server_ip, 9090))

                else: # {movie_name | predecessor_ip | ip_dest}
                    
                    print(f"[handle_server_client] entrei no else com: {message_info} de {sender_ip}")
                    stream_name = message_info[0]  # tens de pedir stream_name ao predecessor_ip
                    predecessor_ip = message_info[1]
                        
                    ip_dest = message_info[2]

                    print(f"Stream name: {stream_name}")

                    if stream_name not in self.connections_ip:

                        self.connections_ip[stream_name] = predecessor_ip
                        # ###print(f"Adicionada a nova conexão: {self.connections_ip}")

                        connection_thread = threading.Thread(target=self.request_streams(stream_name, ip_dest))
                        connection_thread.daemon = True
                        connection_thread.start()
                            
                    else:
                        self.connections_ip[stream_name].append(client_ip)
                        print("A adicionei o cliente à transmição da stream")
                        print(f"self.connections_ip[stream_name] -> {self.connections_ip[stream_name]}")

    def handle_rtt_measurements(self):
        """
        Handle RTT measurement requests on a separate socket
        This method runs in a dedicated thread and listens on port 9092
        """
        rtt_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rtt_socket.bind(('0.0.0.0', 9092))

        while True:
            try:
                # Receive incoming ping request
                data, sender_address = rtt_socket.recvfrom(1024)
                sender_ip, sender_port = sender_address

                try:
                    rtt_socket.sendto(data, sender_address)
                    print(f"Responded to RTT ping from {sender_ip}")
                except Exception as e:
                    print(f"Error responding to RTT ping: {e}")
            except Exception as e:
                print(f"Error in RTT measurement handler: {e}")
                time.sleep(1)  # Prevent tight error loop

    def handle_requests(self):
        self.connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_address = ('0.0.0.0', 9090)
        self.connection_socket.bind(local_address)

        while True:
            try:
                data, sender_address = self.connection_socket.recvfrom(20480)
                if data:
                    # o node deve receber aqui os pacotes RTP 
                    if self.is_rtp_packet(data): # se recebi o caralho dos pacotes RTP
                        #print(f"Received RTP packet from {sender_address}")
                        rtpPacket = RtpPacket()
                        rtpPacket.decode(data)
                        #print(f"{rtpPacket.printheader()}")
                        #print(f"Forwarding RTP packet with frame number: {rtpPacket.seqNum()} to {node_address}")
                        filename = rtpPacket.getFilename() # mudar para o nome do ficheiro estar no header do pacote RTP
                        #print(f"[handle_requests] self.stream_requests -> {self.stream_requests}")
                        if filename in self.stream_requests:
                           
                            for node_ip in self.stream_requests[filename]:
                                #print(f"[handle_requests] for node_ip in self.stream_requests[filename] -> {node_ip}")
                                node_address = (node_ip, 9090) # reencaminha o pacote RTP para quem lhe pediu o pacote
                                self.connection_socket.sendto(data, node_address)
                                
                                #print(f"Sent RTP packet to {node_address} with the frame number: {rtpPacket.seqNum()}")
                        else:
                            pass
                            #print(f"A stream {filename} não está presente")
                    else:
                        print(f"Recebi algo que não é um pacote RTP: '{data}' de ({sender_address})")
            except Exception as e:
                print(f"Error in connection handler: {e}")
                time.sleep(1)  # Wait before retrying if there's an error

    def start(self, server_ip: str):
        if not server_ip:
            print("Usage: python3 node.py <SERVER_IP>")
            return

        self.server_ip = server_ip

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # Start RTT measurement handler thread
            rtt_thread = threading.Thread(target=self.handle_rtt_measurements)
            rtt_thread.daemon = True
            rtt_thread.start()
            
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
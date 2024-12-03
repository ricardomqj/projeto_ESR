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

    def request_streams(self, stream_name, client_ip_dest_or_message, ip_dest, received_predecessor):
        """
        Faz um pedido de stream para um nó ou predecessor.
        """
        print(f"\n\n ----------- PEDIU -------------\n\n")
        print(f"[DEBUG] request_streams chamado para stream: {stream_name}, client_ip_dest_or_message: {client_ip_dest_or_message}, ip_dest: {ip_dest}, received_predecessor: {received_predecessor}")

        try:
            # Verificar se o stream_name existe em connections_ip
            if stream_name not in self.connections_ip:
                print(f"[ERROR] Stream {stream_name} não encontrado em connections_ip!")
                return

            # Obter conexão atual
            current_connection = self.connections_ip[stream_name]
            message = f"stream_request|{stream_name}|{client_ip_dest_or_message if not received_predecessor else ip_dest}"

            # Determinar a porta de destino
            if current_connection == "10.0.0.10":
                destination = (current_connection, 9090)
            else:
                destination = (current_connection, 9091)

            # Log de envio
            print(f"[INFO] Enviando stream_request para {destination} com mensagem: {message}")

            # Enviar a mensagem
            self.connection_socket.sendto(message.encode(), destination)

        except KeyError as e:
            print(f"[ERROR] KeyError em connections_ip: {e}")
        except Exception as e:
            print(f"[ERROR] Exceção em request_streams: {e}")
            time.sleep(1)  # Aguarde antes de tentar novamente, se necessário


    def is_rtp_packet(self, data):
        if len(data) < 26: # HEADER_SIZE IS CURRENTLY 26
            return False
        version = (data[0] >> 6) & 0x03
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
                        
                elif message_info[0] == "stream_request": # stream_request|{filename}|{client_ip}
                    stream_name = message_info[1]
                    client_ip = message_info[2]


                    if stream_name not in self.stream_requests:
                        connection_thread = threading.Thread(
                            target=self.request_streams,
                            args=(stream_name, client_ip, '', False) 
                        )
                        connection_thread.daemon = True
                        connection_thread.start()

                        self.stream_requests[stream_name] = [sender_ip]
                    
                    else:
                        
                        self.stream_requests[stream_name].append(sender_ip)

                elif message_info[0] == "teardown": # teardown|{filename}|{client_ip}
                    stream_name = message_info[1]
                    client_ip = message_info[2]

                    print(f"O stream_requests antes de remover {self.stream_requests}\n")

                    self.stream_requests[stream_name].remove(sender_ip)
                    
                    print(f"O stream_requests após de remover {self.stream_requests}\n")

                    if len(self.stream_requests[stream_name]) == 0:
                        del self.stream_requests[stream_name]

                    print(self.stream_requests)

                    print("-------------------\n")

                    print(f"O connections_ip antes de remover {self.connections_ip}\n")

                    node_stream_request_ip = self.connections_ip[stream_name]
                    
                    del self.connections_ip[stream_name]

                    print(f"O connections_ip após de remover {self.connections_ip}\n")
                    
                    if node_stream_request_ip != "10.0.0.10":
                        self.connection_socket.sendto(data, (node_stream_request_ip, 9091))
                    else:
                        self.connection_socket.sendto(data, (self.server_ip, 9090))
                    
                    print(f"Dei delete e mandei pacote para apagar para trás {self.connections_ip}\n")

                else: # list [movie_name, predecessor_ip]

                    print(f"[handle_server_client] entrei no else com: {message_info} de {sender_ip}")
                    stream_name = message_info[0]  # tens de pedir stream_name ao predecessor_ip
                    self.predecessor_ip = message_info[1]
                        
                    ip_dest = message_info[2]

                    print(f"Stream name: {stream_name}")

                    if stream_name not in self.connections_ip:
                        
                        
                        self.connections_ip[stream_name] = message_info[1]
                        print(f"Adicionada a nova conexão: {self.connections_ip}\n -------- VOU ENTRAR NA THREAD PARA PEDIR ")

                        
                        connection_thread = threading.Thread(target=self.request_streams(stream_name, self.predecessor_ip, ip_dest, True))
                        connection_thread.daemon = True
                        connection_thread.start()
                            
                    else:
                        if client_ip not in self.stream_requests[stream_name]:
                            self.stream_requests[stream_name].append(client_ip)
                            print("A adicionei o cliente à transmição da stream")

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
                data, sender_address = self.connection_socket.recvfrom(20048)
                if data:
                    # o node deve receber aqui os pacotes RTP 
                    if self.is_rtp_packet(data): # se recebi o caralho dos pacotes RTP
                        #print(f"Received RTP packet from {sender_address}")
                        rtpPacket = RtpPacket()
                        rtpPacket.decode(data)
                        #print(f"Forwarding RTP packet with frame number: {rtpPacket.seqNum()}")
                        filename = rtpPacket.getFilename() # mudar para o nome do ficheiro estar no header do pacote RTP
                        if filename in self.stream_requests:
                           
                            for node_ip in self.stream_requests[filename]:
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

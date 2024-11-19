from tkinter import *
from PIL import Image, ImageTk
import tkinter.messagebox
import socket, threading
import time, os
from RtpPacket import RtpPacket
import queue

fronteira = ['10.0.10.2', '10.0.9.2']

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class ClientRunner:
    INIT = 0
    READY = 1
    PLAYING = 2
    BUFFERING = 3

    BUFFER_TIME = 2.0
    FRAME_RATE = 30 
    MAX_BUFFER_SIZE = BUFFER_TIME * FRAME_RATE # Maximum frames to buffer
    
    def __init__(self, master, server_addr, filename):
        self.master = master
        self.createWidgets()
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.server_addr = server_addr
        self.filename = filename
        self.frameNbr = 0
        self.sessionId = 0
        self.state = self.INIT
        self.local_ip = self.get_local_ip()
        print(f"Local IP -> {self.local_ip}")
        
        # Frame buffer to store the received frames
        self.frame_buffer = queue.PriorityQueue()
        self.buffer_lock = threading.Lock()
        self.playback_ready = threading.Event()
        self.is_receiving = True
        
        #self.last_received_time = 0
        #self.TIMEOUT_THRESHOLD = 1.5 # seconds to wait before assuming transmission is complete

        # Setup RTP socket
        self.setup_rtp_socket()
        
        # Start playback
        self.state = self.READY
        self.start_playback()
        #threading.Thread(target=self.run).start()

    def setup_rtp_socket(self):
        """Setup the RTP socket with proper timeout"""
        print("Setting up RTP socket")
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        connection_socket.settimeout(0.5)
        try:
            connection_socket.bind((self.local_ip, 9090))
            self.connection_socket = connection_socket
            print(f"RTP socket binded to -> ({(self.local_ip, 9090)})")
        except Exception as e:
            print(f"Failed to bind socket: {e}")
            raise 

    def start_playback(self):
        """Start video playback"""
        print("Starting playback")
        if self.state == self.READY:
            # Start frame receiving thread
            self.receiver_thread = threading.Thread(target=self.receive_frames)
            self.receiver_thread.daemon = True
            self.receiver_thread.start()

            # Start playback thread
            self.playback_thread = threading.Thread(target=self.play_frames)
            self.playback_thread.daemon = True
            self.playback_thread.start()

            # Send initial request
            for border_node in fronteira:
                try:
                    self.connection_socket.sendto(
                        f"connecting|{self.server_addr}|{self.filename}|{self.local_ip}".encode(),
                        (border_node, 9090)
                    )
                except socket.error:
                    continue

    def receive_frames(self):
        """Continuously receive and buffer frames"""
        initial_buffer_time = time.time()
        frames_received = 0

        while self.is_receiving:
            try:
                data, addr = self.connection_socket.recvfrom(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    if rtpPacket.getClientDestIP() == self.local_ip:
                        currFrameNbr = rtpPacket.seqNum()

                        # Write frame to file and add to buffer
                        frame_file = self.writeFrame(rtpPacket.getPayload(), currFrameNbr)
                        self.frame_buffer.put((currFrameNbr, frame_file))
                        frames_received += 1

                        # Start playback after initial buffering period
                        if not self.playback_ready.is_set():
                            current_time = time.time()
                            if (current_time - initial_buffer_time >= self.BUFFER_TIME or frames_received >= self.MAX_BUFFER_SIZE):
                                print(f"Buffer ready with {frames_received} frames")
                                self.playback_ready.set()
                                self.state = self.PLAYING
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error receiving frame: {e}")
                continue

    def play_frames(self):
        """Play frames from buffer while maintaining proper timing"""
        frame_interval = 1.0 / self.FRAME_RATE

        # Wait for initial buffer to fill
        self.playback_ready.wait()

        last_frame_time = time.time()

        while self.state == self.PLAYING:
            try:
                # Get next frame from buffer
                frameNbr, frame_file = self.frame_buffer.get(timeout=1.0)

                # Calculate time to next frame
                current_time = time.time()
                time_diff = current_time - last_frame_time

                # If we're ahead of schedule, wait
                if time_diff < frame_interval:
                    time.sleep(frame_interval - time_diff)

                # Display frame
                self.updateMovie(frame_file)
                last_frame_time = time.time()

                # Remove played from file
                try:
                    os.remove(frame_file)
                except:
                    pass

            except queue.Empty:
                # Buffer underrun - wait for more frames
                print("Buffer underrun - waiting for frames")
                continue
            except Exception as e:
                print(f"Error playing frame: {e}")
                continue
                

    def handler(self):
        """Clean up on window close"""
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.is_receiving = False
            self.state = self.INIT
            self.connection_socket.close()
            self.master.destroy()

    def createWidgets(self):
        # Create Play button
        #self.start = Button(self.master, width=0, padx=3)
        #self.start["text"] = "Play"
        #self.start["command"] = self.playMovie
        #self.start.grid(row=1, column=1, padx=2, pady=2)

        # Label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

    def playMovie(self):
        """Play button handler"""
        if not self.local_ip:
            tkinter.messagebox.showerror("Error", "Not connected to server yet")
            return
        
        self.playEvent = threading.Event()
        self.playEvent.clear()
        print("Play button clicked")
        self.sendMovieRequest()

    def get_local_ip(self):
        """Get the local IP address of the client"""
        try:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.connect(("8.8.8.8", 80))
            local_ip = temp_socket.getsockname()[0]
            temp_socket.close()
            print(f"[get_local_ip] Returning local ip -> {local_ip}")
            return local_ip
        except Exception as e:
            print(f"Error getting local IP: {e}")
            return None

    def makeRtp(self, payload, frameNbr, ip_source, ip_dest, is_movie_request):
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26 # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()
        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload, ip_dest, self.local_ip, is_movie_request, False)

        return rtpPacket.getPacket()

    def writeFrame(self, data, frameNbr):
        """Write frame data to file with frame number in filename"""
        cachename = f"{CACHE_FILE_NAME}{self.sessionId}-{frameNbr}{CACHE_FILE_EXT}"
        with open(cachename, "wb") as file:
            file.write(data)
        return cachename

    def updateMovie(self, imageFile):
        """Update the imagge field as video frame in the GUI"""
        try:
            photo = ImageTk.PhotoImage(Image.open(imageFile))
            self.label.configure(image = photo, height = 288)
            self.label.image = photo
            self.master.update()
        except Exception as e:
            print(f"Error updating frame: {e}")


    def handle_server_response(self):
        print("inside handle_server_response")
        while self.state in [self.BUFFERING, self.PLAYING]:
            print("inside while loop in handle_server_response")
            try:
                data, addr = self.connection_socket.recvfrom(20480)
                print(f"Received data from addr -> {addr}")
                if data:
                    self.last_received_time = time.time()
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    dest_ip = rtpPacket.getClientDestIP()
                    session = rtpPacket.getSessionNumber()
                    #print(f"Session Number received -> {session}")
                    print(f"Frame Number received -> {rtpPacket.seqNum()}")
                    if self.sessionId == 0:
                        self.sessionId = session
                        print(f"Session ID -> {self.sessionId}")
                    if self.sessionId == session:
                        file_founded = rtpPacket.isFileFound()
                        if file_founded and self.local_ip == dest_ip: # freceber os frames do vídeo
                            currFrameNbr = rtpPacket.seqNum()

                            if currFrameNbr > self.frameNbr:
                                self.frameNbr = currFrameNbr
                                frame_file = self.writeFrame(rtpPacket.getPayload(), currFrameNbr)
                                self.frame_buffer[currFrameNbr] = frame_file
                                print(f"Buffered frame {currFrameNbr}")
                                #self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
                        elif file_founded and not self.local_ip == dest_ip:
                            print("Ficheiro foi encontrado mas não é para mim")
                        else:
                            print("Ficheiro não encontrado")
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error receiving packet: {e}")
                continue

    def monitor_and_play(self):
        """Monitor frame reception and trigger playback when complete"""
        while self.state in [self.BUFFERING, self.PLAYING]:
            current_time = time.time()
            print(f"{current_time - self.last_received_time} > {self.TIMEOUT_THRESHOLD} and {self.last_received_time} > 0 and {len(self.frame_buffer)} > 0 and {self.state} == {self.BUFFERING}")
            # If we haven't received any frames for TIMEOUT_THRESHOLD seconds and we have frames buffered
            if (current_time - self.last_received_time > self.TIMEOUT_THRESHOLD and 
                self.last_received_time > 0 and 
                len(self.frame_buffer) > 0 and 
                self.state == self.BUFFERING):
                
                print(f"Starting playback with {len(self.frame_buffer)} frames")
                self.state = self.PLAYING
                print(f"self.state changed to PLAYING")
                self.play_buffered_frames()
                break

            time.sleep(0.1)

    def play_buffered_frames(self):
        """Play all buffered frames in sequence"""
        frame_delay = 1/30 # Assume 30 fps playback

        sorted_frames = sorted(self.frame_buffer.items())

        for frameNbr, frame_file in sorted_frames:
            if self.state != self.PLAYING:
                break
            self.updateMovie(frame_file)
            time.sleep(frame_delay)

        print("Playback complete")

    def run(self):
        local_client_ip = self.get_local_ip()
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        connection_socket.bind((local_client_ip, 9090))
        print(f"connection socket binded to -> ({(local_client_ip, 9090)})")

        for border_node in fronteira:
            try:
                connection_socket.sendto(f"connecting|{self.server_addr}|{self.filename}|{self.local_ip}".encode(), (border_node, 9090))
                print(f"Sent request to addr -> {(border_node, 9090)}")
                threading.Thread(target=self.handle_server_response, args=(connection_socket,)).start()
                #while True:
                #    data, addr = connection_socket.recvfrom(20480)
                #    if data:
                #        print(f"[run] received data")
                #        thread = threading.Thread(target=self.handle_server_response, args=(connection_socket, data))
                #        thread.start()
            except socket.error:
                continue


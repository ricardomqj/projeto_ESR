from tkinter import *
from PIL import Image, ImageTk
import tkinter.messagebox
import socket, threading
import time, os
from RtpPacket import RtpPacket
import queue
import time
import io
from time import sleep
import numpy as np
import cv2

fronteira = ['10.0.6.2', '10.0.4.2']

CACHE_FILE_NAME = "cache/cache-"
CACHE_FILE_EXT = ".jpg"

class ClientRunner:
    INIT = 0
    READY = 1
    PLAYING = 2
    BUFFERING = 3

    BUFFER_TIME = 1
    FRAME_RATE = 60 
    MAX_BUFFER_SIZE = 200 # Maximum frames to buffer
    
    def __init__(self, master, filename):
        self.master = master
        self.createWidgets()
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
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

        # Setup RTP socket
        self.setup_rtp_socket()
        
        # Start playback
        self.state = self.READY
        self.start_playback()


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


    def select_best_access_point(self):
        """
        Select the best access point by measuring average response times 
        over 5 ping attempts
        Returns IP of the best access point
        """
        ping_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ping_socket.settimeout(1.0)  # 1 second timeout for each ping

        access_point_times = {}

        for access_point in fronteira:
            try:
                # Reset times for this access point
                access_point_times[access_point] = []

                # Send 5 ping attempts
                for _ in range(5):
                    try:
                        # Send simple ping with current timestamp
                        ping_data = str(time.time()).encode()

                        start_time = time.time()
                        ping_socket.sendto(ping_data, (access_point, 9092))

                        try:
                            # Wait for response 
                            response, _ = ping_socket.recvfrom(1024)
                            end_time = time.time()

                            # Calculate round trip time
                            rtt = end_time - start_time
                            access_point_times[access_point].append(rtt)
                            print(f"Ping to Access Point {access_point} RTT: {rtt:.4f} seconds") 

                        except socket.timeout:
                            print(f"No response from access point {access_point} for this attempt")
                            access_point_times[access_point].append(float('inf'))

                    except Exception as e:
                        print(f"Error pinging access point {access_point}: {e}")
                        access_point_times[access_point].append(float('inf'))

            except Exception as e:
                print(f"Error setting up ping for access point {access_point}: {e}")
                access_point_times[access_point] = [float('inf')] * 5

        # Close the temporary ping socket
        ping_socket.close()

        # Calculate average RTT for each access point
        access_point_avg_times = {}
        for access_point, times in access_point_times.items():
            # Filter out infinite values and calculate average
            valid_times = [t for t in times if t != float('inf')]
            if valid_times:
                avg_rtt = sum(valid_times) / len(valid_times)
                access_point_avg_times[access_point] = avg_rtt
                print(f"Access Point {access_point} Average RTT: {avg_rtt:.4f} seconds")

        # Select the access point with the lowest average response time
        if access_point_avg_times:
            best_access_point = min(access_point_avg_times, key=access_point_avg_times.get)
            print(f"Selected best access point: {best_access_point}")
            return best_access_point
        
        # Fallback to first access point if no responses
        return fronteira[0] if fronteira else None          

    def start_playback(self):
        """Start video playback"""
        print("Starting playback")
        if self.state == self.READY:
            # Select best access point 
            best_access_point = self.select_best_access_point()

            # Start frame receiving thread
            self.receiver_thread = threading.Thread(target=self.receive_frames)
            self.receiver_thread.daemon = True
            self.receiver_thread.start()

            # Start playback thread
            self.playback_thread = threading.Thread(target=self.play_frames)
            self.playback_thread.daemon = True
            self.playback_thread.start()


            if best_access_point:
                # Send initial request to best access point 
                try:
                    self.connection_socket.sendto(
                        f"request|{self.filename}|{self.local_ip}".encode(),
                        (best_access_point, 9091)
                    )
                except socket.error as e:
                    print(f"Error sending request: {e}")
            else:
                print("No access points available")

    def receive_frames(self):
        """Continuously receive and buffer frames"""
        initial_buffer_time = time.time()
        frames_received = 0
        session_number = None

        self.frame_buffer = []

        while self.is_receiving:
            try:
                data, addr = self.connection_socket.recvfrom(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    print("Information of the packet received:")
                    print(f"{rtpPacket.printheader()}")
                    print(f"Frame recebido, tamanho: {len(rtpPacket.getPayload())} bytes")

                    if session_number is None:
                        session_number = rtpPacket.getSessionNumber()
                        print(f"Initialized session number: {session_number}")

                    if rtpPacket.getSessionNumber() == session_number:
                        currFrameNbr = rtpPacket.seqNum()
                        
                        # Create in-memory buffer instead of writing to file
                        frame_buffer = io.BytesIO(rtpPacket.getPayload())
                        self.frame_buffer.append((currFrameNbr, frame_buffer))
                        frames_received += 1

                        # Write frame to file and add to buffer
                        #frame_file = self.writeFrame(rtpPacket.getPayload(), currFrameNbr)
                        #self.frame_buffer.put((currFrameNbr, frame_file))
                        #frames_received += 1

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
        last_frame_number = -1

        while self.state == self.PLAYING:
            try:
                # Get next frame from buffer
                frameNbr, frame_buffer = self.frame_buffer.pop(0)

                # Ensure frame are played in order
                if frameNbr <= last_frame_number:
                    #print(f"Skipping out-of-order frame {frameNbr}")
                    continue

                # Calculate time to next frame
                current_time = time.time()
                time_diff = current_time - last_frame_time

                # If we're ahead of schedule, wait
                if time_diff < frame_interval:
                    time.sleep(frame_interval - time_diff)

                # Display frame
                self.updateMovie(frame_buffer)
                sleep(1/60)
                last_frame_time = time.time()
                last_frame_number = frameNbr

                # Remove played from file
                #try:
                #    os.remove(frame_buffer)
                #except:
                #    pass
            except Exception as e:
                #print(f"Error playing frame: {e}")
                continue
                

    def handler(self):
        """Clean up on window close"""
        ## enviar um request para o servidor para parar de enviar frames enviar pela porta 9091
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            cancel_transm_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            best_access_point = self.select_best_access_point()
            request = f"teardown|{self.filename}|{self.local_ip}"
            print(f"Sending '{request}' request to {(best_access_point, 9091)}")
            cancel_transm_socket.sendto(request.encode(), (best_access_point, 9091))
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

    def makeRtp(self, payload, frameNbr, ip_source, ip_dest, is_movie_request, file_found, sessionNumber, filename):
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26 # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()
        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload, ip_dest, ip_source, is_movie_request, file_found, sessionNumber, filename)

        return rtpPacket.getPacket()

    def writeFrame(self, data, frameNbr):
        """Write frame data to file with frame number in filename"""
        cachename = f"{CACHE_FILE_NAME}{self.sessionId}-{frameNbr}{CACHE_FILE_EXT}"
        with open(cachename, "wb") as file:
            file.write(data)
        return cachename

    def updateMovie(self, frame_buffer):
        """Update the imagge field as video frame in the GUI"""
        try:
            print(f"Inside updateMovie function")
            # Reset buffer position to the start
            """

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            photo = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
            """
            frame_buffer.seek(0)
            
            frame_data = frame_buffer.read()

            nparr = np.frombuffer(frame_data, np.uint8)

            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(image)
                self.label.configure(image=photo, height=480, width= 854)
                self.label.image = photo
                self.master.update()

            #photo = ImageTk.PhotoImage(Image.open())
            #self.label.configure(image = photo, height = 1080, width = 1920)
            #self.label.image = photo
            #self.master.update()
        except Exception as e:
            #print(f"Error updating frame: {e}")
            pass

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
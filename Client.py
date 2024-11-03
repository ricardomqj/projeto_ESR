from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.frameNbr = 0
		self.connectToServer()
		
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		"""
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		"""
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
	
	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
	
	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)		
		self.master.destroy() # Close the gui window
		os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video


	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			print("[playMovie] sending Rtsp request...")
			self.sendRtspRequest(self.PLAY)
			print("[playMovie] Sended Rtsp request.")


	def listenRtp(self):		
		"""Listen for RTP packets."""
		print("[listenRTP] listening for RTP packets")
		# self.openRtpPort() tentei meter a abrir a porta apenas uma vez
		#print("[listenRtp] opened Rtp socket to receive the data.")
		while True:
			try:
				print("before getting the sockname from the RTP socket")
				local_ip, local_port = self.rtpSocket.getsockname()
				print(f"[listenRtp] ({local_ip, local_port}) i will try to receive the data from the rtp socket")
				data = self.rtpSocket.recv(20480)
				if data:
					print("[listenRTP] received the data: ")
					print(data)
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					print("[listenRtp] decoded the data from the Rtp packet")
					
					currFrameNbr = rtpPacket.seqNum()
					print("Current Seq Num: " + str(currFrameNbr))
										
					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
			except:
				continue
				#print("[listenRtp] exception")
				#break
				"""
				# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet(): 
					break
				
				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
				"""
			
		print("stopped listening for RTP packet's")
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		print("[connectToServer] starting a new RTSP/TCP session and connecting to the server")
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkMessageBox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		self.rtspSeq += 1
		request = ""
		
		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			request = f"SETUP {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nTransport: RTP/UDP; client_port= {self.rtpPort}"
			self.state = self.READY
			threading.Thread(target=self.recvRtspReply).start()
		
		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			request = f"PLAY {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nSession: {self.sessionId}"
			self.state = self.PLAYING
			self.requestSent = self.PLAY
		
		"""
		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			# ...
		    print('\nPAUSE event\n')
			
			# Write the RTSP request to be sent.
			# request = ...
			
			# Keep track of the sent request.
			# self.requestSent = ...
			
		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			# ...
		    print('\nTEARDOWN event\n')
			
			# Write the RTSP request to be sent.
			# request = ...
			
			# Keep track of the sent request.
			# self.requestSent = ...
		"""
		self.rtspSocket.send(request.encode())
		print('\n[sendRtspRequest] Data sent:\n' + request)
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		print(f"[recvRtspReply] waiting to receive Rtsp reply from the server")
		while True:
			reply = self.rtspSocket.recv(1024)
			
			if reply: 
				print("[recvRtspReply] received the RtspReply from the server")
				self.parseRtspReply(reply.decode("utf-8"))
			
			# Close the RTSP socket upon requesting Teardown
			"""
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break"""
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		lines = data.split('\n')
		seqNum = int(lines[1].split(' ')[1])
		
		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session
			if self.sessionId == session and int(lines[0].split(' ')[1]) == 200:
				if self.requestSent == self.PLAY:
					print('\nPLAY event confirmed\n')
					# Abre o socket RTP para permitir receber os pactes RTP
					# self.openRtpPort()
					self.rtspSocket.close()
					self.openRtpPort()
					self.listenRtp()
					self.state = self.PLAYING
					
			
			# Process only if the session ID is the same
			"""
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200: 
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
						# self.state = ...
						
						# Open RTP port.
						self.openRtpPort() 
					elif self.requestSent == self.PLAY:
						# self.state = ...
						print('\nPLAY sent\n')
					elif self.requestSent == self.PAUSE:
						# self.state = ...
						
						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()
					elif self.requestSent == self.TEARDOWN:
						# self.state = ...
						
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1 """
	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		print(f"[openRtpPort] inside openRtpPort function")
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.rtpSocket.settimeout(0.5)

		try:
			# Bind the socket to the address using the RTP port given by the client user
			print(f"[openRtpPort] trying to bind the socket to the address -> {('', self.rtpPort)}")
			self.rtpSocket.bind(('', self.rtpPort))
			print(f"[openRtpPort] binded the socket to the address -> {('', self.rtpPort)}")
		except Exception as e:
			#tkMessageBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)
			print(f"[openRtpPort] exception: {e}")
			#tkinter.messagebox.showwarning("Unable to Bind", f"Unbale to bind PORT={self.rtpPort}")


	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		"""
		self.pauseMovie()
		if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playMovie()
				"""
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.master.destroy()


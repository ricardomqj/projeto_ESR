import sys
from time import time
import socket
HEADER_SIZE = 90 # 26 (original) + 64 filename

class RtpPacket:	
	header = bytearray(HEADER_SIZE)
	
	def __init__(self):
		pass
		
	def encode(self, version, padding, extension, cc, seqnum, marker, pt, ssrc, payload, client_ip, source_ip, is_movie_request, file_found, session_number, filename):
		"""Encode the RTP packet with header fields and payload."""
		timestamp = int(time())
		header = bytearray(HEADER_SIZE) 
		header[0] = (header[0] | version << 6) & 0xC0; # 2 bits
		header[0] = (header[0] | padding << 5); # 1 bit
		header[0] = (header[0] | extension << 4); # 1 bit
		header[0] = (header[0] | (cc & 0x0F)); # 4 bits
		header[1] = (header[1] | marker << 7); # 1 bit
		header[1] = (header[1] | (pt & 0x7f)); # 7 bits
		header[2] = (seqnum >> 8); 
		header[3] = (seqnum & 0xFF);
		header[4] = (timestamp >> 24);
		header[5] = (timestamp >> 16) & 0xFF;
		header[6] = (timestamp >> 8) & 0xFF;
		header[7] = (timestamp & 0xFF);
		header[8] = (ssrc >> 24);
		header[9] = (ssrc >> 16) & 0xFF;
		header[10] = (ssrc >> 8) & 0xFF;
		header[11] = ssrc & 0xFF
		
		try:
			# Convert IP address to 4-byte representation and add to header
			ip_dest_bytes = socket.inet_aton(client_ip)
			header[12:16] = ip_dest_bytes

			# Convert source IP address to 4-byte representation
			ip_source_bytes = socket.inet_aton(source_ip)
			header[16:20] = ip_source_bytes
		except socket.error as e:
			print(f"Error converting IP address: {e}")
			raise

		header[20] = 1 if is_movie_request else 0
		header[21] = 1 if file_found else 0

		# Add session number (4 bytes)
		header[22] = (session_number >> 24) & 0xFF
		header[23] = (session_number >> 16) & 0xFF
		header[24] = (session_number >> 8) & 0xFF
		header[25] = session_number & 0xFF

		# Add filename (64 bytes)
		filename_bytes = filename.encode('utf-8')[:64]
		filename_padded = filename_bytes.ljust(64, b'\0')
		header[26:90] = filename_padded

		# set header and  payload
		self.header = header
		self.payload = payload
		
	def decode(self, byteStream):
		"""Decode the RTP packet."""
		self.header = bytearray(byteStream[:HEADER_SIZE])
		self.payload = byteStream[HEADER_SIZE:]
	
	def version(self):
		"""Return RTP version."""
		return int(self.header[0] >> 6)
	
	def seqNum(self):
		"""Return sequence (frame) number."""
		seqNum = self.header[2] << 8 | self.header[3]
		return int(seqNum)
	
	def timestamp(self):
		"""Return timestamp."""
		timestamp = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
		return int(timestamp)
	
	def payloadType(self):
		"""Return payload type."""
		pt = self.header[1] & 127
		return int(pt)
	
	def getPayload(self):
		"""Return payload."""
		return self.payload
		
	def getPacket(self):
		"""Return RTP packet."""
		return self.header + self.payload

	def getClientDestIP(self):
		"""Return the client IP address from the header."""
		return '.'.join(str(b) for b in self.header[12:16])

	def getSourceIP(self):
		"""Return the source IP address from the header."""
		source_ip_bytes = bytearray(4)
		source_ip_bytes[0] = self.header[16] & 0x3F 
		source_ip_bytes[1:4] = self.header[17:20]
		return '.'.join(str(b) for b in source_ip_bytes)

	def isMovieRequest(self):
		"""Return whether the packet is a movie request."""
		return bool(self.header[20])
	
	def isFileFound(self):
		"""Return whether the movie file was found"""
		return bool(self.header[21])

	def getSessionNumber(self):
		"""Return the session number."""
		session_number = (self.header[22] << 24) | (self.header[23] << 16) | (self.header[24] << 8) | self.header[25]
		return int(session_number)

	def getFilename(self):
		"""Return the filename from the header"""
		filename_bytes = self.header[26:90]
		return filename_bytes.rstrip(b'\0').decode('utf-8')

	def printheader(self):
		"""Imprime o cabeçalho do pacote RTP de forma legível para debug."""
		# Exibe versão, padding, extensão e número de CSRCs
		version = self.version()
		padding = (self.header[0] >> 5) & 0x01
		extension = (self.header[0] >> 4) & 0x01
		cc = self.header[0] & 0x0F

		# Exibe marcador e tipo de payload
		marker = (self.header[1] >> 7) & 0x01
		payload_type = self.payloadType()

		# Exibe o número de sequência e timestamp
		seq_num = self.seqNum()
		timestamp = self.timestamp()

		# Exibe o SSRC
		ssrc = (self.header[8] << 24) | (self.header[9] << 16) | (self.header[10] << 8) | self.header[11]

		# Exibe o IP de destino, assumindo que foi adicionado após o SSRC
		dest_ip = '.'.join(str(b) for b in self.header[12:16])
		source_ip = self.getSourceIP()

		# Impressão formatada do cabeçalho
		print("[RTP Packet] Header Information:")
		print(f"  Version: {version}")
		print(f"  Padding: {padding}")
		print(f"  Extension: {extension}")
		print(f"  CSRC Count: {cc}")
		print(f"  Marker: {marker}")
		print(f"  Payload Type: {payload_type}")
		print(f"  Sequence Number: {seq_num}")
		print(f"  Timestamp: {timestamp}")
		print(f"  SSRC: {ssrc}")
		print(f"  Destination IP: {dest_ip}")
		print(f"  Source IP: {source_ip}")
		print(f"  Is Movie Request: {self.isMovieRequest()}")
		print(f"  File Found: {self.isFileFound()}")
		print(f"  Session number: {self.getSessionNumber()}")
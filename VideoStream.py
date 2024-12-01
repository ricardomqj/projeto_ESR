import math

class VideoStream:
    def __init__(self, filename, max_packet_size=60000):
        """
        Initialize VideoStream with optional max packet size.
        
        :param filename: Path to the video file
        :param max_packet_size: Maximum size of each UDP packet (default 60000 bytes)
        """
        self.filename = filename
        self.max_packet_size = max_packet_size
        
        try:
            self.file = open(filename, 'rb')
        except IOError:
            raise IOError(f"Could not open file {filename}")
        
        self.frameNum = 0
        self.end_of_file = False
        self.current_frame = None
        self.current_frame_fragments = []
        self.current_fragment_index = 0

    def _read_next_frame(self):
        """
        Read the next complete frame from the file.
        
        :return: Bytes representing the complete frame or b'' if no frame
        """
        if self.end_of_file:
            return b''
        
        # Read the first 5 bytes as potential frame length
        length_data = self.file.read(5)
        
        if not length_data:
            self.end_of_file = True
            return b''
        
        try:
            # Try to convert first 5 bytes to integer frame length
            framelength = int(length_data)
            
            # Read the frame data
            data = self.file.read(framelength)
            
            if data:
                self.frameNum += 1
                return data
            else:
                self.end_of_file = True
                return b''
        
        except ValueError:
            # Fallback to JPEG marker method
            self.file.seek(-len(length_data), 1)
            
            # Look for JPEG start of image marker
            while True:
                start_marker = self.file.read(1)
                if not start_marker:
                    self.end_of_file = True
                    return b''
                
                if start_marker == b'\xff':
                    next_byte = self.file.read(1)
                    if next_byte == b'\xd8':
                        break
            
            # Now collect the entire frame
            frame_data = bytearray(start_marker + next_byte)
            
            # Continue reading until we find the end of image marker (0xFFD9)
            while True:
                chunk = self.file.read(1024)
                if not chunk:
                    self.end_of_file = True
                    break
                
                frame_data.extend(chunk)
                
                # Check if we've found the end of the image
                if b'\xff\xd9' in chunk:
                    # Trim to the exact end of the image
                    end_index = frame_data.rfind(b'\xff\xd9') + 2
                    frame_data = frame_data[:end_index]
                    break
            
            if len(frame_data) > 0:
                self.frameNum += 1
                return bytes(frame_data)
            else:
                self.end_of_file = True
                return b''

    def nextFrame(self):
        """
        Get next frame, potentially fragmented.
        
        :return: A fragment of the frame or b'' if no more data
        """
        # If we don't have a current frame or have exhausted its fragments, read a new frame
        if not self.current_frame or self.current_fragment_index >= len(self.current_frame_fragments):
            # Read next frame
            self.current_frame = self._read_next_frame()
            
            # If no frame, return empty bytes
            if not self.current_frame:
                return b''
            
            # Fragment the frame
            self.current_frame_fragments = self._fragment_frame(self.current_frame)
            self.current_fragment_index = 0
        
        # Return the next fragment
        fragment = self.current_frame_fragments[self.current_fragment_index]
        self.current_fragment_index += 1
        
        return fragment

    def _fragment_frame(self, frame_data):
        """
        Fragment a frame into smaller packets.
        
        :param frame_data: Complete frame data
        :return: List of frame fragments
        """
        total_fragments = math.ceil(len(frame_data) / self.max_packet_size)
        fragments = []
        
        for i in range(total_fragments):
            start = i * self.max_packet_size
            end = min((i + 1) * self.max_packet_size, len(frame_data))
            
            # Create fragment with consistent metadata
            fragment = (
                f"{total_fragments}|{i}|{len(frame_data)}|".encode('utf-8') + 
                frame_data[start:end]
            )
            
            fragments.append(fragment)
        
        return fragments

    def frameNbr(self):
        """Get current frame number."""
        return self.frameNum

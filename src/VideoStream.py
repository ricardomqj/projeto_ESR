class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        try:
            self.file = open(filename, 'rb')
        except:
            raise IOError
        self.frameNum = 0
        self.end_of_file = False
        
    def nextFrame(self):
        """Get next frame."""
        if self.end_of_file:
            return b''
        
        data = self.file.read(5) # Get the framelength from the first 5 bits
        if data: 
            print(f"[VideoStream:nextFrame] antes de framelength = int(data)")
            framelength = int(data)
            print(f"[VideoStream:nextFrame] framelength -> {framelength}")
            # Read the current frame
            data = self.file.read(framelength)
            
            if data:
                self.frameNum += 1
                return data
            else:
                self.end_of_file = True
                return b''
            
        self.end_of_file = True
        return b''
        
    def frameNbr(self):
        """Get frame number."""
        return self.frameNum
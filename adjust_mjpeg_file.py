import os
import sys

def add_length_markers_to_mjpeg(input_file):
    """
    Add 5-byte length markers to an existing MJPEG file, overwriting the original file.
    
    :param input_file: Path to the input MJPEG file (will be overwritten)
    """
    temp_file = input_file + '.tmp'

    def find_next_start_marker(infile):
        """Find the next JPEG start marker in the input file."""
        while True:
            byte = infile.read(1)
            if not byte:
                return None  # End of file
            if byte == b'\xff':
                next_byte = infile.read(1)
                if next_byte == b'\xd8':  # Start of JPEG marker
                    return b'\xff\xd8'

    with open(input_file, 'rb') as infile, open(temp_file, 'wb') as outfile:
        while True:
            # Locate the next JPEG start marker
            start_marker = find_next_start_marker(infile)
            if not start_marker:
                break
            
            # Collect the entire frame
            frame_data = bytearray(start_marker)
            while True:
                chunk = infile.read(1024)
                if not chunk:
                    break
                frame_data.extend(chunk)
                if b'\xff\xd9' in chunk:  # End of JPEG marker
                    end_index = frame_data.rfind(b'\xff\xd9') + 2
                    frame_data = frame_data[:end_index]
                    break
            
            # Calculate frame length and write marker + frame
            frame_length = len(frame_data)
            length_marker = f"{frame_length:05d}".encode('utf-8')
            outfile.write(length_marker)
            outfile.write(frame_data)
    
    os.replace(temp_file, input_file)
    print(f"File processed and updated: {input_file}")

# Exemplo de uso
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]  # Caminho do ficheiro de entrada
    add_length_markers_to_mjpeg(input_file)

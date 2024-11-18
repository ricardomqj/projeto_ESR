import sys, socket, threading
from tkinter import Tk
from ClientAux import ClientRunner

fronteira = ['10.0.9.2', '10.0.10.2']

def main():
    try:
        server_addr = sys.argv[1]
        filename = sys.argv[2]
    except:
        print(f"Usage: python Client.py <Server_address> <filename>")

    root = Tk()

    app = ClientRunner(root, server_addr, filename)
    app.master.title("RTPClient")
    root.mainloop()

if __name__ == "__main__":
    main()


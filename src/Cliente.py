import sys, socket, threading
from tkinter import Tk
from ClientAux import ClientRunner

def main():
    try:
        filename = sys.argv[1]
    except:
        print(f"Usage: python Cliente.py <filename>")

    root = Tk()

    app = ClientRunner(root, filename)
    app.master.title("RTPClient")
    root.mainloop()

if __name__ == "__main__":
    main()

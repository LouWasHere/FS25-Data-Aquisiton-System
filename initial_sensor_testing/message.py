import tkinter as tk
import os

def main():
        # Debugging output
        print(f"DISPLAY={os.environ.get('DISPLAY')}")

        # Create the main application window
        root = tk.Tk()
                        
        # Set the window title
        root.title("Basic App Window")

        # Set the size of the window (480x320) and position it at the center of the screen
        root.geometry("480x320")

        # Create a label with some text
        text_label = tk.Label(root, text="Hello, LGR!", font=("Arial", 16), fg="blue")
        text_label.pack(expand=True)

        # Run the application
        root.mainloop()

if __name__ == "__main__":
    main()

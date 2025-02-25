import sys
import requests
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from PyQt5.QtCore import Qt

def get_ngrok_address():
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        data = response.json()

        for tunnel in data["tunnels"]:
            if tunnel["proto"] == "tcp":
                return tunnel["public_url"]

        return "No active ngrok tunnel found"

    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

def main():
    # Create the main application
    app = QApplication(sys.argv)

    # Create the main window
    window = QMainWindow()
    window.setWindowTitle("Basic App Window")
    window.setGeometry(50, 50, 430, 270)

    # Set the window to stay on top and be frameless (optional)
    window.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

    ngrok_url = get_ngrok_address()

    if "tunnel" in ngrok_url:
        return 0

    # Create a label with some text
    text_label = QLabel(ngrok_url, window)
    text_label.setStyleSheet("font-size: 12pt; color: blue;")
    text_label.setAlignment(Qt.AlignCenter)
    window.setCentralWidget(text_label)

    # Show the window
    window.showFullScreen()  # Makes it fullscreen over the taskbar

    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QSlider, QHBoxLayout, QPushButton, QComboBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
import folium
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import Qt

class RaceDataAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Race Data Analyzer")
        self.setGeometry(100, 100, 800, 600)

        # Load data
        self.data = pd.read_csv("recorded_data.csv")

        # Create map
        self.map = self.create_map()

        # Set up UI
        self.init_ui()

    def create_map(self):
        # Initialize map centered at the first GPS coordinate
        start_coords = (self.data.iloc[0]['Latitude'], self.data.iloc[0]['Longitude'])
        race_map = folium.Map(location=start_coords, zoom_start=15)

        # Add route to the map
        points = []
        for _, row in self.data.iterrows():
            point = (row['Latitude'], row['Longitude'])
            points.append(point)
            folium.CircleMarker(
                location=point,
                radius=5,
                popup=f"Speed: {row['Speed (km/h)']} km/h\nRPM: {row['RPM']}\nGear: {row['Gear Position']}",
                color='blue',
                fill=True,
                fill_color='blue'
            ).add_to(race_map)

        # Draw lines between points
        folium.PolyLine(points, color='red', weight=2.5, opacity=1).add_to(race_map)

        # Save map to HTML
        race_map.save("analysisMap.html")

        # Add JavaScript to dynamically identify and initialize the map object
        with open("analysisMap.html", "a") as f:
            f.write("""
            <script>
                // Dynamically find the map object by querying the DOM
                const mapContainer = document.querySelector('[id^="map_"]');
                if (mapContainer) {
                    const mapId = mapContainer.id;
                    if (typeof window[mapId] !== 'undefined') {
                        window.map = window[mapId];
                    } else {
                        console.error('Map object not found for ID:', mapId);
                    }
                } else {
                    console.error('Map container not found.');
                }
            </script>
            """)

        return race_map

    def update_info(self, index):
        # Update info label
        row = self.data.iloc[index]
        self.info_label.setText(
            f"Timestamp: {row['Timestamp']}, Speed: {row['Speed (km/h)']} km/h, "
            f"RPM: {row['RPM']}, Gear: {row['Gear Position']}"
        )

        # Use JavaScript to update the map dynamically without reloading
        js_code = f'''
        if (typeof window.map === 'undefined') {{
            console.error("Map object not found.");
        }} else {{
            // Remove the previous highlight marker if it exists
            if (typeof window.currentMarker !== 'undefined') {{
                window.map.removeLayer(window.currentMarker);
            }}

            // Add a new marker for the current point
            var currentPoint = [{row['Latitude']}, {row['Longitude']}];
            window.currentMarker = L.circleMarker(currentPoint, {{
                radius: 8,
                color: 'green',
                fillColor: 'green',
                fillOpacity: 1
            }}).addTo(window.map);

            // Optionally, pan to the current point without resetting zoom
            window.map.panTo(currentPoint);
        }}
        '''

        self.map_view.page().runJavaScript(js_code)

        # Update graphs
        self.update_graphs(index)

    def init_ui(self):
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Layout
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # Map view
        self.map_view = QWebEngineView()
        self.map_view.setHtml(open("analysisMap.html").read())
        layout.addWidget(self.map_view)

        # Slider
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(len(self.data) - 1)
        self.slider.valueChanged.connect(self.update_info)
        layout.addWidget(self.slider)

        # Info label
        self.info_label = QLabel("Hover over points on the map to view details.")
        layout.addWidget(self.info_label)

        # Graphs
        graph_layout = QHBoxLayout()
        self.rpm_canvas = FigureCanvas(plt.figure())
        self.speed_canvas = FigureCanvas(plt.figure())
        graph_layout.addWidget(self.rpm_canvas)
        graph_layout.addWidget(self.speed_canvas)
        layout.addLayout(graph_layout)

        # Initial graph update
        self.update_graphs(0)

    def update_graphs(self, index):
        # Clear existing axes
        self.rpm_canvas.figure.clf()
        self.speed_canvas.figure.clf()

        # Update RPM graph
        rpm_ax = self.rpm_canvas.figure.add_subplot(111)
        start = max(0, index - 10)
        end = min(len(self.data), index + 10)
        rpm_ax.plot(range(start - index, end - index), self.data['RPM'][start:end], label='RPM')
        rpm_ax.axvline(0, color='red', linestyle='--', label='Current Point')
        rpm_ax.set_ylim(0, 18000)  # Limit y-axis for RPM
        rpm_ax.legend()
        self.rpm_canvas.draw()

        # Update Speed graph
        speed_ax = self.speed_canvas.figure.add_subplot(111)
        speed_ax.plot(range(start - index, end - index), self.data['Speed (km/h)'][start:end], label='Speed (km/h)')
        speed_ax.axvline(0, color='red', linestyle='--', label='Current Point')
        speed_ax.set_ylim(0, 120)  # Limit y-axis for Speed
        speed_ax.legend()
        self.speed_canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RaceDataAnalyzer()
    window.show()
    sys.exit(app.exec_())
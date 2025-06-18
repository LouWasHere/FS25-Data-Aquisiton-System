import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QSlider, QHBoxLayout, QPushButton, QComboBox, QDialog, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView
import folium
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import Qt

class DataPointDialog(QDialog):
    def __init__(self, data_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("All Data for Selected Point")
        self.setMinimumSize(400, 400)
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        # Format the data as key: value lines
        text = "\n".join(f"{k}: {v}" for k, v in data_dict.items())
        self.text_edit.setText(text)
        layout.addWidget(self.text_edit)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)

class RaceDataAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Race Data Analyzer")
        self.setGeometry(100, 100, 800, 600)

        # Load data
        self.data = pd.read_csv("recorded_data.csv")

        # Dynamically find relevant columns
        self.timestamp_col = self.find_column(['Timestamp'])
        self.speed_col = self.find_column(['Speed', 'Wheel Speed'])
        self.rpm_col = self.find_column(['RPM'])
        self.gear_col = self.find_column(['Gear'])
        self.lat_col = self.find_column(['Latitude'])
        self.lon_col = self.find_column(['Longitude'])
        self.engine_temp_col = self.find_column(['Engine Temperature'])

        # Create map
        self.map = self.create_map()

        # Set up UI
        self.init_ui()

    def find_column(self, keywords):
        """Find the first column containing any of the keywords (case-insensitive)."""
        for col in self.data.columns:
            for kw in keywords:
                if kw.lower() in col.lower():
                    return col
        return None

    def create_map(self):
        # Use the first valid GPS coordinate
        start_coords = (self.data.iloc[0][self.lat_col], self.data.iloc[0][self.lon_col])
        race_map = folium.Map(location=start_coords, zoom_start=15)

        # Add route to the map
        points = []
        for _, row in self.data.iterrows():
            point = (row[self.lat_col], row[self.lon_col])
            points.append(point)
            folium.CircleMarker(
                location=point,
                radius=5,
                popup=f"Speed: {row.get(self.speed_col, 'N/A')} km/h\nRPM: {row.get(self.rpm_col, 'N/A')}\nGear: {row.get(self.gear_col, 'N/A')}\nEngine Temp: {row.get(self.engine_temp_col, 'N/A')}",
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
            f"Timestamp: {row.get(self.timestamp_col, 'N/A')}, "
            f"Speed: {row.get(self.speed_col, 'N/A')} km/h, "
            f"RPM: {row.get(self.rpm_col, 'N/A')}, "
            f"Gear: {row.get(self.gear_col, 'N/A')}, "
            f"Engine Temp: {row.get(self.engine_temp_col, 'N/A')}"
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
            var currentPoint = [{row[self.lat_col]}, {row[self.lon_col]}];
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

        # "Show All Data" button
        self.show_data_btn = QPushButton("Show All Data for This Point")
        self.show_data_btn.clicked.connect(self.show_all_data_for_point)
        layout.addWidget(self.show_data_btn)

        # Graphs
        graph_layout = QHBoxLayout()
        self.rpm_canvas = FigureCanvas(plt.figure())
        self.speed_canvas = FigureCanvas(plt.figure())
        graph_layout.addWidget(self.rpm_canvas)
        graph_layout.addWidget(self.speed_canvas)
        layout.addLayout(graph_layout)

        # Initial graph update
        self.update_graphs(0)

    def show_all_data_for_point(self):
        idx = self.slider.value()
        row = self.data.iloc[idx]
        # Convert row to dict, replacing NaN with "N/A"
        data_dict = {col: (row[col] if pd.notnull(row[col]) else "N/A") for col in self.data.columns}
        dlg = DataPointDialog(data_dict, self)
        dlg.exec_()

    def update_graphs(self, index):
        # Clear existing axes
        self.rpm_canvas.figure.clf()
        self.speed_canvas.figure.clf()

        # Update RPM graph
        rpm_ax = self.rpm_canvas.figure.add_subplot(111)
        start = max(0, index - 10)
        end = min(len(self.data), index + 10)
        if self.rpm_col:
            rpm_ax.plot(range(start - index, end - index), self.data[self.rpm_col][start:end], label='RPM')
        rpm_ax.axvline(0, color='red', linestyle='--', label='Current Point')
        rpm_ax.set_ylim(0, 18000)  # Limit y-axis for RPM
        rpm_ax.legend()
        self.rpm_canvas.draw()

        # Update Speed graph
        speed_ax = self.speed_canvas.figure.add_subplot(111)
        if self.speed_col:
            speed_ax.plot(range(start - index, end - index), self.data[self.speed_col][start:end], label='Speed (km/h)')
        speed_ax.axvline(0, color='red', linestyle='--', label='Current Point')
        speed_ax.set_ylim(0, 120)  # Limit y-axis for Speed
        speed_ax.legend()
        self.speed_canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RaceDataAnalyzer()
    window.show()
    sys.exit(app.exec_())
# QGIS River Flow Analysis Plugin

This QGIS plugin enables environmental and hydrological analysis based on river flow data. It is designed to assist users in visualizing, analyzing, and interpreting temporal changes and trends in river flow using CSV datasets.

## 🌊 Features

- Import river flow data from CSV files.
- Visualize time series of river discharge.
- Analyze seasonal variation and long-term trends.
- Generate summary statistics.
- Export plots and results for reporting.

## 🛠️ Installation

1. Open **QGIS** (tested with version 3.40.6 and above).
2. Go to `Plugins` > `Manage and Install Plugins`.
3. Click on `Install from ZIP` if installing manually.
4. Clone or download this repository:
   ```bash
   git clone https://github.com/engingul/Qgis-river-flow-analysis.git
5.Copy the folder to your QGIS plugin directory:
Linux: ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins
Windows: C:\Users\<YourUsername>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins
6.Restart QGIS and enable the plugin from the Plugins menu.

## 📷 Screenshots

![Ekran görüntüsü 2025-06-10 163017](https://github.com/user-attachments/assets/6776c8a4-0857-417e-a50a-fb3295ccd205)

## 📊 Usage
1. Load a CSV file containing river flow data (Date and Discharge columns).
2. Use the plugin panel to select:
- Date range
- Visualization type (line chart, bar chart)
- Analysis options (trendline, seasonality, etc.)
3. Click Run Analysis to generate graphs and summaries.
4. Export charts or results if needed.

## 🧪 Dependencies
QGIS 3.x

Python 3.8+

PyQt5

matplotlib

pandas

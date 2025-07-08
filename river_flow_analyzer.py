import os
import csv
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from PyQt5.QtWidgets import (QAction, QFileDialog, QMessageBox, QWidget, QVBoxLayout,
                             QLabel, QPushButton, QListWidget, QDateEdit, QHBoxLayout,
                             QCheckBox, QComboBox, QProgressBar, QTabWidget, QTextBrowser)
from PyQt5.QtCore import QDate
from PyQt5 import QtCore
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import mplcursors
from scipy.stats import linregress
import pymannkendall as mk
from qgis.core import (QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsRectangle,
                       QgsPointXY, QgsProject, QgsMarkerSymbol, QgsCoordinateReferenceSystem, QgsVectorFileWriter)
from qgis.PyQt.QtCore import QVariant
# Kodun başına ekledik hata uyarıları konsolda gizlemek için
import warnings
warnings.filterwarnings("ignore")


class RiverFlowAnalyzer:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)  # Eklenti dizinini al
        self.canvas = iface.mapCanvas()
        self.station_locations = {}
        self.dialog = None

    def run(self):
        # Ana pencereyi QTabWidget olarak oluştur
        self.dialog = QTabWidget()
        self.dialog.setWindowTitle("Nehir Akış Analizi")
        self.dialog.setMinimumWidth(600)
        self.dialog.setMinimumHeight(500)

        # 1. Sekme: Analiz
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout()

        # File selection
        self.file_label = QLabel("CSV Dosyalarını Seçin:")
        analysis_layout.addWidget(self.file_label)

        self.select_button = QPushButton("Dosyaları Seç")
        self.select_button.clicked.connect(self.load_csv_files)
        analysis_layout.addWidget(self.select_button)

        self.station_list = QListWidget()
        self.station_list.setSelectionMode(QListWidget.MultiSelection)
        analysis_layout.addWidget(self.station_list)

        # Date range
        self.date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate(2014, 10, 1))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate(2015, 9, 30))
        self.date_layout.addWidget(QLabel("Başlangıç Tarihi:"))
        self.date_layout.addWidget(self.start_date)
        self.date_layout.addWidget(QLabel("Bitiş Tarihi:"))
        self.date_layout.addWidget(self.end_date)
        analysis_layout.addLayout(self.date_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        analysis_layout.addWidget(self.progress)

        # Export options
        self.export_checkbox = QCheckBox("Sonuçları dışa aktar")
        analysis_layout.addWidget(self.export_checkbox)

        self.export_layout = QHBoxLayout()
        self.export_layout.addWidget(QLabel("Dışa Aktarım Formatı:"))
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["CSV", "Excel", "Shapefile", "GeoPackage"])
        self.export_layout.addWidget(self.export_format_combo)
        analysis_layout.addLayout(self.export_layout)

        # QGIS Map options
        self.map_checkbox = QCheckBox("Haritada Göster")
        analysis_layout.addWidget(self.map_checkbox)

        self.zoom_checkbox = QCheckBox("Seçilen İstasyona Zoom Yap")
        analysis_layout.addWidget(self.zoom_checkbox)

        # Analysis buttons
        buttons = [
            ("Trend Analizi", "trend"),
            ("Maksimum Akım Günü", "maxflow"),
            ("İstasyon Ortalama Akım", "avgflow"),
            ("Standart Sapma Analizi", "stddev"),
            ("Minimum Akım Günü", "minflow"),
            ("Veri Sayısı Analizi", "count"),
            ("Yıllık Toplam Akım", "sumflow"),
            ("Maksimum Akım Mevsimi", "season"),
            ("Aylık Ortalama Akım", "monthly_avg"),
            ("Mann-Kendall Trend Testi", "mann_kendall"),
            ("Taşkın Eşiği Analizi", "flood"),
            ("Kurak Dönem Analizi", "dry")
        ]

        for text, analysis_type in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, at=analysis_type: self.perform_analysis(at))
            analysis_layout.addWidget(btn)

        self.all_button = QPushButton("Tüm Analizleri Yap")
        self.all_button.clicked.connect(self.perform_all_analyses)
        analysis_layout.addWidget(self.all_button)

        analysis_tab.setLayout(analysis_layout)
        self.dialog.addTab(analysis_tab, "Analiz")

        # 2. Sekme: Hakkında
        about_tab = QWidget()
        about_layout = QVBoxLayout()

        # Logo veya başlık
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            about_layout.addWidget(logo_label)
        else:
            about_layout.addWidget(QLabel("Nehir Akış Analiz Eklentisi", alignment=Qt.AlignCenter))

        # Geliştirici bilgileri
        about_text = """
        <h2>Nehir Akış Analiz Eklentisi</h2>
        <p><b>Sürüm:</b> 1.0.0</p>
        <p><b>Geliştirici:</b> Engin GÜL</p>
        <p><b>E-posta:</b> engin_gul@outlook.com.tr</p>
        <p><b>Github:</b> https://github.com/engingul</p>
        <p><b>Geliştirme Tarihi:</b> 28 Mayıs 2025</p>

        <h3>Özellikler</h3>
        <ul>
            <li>Akım trend analizi</li>
            <li>Maksimum ve minimum akım tespiti</li>
            <li>Aylık ortalama akım hesaplama</li>
            <li>Taşkın ve kurak dönem analizleri</li>
            <li>QGIS harita entegrasyonu</li>
        </ul>

        <h3>Lisans</h3>
        <p>Bu eklenti MIT lisansı ile lisanslanmıştır. 
        Kaynak kodları GitHub üzerinde bulunabilir.</p>
        
        <h4>TÜBİTAK 2209/A ÜNİVERSİTE ÖĞRENCİLERİ ARAŞTIRMA PROJELERİ DESTEK PROGRAMI</h4>
        <p>SÜLEYMAN DEMİREL ÜNİVERSİTESİ BİLGİSAYAR MÜHENDİSLİĞİ BÖLÜMÜ</p>
        <p>Akademik Danışman:	Doç. Dr. Fatih Ahmet ŞENEL</p>
        <p>Öğrenci:	Engin GÜL</p>
        <p>
        </p>
        <h5>Teşekkür</h5>
        <p>Desteklerinden dolayı Prof. Dr. Okan FISTIKOĞLU ve Dr. Öğr. Üyesi Meltem KAÇIKOÇ'a teşekkür ederiz.</p>
        """

        about_browser = QTextBrowser()
        about_browser.setOpenExternalLinks(True)
        about_browser.setHtml(about_text)
        about_layout.addWidget(about_browser)

        # Ekibin fotoğrafları (opsiyonel)
        photo_layout = QHBoxLayout()
        for i in range(1, 4):  # 3 takım üyesi
            photo_path = os.path.join(os.path.dirname(__file__), f'team{i}.png')
            if os.path.exists(photo_path):
                photo_label = QLabel()
                pixmap = QPixmap(photo_path)
                pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio)
                photo_label.setPixmap(pixmap)
                photo_label.setAlignment(Qt.AlignCenter)
                photo_layout.addWidget(photo_label)
        about_layout.addLayout(photo_layout)

        # Takım üyeleri bilgisi
        team_label = QLabel("<p><b>Bu proje Tübitak 2209-A kapsamında desteklenmiştir")
        team_label.setAlignment(Qt.AlignCenter)
        about_layout.addWidget(team_label)

        about_tab.setLayout(about_layout)
        self.dialog.addTab(about_tab, "Hakkında")

        self.dialog.show()
        return self.dialog

    def load_csv_files(self):
        self.files, _ = QFileDialog.getOpenFileNames(None, "CSV Dosyalarını Seç", "", "CSV files (*.csv)")
        self.dataframes = []
        self.station_list.clear()
        self.station_locations = {}

        for file in self.files:
            try:
                df = pd.read_csv(file, encoding="utf-8")
                df.columns = [col.strip() for col in df.columns]
                df = df.rename(columns={
                    "İstasyon": "Station",
                    "Tarih": "Date",
                    "Akım (m³/s)": "Flow",
                    "Enlem": "Latitude",
                    "Boylam": "Longitude"
                })
                df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors='coerce')
                df = df.dropna(subset=["Date"])

                # Store station locations
                for station, group in df.groupby("Station"):
                    if station not in self.station_locations:
                        self.station_locations[station] = {
                            'Latitude': group['Latitude'].iloc[0],
                            'Longitude': group['Longitude'].iloc[0]
                        }

                self.dataframes.append(df)
                for station in df["Station"].unique():
                    if not self.station_list.findItems(station, QtCore.Qt.MatchExactly):
                        self.station_list.addItem(station)
            except Exception as e:
                QMessageBox.warning(None, "Hata", f"{file} dosyası yüklenirken hata oluştu: {e}")

    def perform_analysis(self, analysis_type):
        selected_stations = [item.text() for item in self.station_list.selectedItems()]
        if not selected_stations:
            QMessageBox.warning(None, "Uyarı", "Lütfen en az bir istasyon seçin.")
            return

        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()

        all_df = pd.concat(self.dataframes, ignore_index=True)
        filtered_df = all_df[(all_df["Station"].isin(selected_stations)) &
                             (all_df["Date"] >= pd.to_datetime(start_date)) &
                             (all_df["Date"] <= pd.to_datetime(end_date))]

        result_df = pd.DataFrame()
        results = []  # Results will be collected here

        # Show progress
        self.progress.setVisible(True)
        self.progress.setRange(0, len(selected_stations))

        try:
            if analysis_type == "trend":
                fig, ax = plt.subplots(figsize=(12, 6))
                for i, station in enumerate(selected_stations):
                    self.progress.setValue(i)
                    QtCore.QCoreApplication.processEvents()

                    station_df = filtered_df[filtered_df["Station"] == station].copy()
                    station_df = station_df.dropna(subset=["Date", "Flow"])
                    ax.plot(station_df["Date"], station_df["Flow"], label=f"{station} - Akım")

                    station_df = station_df.sort_values("Date")
                    x = mdates.date2num(station_df["Date"])
                    y = station_df["Flow"].values
                    slope, intercept, _, _, _ = linregress(x, y)
                    trend = slope * x + intercept
                    ax.plot(station_df["Date"], trend, linestyle="--", label=f"{station} - Trend")

                ax.set_title(f"Trend Analizi")
                ax.set_xlabel("Tarih")
                ax.set_ylabel("Akım (m³/s)")
                ax.legend()
                ax.grid(True)
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.show(block=False)

            elif analysis_type == "sumflow":
                fig, ax = plt.subplots(figsize=(10, 6))
                for i, station in enumerate(selected_stations):
                    self.progress.setValue(i)
                    QtCore.QCoreApplication.processEvents()

                    station_df = filtered_df[filtered_df["Station"] == station].copy()
                    station_df["Year"] = station_df["Date"].dt.year
                    yearly_sum = station_df.groupby("Year")["Flow"].sum().reset_index()
                    yearly_sum["Station"] = station

                    # Collect results
                    for _, row in yearly_sum.iterrows():
                        results.append({
                            "Station": station,
                            "Year": row["Year"],
                            "Total Flow": row["Flow"]
                        })

                    # Plot
                    ax.plot(yearly_sum["Year"], yearly_sum["Flow"], marker='o', linestyle='-', label=station)

                ax.set_title("Yıllık Toplam Akım")
                ax.set_xlabel("Yıl")
                ax.set_ylabel("Toplam Akım (m³/s)")
                ax.legend()
                ax.grid(True)
                plt.tight_layout()
                plt.show(block=False)

                # Create result DataFrame
                result_df = pd.DataFrame(results)

            elif analysis_type == "season":
                for i, station in enumerate(selected_stations):
                    self.progress.setValue(i)
                    QtCore.QCoreApplication.processEvents()

                    station_df = filtered_df[filtered_df["Station"] == station].copy()
                    if station_df.empty:
                        continue

                    # Determine seasons: 1=Winter, 2=Spring, 3=Summer, 4=Autumn
                    station_df["Season"] = station_df["Date"].dt.month % 12 // 3 + 1

                    # Find max flow
                    max_flow_row = station_df.loc[station_df["Flow"].idxmax()]
                    season_num = max_flow_row["Season"]

                    # Map season number to name
                    seasons = {1: "Kış", 2: "İlkbahar", 3: "Yaz", 4: "Sonbahar"}
                    season_name = seasons.get(season_num, "Bilinmeyen")

                    results.append({
                        "Station": station,
                        "MaxFlow": max_flow_row["Flow"],
                        "Season": season_name,
                        "Date": max_flow_row["Date"]
                    })

                # Create result DataFrame
                result_df = pd.DataFrame(results)



            elif analysis_type == "monthly_avg":
                fig, ax = plt.subplots(figsize=(12, 6))
                months = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                          'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
                for i, station in enumerate(selected_stations):
                    self.progress.setValue(i)
                    QtCore.QCoreApplication.processEvents()
                    station_df = filtered_df[filtered_df["Station"] == station].copy()
                    station_df["Month"] = station_df["Date"].dt.month.astype(int)
                    monthly_avg = station_df.groupby("Month")["Flow"].mean().reset_index()
                    # Eksik ayları tamamla
                    all_months = pd.DataFrame({'Month': range(1, 13)})
                    monthly_avg = pd.merge(all_months, monthly_avg, on='Month', how='left')
                    monthly_avg['Flow'] = monthly_avg['Flow'].fillna(0)
                    # Collect results
                    for _, row in monthly_avg.iterrows():
                        month_index = int(row["Month"]) - 1
                        results.append({
                            "Station": station,
                            "Month": months[month_index],
                            "Average Flow": row["Flow"]
                        })
                    # Plot with month names
                    # Tüm aylar için değerleri al
                    flow_values = monthly_avg['Flow'].values
                    ax.plot(months, flow_values, marker='o', label=station)
                ax.set_title("Aylık Ortalama Akım")
                ax.set_xlabel("Ay")
                ax.set_ylabel("Ortalama Akım (m³/s)")
                ax.legend()
                ax.grid(True)
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.show(block=False)
                # Create result DataFrame
                result_df = pd.DataFrame(results)

            elif analysis_type == "mann_kendall":
                for i, station in enumerate(selected_stations):
                    self.progress.setValue(i)
                    QtCore.QCoreApplication.processEvents()

                    station_df = filtered_df[filtered_df["Station"] == station].copy()
                    station_df = station_df.sort_values("Date")
                    station_df = station_df.dropna(subset=["Flow"])

                    if len(station_df) < 4:
                        results.append({
                            "Station": station,
                            "Trend": "Yetersiz Veri",
                            "P-value": np.nan,
                            "Z-score": np.nan,
                            "H0": np.nan
                        })
                        continue

                    try:
                        result = mk.original_test(station_df["Flow"])
                        trend_dict = {
                            'increasing': 'Artış',
                            'decreasing': 'Azalış',
                            'no trend': 'Trend Yok'
                        }
                        trend_name = trend_dict.get(result.trend, result.trend)

                        results.append({
                            "Station": station,
                            "Trend": trend_name,
                            "P-value": result.p,
                            "Z-score": result.z,
                            "H0": "Red" if result.h else "Kabul"
                        })
                    except Exception as e:
                        QMessageBox.warning(None, "Hata", f"{station} için Mann-Kendall testi yapılamadı: {str(e)}")

                # Create result DataFrame
                result_df = pd.DataFrame(results)

            elif analysis_type == "flood":
                for i, station in enumerate(selected_stations):
                    self.progress.setValue(i)
                    QtCore.QCoreApplication.processEvents()

                    station_df = filtered_df[filtered_df["Station"] == station].copy()
                    if station_df.empty:
                        continue

                    threshold = station_df["Flow"].quantile(0.9)
                    flood_days = station_df[station_df["Flow"] > threshold].shape[0]
                    total_days = station_df.shape[0]
                    flood_ratio = flood_days / total_days if total_days > 0 else 0

                    results.append({
                        "Station": station,
                        "Flood_Threshold": threshold,
                        "Flood_Days": flood_days,
                        "Flood_Ratio": flood_ratio
                    })

                # Create result DataFrame
                result_df = pd.DataFrame(results)

            elif analysis_type == "dry":
                for i, station in enumerate(selected_stations):
                    self.progress.setValue(i)
                    QtCore.QCoreApplication.processEvents()

                    station_df = filtered_df[filtered_df["Station"] == station].copy()
                    if station_df.empty:
                        continue

                    avg_flow = station_df["Flow"].mean()
                    dry_threshold = avg_flow * 0.2

                    # Identify dry periods
                    station_df = station_df.sort_values("Date")
                    station_df['is_dry'] = station_df['Flow'] < dry_threshold
                    station_df['period'] = (station_df['is_dry'] != station_df['is_dry'].shift(1)).cumsum()

                    dry_periods = station_df[station_df['is_dry']].groupby('period')
                    period_lengths = dry_periods.size()
                    num_periods = len(period_lengths)
                    avg_duration = period_lengths.mean() if num_periods > 0 else 0

                    results.append({
                        "Station": station,
                        "Dry_Threshold": dry_threshold,
                        "Dry_Periods": num_periods,
                        "Avg_Duration": avg_duration
                    })

                # Create result DataFrame
                result_df = pd.DataFrame(results)

            else:  # Existing analyses
                for i, station in enumerate(selected_stations):
                    self.progress.setValue(i)
                    QtCore.QCoreApplication.processEvents()

                    station_df = filtered_df[filtered_df["Station"] == station].copy()
                    if station_df.empty:
                        continue

                    if analysis_type == "maxflow":
                        max_row = station_df.loc[station_df["Flow"].idxmax()]
                        results.append(max_row.to_dict())
                    elif analysis_type == "avgflow":
                        avg_flow = station_df["Flow"].mean()
                        results.append({"Station": station, "Average Flow": avg_flow})
                    elif analysis_type == "stddev":
                        std_dev = station_df["Flow"].std()
                        results.append({"Station": station, "Std Dev": std_dev})
                    elif analysis_type == "minflow":
                        min_row = station_df.loc[station_df["Flow"].idxmin()]
                        results.append(min_row.to_dict())
                    elif analysis_type == "count":
                        count = station_df["Flow"].count()
                        results.append({"Station": station, "Count": count})

                # Create result DataFrame
                result_df = pd.DataFrame(results)

            # Show results if not graphical
            if analysis_type not in ["trend", "sumflow", "monthly_avg"] and not result_df.empty:
                result_text = result_df.to_string(index=False)
                QMessageBox.information(None, f"{analysis_type.capitalize()} Analizi", result_text)

            # Export results
            if self.export_checkbox.isChecked() and not result_df.empty:
                out_path = os.path.expanduser("~/Desktop")
                ext = self.export_format_combo.currentText().lower()

                if ext in ["shapefile", "geopackage"]:
                    self.export_as_vector(result_df, analysis_type, start_date, end_date, ext)
                else:
                    out_file = os.path.join(out_path,
                                            f"nehir_akis_{analysis_type}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.{ext if ext != 'excel' else 'xlsx'}")
                    if ext == "csv":
                        result_df.to_csv(out_file, index=False, encoding="utf-8-sig")
                    else:
                        result_df.to_excel(out_file, index=False)
                    QMessageBox.information(None, "Başarılı", f"Sonuçlar başarıyla kaydedildi:\n{out_file}")

            # Show on map
            if self.map_checkbox.isChecked() and not result_df.empty:
                self.show_on_map(result_df, analysis_type)

                # Zoom to selected station
                if self.zoom_checkbox.isChecked() and len(selected_stations) == 1:
                    self.zoom_to_station(selected_stations[0])

        except Exception as e:
            QMessageBox.critical(None, "Hata", f"Analiz sırasında hata oluştu: {str(e)}")
        finally:
            self.progress.setVisible(False)

    def export_as_vector(self, result_df, analysis_type, start_date, end_date, format):
        """Export results as vector layer (Shapefile or GeoPackage)"""
        # Create memory layer
        layer_name = f"nehir_akis_{analysis_type}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        vl = self.create_vector_layer(result_df, layer_name)

        if not vl:
            QMessageBox.warning(None, "Uyarı", "Vektör katmanı oluşturulamadı. Konum bilgileri eksik olabilir.")
            return

        # Save to file
        out_path = os.path.expanduser("~/Desktop")
        if format == "shapefile":
            filename = f"{layer_name}.shp"
            file_format = "ESRI Shapefile"
        else:  # geopackage
            filename = f"{layer_name}.gpkg"
            file_format = "GPKG"

        out_file = os.path.join(out_path, filename)

        # Dışa aktarım işlemi
        error = QgsVectorFileWriter.writeAsVectorFormat(
            vl,
            out_file,
            "UTF-8",
            QgsCoordinateReferenceSystem("EPSG:4326"),
            file_format
        )

        if error[0] == QgsVectorFileWriter.NoError:
            QMessageBox.information(None, "Başarılı", f"Vektör katmanı başarıyla kaydedildi:\n{out_file}")
            # Add layer to QGIS
            saved_layer = QgsVectorLayer(out_file, layer_name, "ogr")
            QgsProject.instance().addMapLayer(saved_layer)
        else:
            QMessageBox.warning(None, "Hata", f"Vektör katmanı kaydedilemedi: {error}")

    def create_vector_layer(self, result_df, layer_name):
        """Create a point vector layer from analysis results"""
        # Check if we have location data
        if "Latitude" not in result_df.columns or "Longitude" not in result_df.columns:
            # Try to add from stored locations
            for idx, row in result_df.iterrows():
                station = row["Station"]
                if station in self.station_locations:
                    result_df.at[idx, "Latitude"] = self.station_locations[station]["Latitude"]
                    result_df.at[idx, "Longitude"] = self.station_locations[station]["Longitude"]

        if "Latitude" not in result_df.columns or "Longitude" not in result_df.columns:
            return None

        # Create vector layer
        vl = QgsVectorLayer("Point?crs=EPSG:4326", layer_name, "memory")
        provider = vl.dataProvider()

        # Add fields
        fields = []
        for col in result_df.columns:
            if col not in ["Latitude", "Longitude"]:
                # Determine field type
                sample_value = result_df[col].iloc[0] if not result_df.empty else None

                # Create field with explicit parameters
                if isinstance(sample_value, (int, np.integer)):
                    field = QgsField(name=col, type=QVariant.Int, len=0, prec=0, comment='', typeName='integer')
                elif isinstance(sample_value, (float, np.floating)):
                    field = QgsField(name=col, type=QVariant.Double, len=0, prec=0, comment='',
                                     typeName='double precision')
                elif isinstance(sample_value, pd.Timestamp):
                    field = QgsField(name=col, type=QVariant.DateTime, len=0, prec=0, comment='', typeName='datetime')
                else:
                    field = QgsField(name=col, type=QVariant.String, len=0, prec=0, comment='', typeName='text')

                fields.append(field)

        provider.addAttributes(fields)
        vl.updateFields()

        # Add features
        for _, row in result_df.iterrows():
            feat = QgsFeature()
            point = QgsPointXY(float(row["Longitude"]), float(row["Latitude"]))
            feat.setGeometry(QgsGeometry.fromPointXY(point))

            # Set attributes
            attrs = []
            for field in fields:
                col = field.name()
                value = row[col]

                # Convert pandas Timestamp to QDateTime
                if isinstance(value, pd.Timestamp):
                    qdate = QtCore.QDate(value.year, value.month, value.day)
                    qtime = QtCore.QTime(value.hour, value.minute, value.second)
                    value = QtCore.QDateTime(qdate, qtime)

                attrs.append(value)

            feat.setAttributes(attrs)
            provider.addFeature(feat)

        vl.updateExtents()
        return vl

    def show_on_map(self, result_df, analysis_type):
        """Show analysis results on QGIS map"""
        vl = self.create_vector_layer(result_df, f"RiverFlow_{analysis_type}")
        if not vl:
            QMessageBox.warning(None, "Uyarı", "Harita görüntülenemedi. Konum bilgileri eksik olabilir.")
            return

        # Apply styling based on analysis type
        symbol = QgsMarkerSymbol.createSimple({
            'name': 'circle',
            'color': 'blue',
            'size': '3.0'
        })
        vl.renderer().setSymbol(symbol)

        # Add layer to QGIS
        QgsProject.instance().addMapLayer(vl)

        # Zoom to layer extent
        self.canvas.setExtent(vl.extent())
        self.canvas.refresh()

    def zoom_to_station(self, station_name):
        """Zoom to a specific station on the map"""
        if station_name in self.station_locations:
            loc = self.station_locations[station_name]
            point = QgsPointXY(float(loc["Longitude"]), float(loc["Latitude"]))

            # Create point geometry and buffer it
            geom = QgsGeometry.fromPointXY(point)
            buffered_geom = geom.buffer(0.1, 5)  # 0.1 derece buffer

            # Set extent to buffered geometry
            self.canvas.setExtent(buffered_geom.boundingBox())
            self.canvas.refresh()
        else:
            QMessageBox.warning(None, "Uyarı", f"{station_name} istasyonunun konum bilgisi bulunamadı.")

    def perform_all_analyses(self):
        plt.ioff()
        analysis_types = [
            "trend", "maxflow", "avgflow", "stddev", "minflow", "count", "sumflow",
            "season", "monthly_avg", "mann_kendall", "flood", "dry"
        ]
        for analysis_type in analysis_types:
            self.perform_analysis(analysis_type)
        plt.ion()

    def initGui(self):
        # ... diğer GUI başlatmalar
        self.load_base_layers()  # Temel katmanları yükle

    def load_base_layers(self):
        """Eklenti başlatıldığında temel katmanları yükler"""
        layers_to_load = {
            "rivers": {
                "path": os.path.join(self.plugin_dir, "layers", "rivers.gpkg"),
                "name": "Nehir Hatları"
            },
            "stations": {
                "path": os.path.join(self.plugin_dir, "layers", "stations.gpkg"),
                "name": "Akım İstasyonları"
            }
        }

        for layer_id, layer_info in layers_to_load.items():
            if not QgsProject.instance().mapLayersByName(layer_info["name"]):
                layer = QgsVectorLayer(layer_info["path"], layer_info["name"], "ogr")
                if layer.isValid():
                    QgsProject.instance().addMapLayer(layer)
                    print(f"{layer_info['name']} katmanı yüklendi")
                else:
                    print(f"Hata: {layer_info['name']} katmanı geçersiz")
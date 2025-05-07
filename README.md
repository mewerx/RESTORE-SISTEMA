mport sys
import os
import pandas as pd
import folium
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QComboBox, QTextEdit, QFileDialog,
    QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QImage, QPixmap
from io import BytesIO
from datetime import datetime, timedelta, time
from folium.plugins import HeatMap
import seaborn as sns
from collections import Counter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib import colors
from reportlab.lib.units import inch
from PIL import Image  # Necesario para trabajar con QImage en ReportLab
from sklearn.cluster import DBSCAN
import numpy as np
import matplotlib.colors
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QComboBox, QTextEdit, QFileDialog,
    QTableWidget, QTableWidgetItem, QTabWidget  # Agrega QTabWidget
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("COMSTAT UNIMER")
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet("background-color: #1c1f26; color: white;")
        self.df = None
        self.df_original = None
        self.modelo_riesgo = None
        main_layout = QVBoxLayout()
        # Encabezado
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("COMSTAT UNIMER", styleSheet="font-size: 24px; font-weight: bold;"))
        header_layout.addStretch()
        header_layout.addWidget(QPushButton("Actualizar Datos", clicked=self.cargar_y_mostrar_datos, styleSheet="padding: 8px; background-color: #3a3f4b; color: white;"))
        header_layout.addWidget(QPushButton("Generar Informe PDF", clicked=self.guardar_informe_pdf, styleSheet="padding: 8px; background-color: #4CAF50; color: white;"))  # Botón movido aquí
        header_layout.addWidget(QPushButton("Ejecutar Modelo IA", clicked=self.ejecutar_modelo_ia, styleSheet="padding: 8px; background-color: #3a3f4b; color: white;"))
        main_layout.addLayout(header_layout)
        # Sección de Filtros
        filtros_layout = QHBoxLayout()
        self.año_label = QLabel("Año:", styleSheet="font-size: 12px;")
        self.año_combo = QComboBox(self)
        filtros_layout.addWidget(self.año_label)
        filtros_layout.addWidget(self.año_combo)
        self.mes_label = QLabel("Mes:", styleSheet="font-size: 12px;")
        self.mes_combo = QComboBox(self)
        self.mes_combo.addItems(["Todos", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
        filtros_layout.addWidget(self.mes_label)
        filtros_layout.addWidget(self.mes_combo)
        self.colonia_label = QLabel("Colonia:", styleSheet="font-size: 12px;")
        self.colonia_combo = QComboBox(self)
        self.colonia_combo.addItem("Todas")
        filtros_layout.addWidget(self.colonia_label)
        filtros_layout.addWidget(self.colonia_combo)
        self.clasificacion_label = QLabel("Clasificación:", styleSheet="font-size: 12px;")
        self.clasificacion_combo = QComboBox(self)
        self.clasificacion_combo.addItem("Todas")
        filtros_layout.addWidget(self.clasificacion_label)
        filtros_layout.addWidget(self.clasificacion_combo)
        main_layout.addLayout(filtros_layout)
        # Zona central
        zona_central = QHBoxLayout()
        mapa_widget = QWidget()
        mapa_layout = QVBoxLayout()
        self.mapa_selector = QComboBox(self)
        self.placas_repetidas_df = None  # Inicializar el DataFrame de placas repetidas
        self.series_repetidas_df = None  # Inicializar el DataFrame de series repetida
        self.mapa_selector.addItems(["Puntos Rojos", "Mapa de Calor", "Riesgo por Colonia", "Clusters de Robos", "Placas Repetidas", "Series Repetidas"])
        self.mapa_selector.currentIndexChanged.connect(self.actualizar_mapa)
        mapa_layout.addWidget(self.mapa_selector)
        self.mapa_view = QWebEngineView()
        mapa_layout.addWidget(self.mapa_view)
        mapa_widget.setLayout(mapa_layout)
        zona_central.addWidget(mapa_widget)
        grafico_principal_widget = QWidget()
        grafico_principal_layout = QVBoxLayout()
        self.grafico_principal_selector = QComboBox(self)
        self.grafico_principal_selector.addItems(["Total de Robos por Año",
                                                 "Robos por Hora", "Robos por Clasificación"])
        self.grafico_principal_selector.currentIndexChanged.connect(self.actualizar_grafico_principal)
        grafico_principal_layout.addWidget(self.grafico_principal_selector)
        self.grafico_principal_view = QLabel("GRÁFICO PRINCIPAL", alignment=Qt.AlignCenter,
                                             styleSheet="background-color: #61a5c2; font-size: 16px;")
        grafico_principal_layout.addWidget(self.grafico_principal_view)
        grafico_principal_widget.setLayout(grafico_principal_layout)
        zona_central.addWidget(grafico_principal_widget)
        main_layout.addLayout(zona_central)
        # Zona inferior reestructurada
        zona_inferior = QHBoxLayout()
        # Tab Widget para Anomalías, Series Repetidas y Clusters
        self.tab_widget = QTabWidget()
        # Izquierda: Anomalías
        self.anomalias_tab = QWidget()
        self.anomalias_layout = QVBoxLayout()
        self.anomalias_label = QLabel("Anomalías:", styleSheet="font-size: 14px; font-weight: bold;")
        self.anomalias_text = QTextEdit(self)
        self.anomalias_text.setReadOnly(True)
        self.anomalias_text.setStyleSheet("background-color: #62aef4; color: black; font-size: 12px;")
        self.anomalias_layout.addWidget(self.anomalias_label)
        self.anomalias_layout.addWidget(self.anomalias_text)
        self.anomalias_tab.setLayout(self.anomalias_layout)
        self.tab_widget.addTab(self.anomalias_tab, "Anomalías")
        # Centro: Totales
        centro_inferior = QVBoxLayout()
        # Totales existentes
        self.total_robos_label = QLabel("Total Robos: ", alignment=Qt.AlignCenter,
                                         styleSheet="background-color: #2a2f38; font-size: 16px;")
        self.probabilidad_label = QLabel("Probabilidad de Robo: ", alignment=Qt.AlignCenter,
                                          styleSheet="background-color: #2a2f38; font-size: 16px;")
        centro_inferior.addWidget(self.total_robos_label)
        centro_inferior.addWidget(self.probabilidad_label)
        # Nuevos totales para series repetidas y placas repetidas
        self.total_series_repetidas_label = QLabel("Total Series Repetidas: ", alignment=Qt.AlignCenter,
                                                    styleSheet="background-color: #2a2f38; font-size: 16px;")
        self.total_placas_repetidas_label = QLabel("Total Placas Repetidas: ", alignment=Qt.AlignCenter,
                                                   styleSheet="background-color: #2a2f38; font-size: 16px;")
        centro_inferior.addWidget(self.total_series_repetidas_label)
        centro_inferior.addWidget(self.total_placas_repetidas_label)

        

        # Derecha: Tabla de Colonias y Probabilidades
        derecha_inferior = QVBoxLayout()
        self.tabla_colonias_label = QLabel("Colonias y Probabilidades:", styleSheet="font-size: 14px; font-weight: bold;")
        self.tabla_colonias = QTableWidget(self)
        self.tabla_colonias.setStyleSheet("background-color: #62aef4; color: black; font-size: 12px;")
        derecha_inferior.addWidget(self.tabla_colonias_label)
        derecha_inferior.addWidget(self.tabla_colonias)
        # Nueva pestaña para Placas Repetidas
        self.placas_repetidas_tab = QWidget()
        self.placas_repetidas_layout = QVBoxLayout()
        self.placas_repetidas_label = QLabel("Placas Repetidas:", styleSheet="font-size: 14px; font-weight: bold;")
        self.tabla_placas_repetidas = QTableWidget(self)
        self.tabla_placas_repetidas.setStyleSheet("background-color: #62aef4; color: black; font-size: 12px;")
        self.placas_repetidas_layout.addWidget(self.placas_repetidas_label)
        self.placas_repetidas_layout.addWidget(self.tabla_placas_repetidas)
        self.placas_repetidas_tab.setLayout(self.placas_repetidas_layout)
        self.tab_widget.addTab(self.placas_repetidas_tab, "Placas Repetidas")  # Agregamos la nueva pestaña
        zona_inferior.addWidget(self.tab_widget)
        zona_inferior.addLayout(centro_inferior)
        zona_inferior.addLayout(derecha_inferior)
        main_layout.addLayout(zona_inferior)
        # Nueva pestaña para Series Repetidas
        self.series_repetidas_tab = QWidget()
        self.series_repetidas_layout = QVBoxLayout()
        self.series_repetidas_label = QLabel("Series Repetidas:", styleSheet="font-size: 14px; font-weight: bold;")
        self.tabla_series_repetidas = QTableWidget(self)
        self.tabla_series_repetidas.setStyleSheet("background-color: #62aef4; color: black; font-size: 12px;")
        self.series_repetidas_layout.addWidget(self.series_repetidas_label)
        self.series_repetidas_layout.addWidget(self.tabla_series_repetidas)
        self.series_repetidas_tab.setLayout(self.series_repetidas_layout)
        self.tab_widget.addTab(self.series_repetidas_tab, "Series Repetidas")
        
        contenedor = QWidget()
        contenedor.setLayout(main_layout)
        self.setCentralWidget(contenedor)
        self.cargar_y_mostrar_datos()

    def actualizar_grafico_principal(self, index):
        if index == 0:
            self.mostrar_grafico_barras_año()
        elif index == 1:
            self.mostrar_grafico_horas()
        elif index == 2:
            self.mostrar_grafico_clasificacion()

    def cargar_datos(self):
        try:
            self.df_original = pd.read_excel("robo de vehiculo23-24.xlsx")
            self.df_original["LATITUD"] = pd.to_numeric(self.df_original["LATITUD"], errors="coerce")
            self.df_original["LONGITUD"] = pd.to_numeric(self.df_original["LONGITUD"], errors="coerce")
            self.df_original['FECHA'] = pd.to_datetime(self.df_original['FECHA'], errors='coerce')
            self.df_original['AÑO'] = self.df_original['FECHA'].dt.year
            self.df_original = self.df_original.dropna(subset=["LATITUD", "LONGITUD", "FECHA", "COLONIA", "HORA REDONDEADA", "CLASIFICACION"])
            # Comprobar que las fechas incluyan los meses deseados
            print(f"Fechas mínimas y máximas en los datos cargados:{self.df_original['FECHA'].min()} - {self.df_original['FECHA'].max()}")
            
            self.df = self.df_original.copy()
            print("Datos cargados correctamente.")
            return True
        except FileNotFoundError:
            print("Error: El archivo 'robo de vehiculo23-24.xlsx' no se encontró.")
            return False
        except Exception as e:
            print(f"Error al cargar los datos: {e}")
            return False
        
    def verificar_meses(self):
         # Extraer los meses y años presentes en el DataFrame
         if self.df is not None and not self.df.empty:
             meses_anios = self.df['FECHA'].dt.to_period('M').unique()
             print("Meses y años disponibles en los datos:", meses_anios)

              # Verificar si los meses deseados están presentes
             meses_deseados = ["2023-04", "2024-04", "2025-01", "2025-02", "2025-03", "2025-04"]
             for mes in meses_deseados:
                 if mes in meses_anios.astype(str):
                     print(f"El mes {mes} está presente en los datos.")
                 else:
                     print(f"Advertencia: El mes {mes} no está presente en los datos.")

    def cargar_y_mostrar_datos(self):
        if self.cargar_datos():
            años_unicos = sorted(self.df_original['FECHA'].dt.year.unique())
            self.año_combo.clear()
            self.año_combo.addItem("Todos")
            self.año_combo.addItems([str(año) for año in años_unicos])
            self.año_combo.setCurrentIndex(0)
            colonias_unicas = sorted(self.df_original['COLONIA'].unique())
            self.colonia_combo.clear()
            self.colonia_combo.addItem("Todas")
            self.colonia_combo.addItems(colonias_unicas)
            self.colonia_combo.setCurrentIndex(0)
            clasificaciones_unicas = sorted(self.df_original['CLASIFICACION'].unique())
            self.clasificacion_combo.clear()
            self.clasificacion_combo.addItem("Todas")
            self.clasificacion_combo.addItems(clasificaciones_unicas)
            self.clasificacion_combo.setCurrentIndex(0)
            self.año_combo.currentIndexChanged.connect(self.aplicar_filtros)
            self.mes_combo.currentIndexChanged.connect(self.aplicar_filtros)
            self.colonia_combo.currentIndexChanged.connect(self.aplicar_filtros)
            self.clasificacion_combo.currentIndexChanged.connect(self.aplicar_filtros)
            self.mapa_selector.clear()
            self.mapa_selector.addItems(["Puntos Rojos", "Mapa de Calor", "Riesgo por Colonia", "Clusters de Robos","Placas Repetidas","Series Repetidas"])
            self.actualizar_mapa(self.mapa_selector.currentIndex())
            self.actualizar_grafico_principal(self.grafico_principal_selector.currentIndex())
            self.actualizar_totales()

            # Mostrar Placas Repetidas
            self.mostrar_placas_repetidas()
             # Mostrar Series Repetidas
            self.mostrar_series_repetidas()
            
            # Generar DataFrames de placas y series repetidas
        self.placas_repetidas_df = self.encontrar_placas_repetidas()
        self.series_repetidas_df = self.encontrar_series_repetidas()

        self.verificar_meses()
        self.cargar_y_mostrar_datos()


       

        # Actualizar los totales
        self.actualizar_totales()



    def encontrar_placas_repetidas(self):
        if self.df is None or self.df.empty:
            print("No hay datos cargados para encontrar placas repetidas.")
            return pd.DataFrame()

        # Verificar que las columnas necesarias existan
        columnas_requeridas = ['PLACA', 'INCIDENTE', 'COLONIA', 'CLASIFICACION', 'LATITUD', 'LONGITUD', 'FECHA']
        for columna in columnas_requeridas:
            if columna not in self.df.columns:
                print(f"Error: Falta la columna '{columna}' en el DataFrame.")
                return pd.DataFrame()



        placas_repetidas = self.df['PLACA'].value_counts()

        # Crear un DataFrame con las placas repetidas
        placas_repetidas_df = pd.DataFrame({
            'PLACA': placas_repetidas.index,
            'Frecuencia': placas_repetidas.values
         })
        
        # Filtrar placas con frecuencia mayor a 1
        if not placas_repetidas_df.empty:
            placas_repetidas_df = placas_repetidas_df[placas_repetidas_df['Frecuencia'] > 1]

        else:
             print("No se encontraron placas repetidas.")
             return pd.DataFrame()

             

        
        

        # Filtrar para excluir las placas que son exactamente "SD"
        placas_repetidas_df = placas_repetidas_df[placas_repetidas_df['PLACA'] != 'SD']
        
        # Funciones auxiliares para obtener las colonias de robo y recuperación
        def obtener_colonia_y_fecha(grupo, tipo):
            for _, fila in grupo.iterrows():
                if tipo.lower() in fila['INCIDENTE'].lower():
                    return fila['COLONIA'], fila['FECHA']
            return None, None
        
        def obtener_ubicacion(grupo, tipo):
            for _, fila in grupo.iterrows():
                if tipo.lower() in fila['INCIDENTE'].lower():
                    return fila['LATITUD'], fila['LONGITUD']
            return None, None
        



        # Agregar columnas al DataFrame
        datos_robo = placas_repetidas_df['PLACA'].apply(
            lambda placa: obtener_colonia_y_fecha(self.df[self.df['PLACA'] == placa], 'robo')
         )
        datos_recuperacion = placas_repetidas_df['PLACA'].apply(
            lambda placa: obtener_colonia_y_fecha(self.df[self.df['PLACA'] == placa], 'recuperación')
        )

        placas_repetidas_df['Colonia_Robo'] = datos_robo.apply(lambda x: x[0])
        placas_repetidas_df['Fecha_Robo'] = datos_robo.apply(lambda x: x[1])
        placas_repetidas_df['Colonia_Recuperacion'] = datos_recuperacion.apply(lambda x: x[0])
        placas_repetidas_df['Fecha_Recuperacion'] = datos_recuperacion.apply(lambda x: x[1])

        ubicaciones_robo = placas_repetidas_df['PLACA'].apply(
            lambda placa: obtener_ubicacion(self.df[self.df['PLACA'] == placa], 'robo')
        )
        ubicaciones_recuperacion = placas_repetidas_df['PLACA'].apply(
            lambda placa: obtener_ubicacion(self.df[self.df['PLACA'] == placa], 'recuperación')
        )

        placas_repetidas_df['LATITUD'] = ubicaciones_robo.apply(lambda x: x[0])
        placas_repetidas_df['LONGITUD'] = ubicaciones_robo.apply(lambda x: x[1])
        placas_repetidas_df['LATITUD_Recuperacion'] = ubicaciones_recuperacion.apply(lambda x: x[0])
        placas_repetidas_df['LONGITUD_Recuperacion'] = ubicaciones_recuperacion.apply(lambda x: x[1])

        # Validar que las colonias de robo y recuperación no sean iguales
        def validar_colonias(robo, recuperacion):
            if robo == recuperacion:
                return "Error: Colonias Iguales"
            return "Correcto"
        placas_repetidas_df['Validacion_Colonias'] = placas_repetidas_df.apply(
            lambda row: validar_colonias(row['Colonia_Robo'], row['Colonia_Recuperacion']),
            axis=1
        )








        
    

        # Combinar con los datos originales para obtener INCIDENTE, CLASIFICACION y COLONIA
        placas_repetidas_df = pd.merge(
            placas_repetidas_df,
            self.df[['PLACA', 'INCIDENTE', 'CLASIFICACION']].drop_duplicates(subset=['PLACA']),
            on='PLACA',
            how='left'
        )
        return placas_repetidas_df

    def mostrar_placas_repetidas(self):
        placas_repetidas_df = self.encontrar_placas_repetidas()
        self.tabla_placas_repetidas.clear()
        self.tabla_placas_repetidas.setRowCount(0)
        self.tabla_placas_repetidas.setColumnCount(0)
       


        if not placas_repetidas_df.empty:
            self.tabla_placas_repetidas.setColumnCount(len(placas_repetidas_df.columns))
            self.tabla_placas_repetidas.setHorizontalHeaderLabels(placas_repetidas_df.columns)
            for i, row in placas_repetidas_df.iterrows():
                self.tabla_placas_repetidas.insertRow(i)
                for j, col in enumerate(placas_repetidas_df.columns):
                    # Formatear fechas para que sean más legibles (opcional)
                    if col in ['Fecha_Robo', 'Fecha_Recuperacion'] and pd.notnull(row[col]):
                        fecha_formateada = pd.to_datetime(row[col]).strftime('%d-%m-%Y')
                        self.tabla_placas_repetidas.setItem(i, j, QTableWidgetItem(fecha_formateada))
                    else:
                        self.tabla_placas_repetidas.setItem(i, j, QTableWidgetItem(str(row[col])))
            self.tabla_placas_repetidas.resizeColumnsToContents()
        else:
            self.tabla_placas_repetidas.setRowCount(1)
            self.tabla_placas_repetidas.setColumnCount(1)
            item = QTableWidgetItem("No se encontraron placas repetidas")
            self.tabla_placas_repetidas.setItem(0, 0, item)
            self.tabla_placas_repetidas.resizeColumnsToContents()
        

    def encontrar_series_repetidas(self):
        if self.df is None or self.df.empty:
            print("No hay datos cargados para encontrar series repetidas.")
            return pd.DataFrame()

        # Verificar que las columnas necesarias existan
        columnas_requeridas = ['SERIE', 'INCIDENTE', 'COLONIA', 'CLASIFICACION', 'LATITUD', 'LONGITUD', 'FECHA']
        for columna in columnas_requeridas:
            if columna not in self.df.columns:
                print(f"Error: Falta la columna '{columna}' en el DataFrame.")
                return pd.DataFrame()
        
        # Calcular la frecuencia de cada serie
        series_repetidas = self.df['SERIE'].value_counts()

        # Crear un DataFrame con las series repetidas
        series_repetidas_df = pd.DataFrame({
            'SERIE': series_repetidas.index,
            'Frecuencia': series_repetidas.values
        })
        
        # Filtrar series con frecuencia mayor a 1
        if not series_repetidas_df.empty:
            series_repetidas_df = series_repetidas_df[series_repetidas_df['Frecuencia'] > 1]
        else:
            print("No se encontraron series repetidas.")
            return pd.DataFrame()


        # Filtrar para excluir las series que son "SD", "S/D" o "PENDIENTE"
        valores_a_excluir = ['SD', 'S/D', 'PENDIENTE']
        series_repetidas_df = series_repetidas_df[~series_repetidas_df['SERIE'].isin(valores_a_excluir)]

        # Función auxiliar para obtener información de robo y recuperación
        def obtener_colonia_y_fecha(grupo, tipo):
            for _, fila in grupo.iterrows():
                if tipo.lower() in fila['INCIDENTE'].lower():
                     return fila['COLONIA'], fila['LATITUD'], fila['LONGITUD'], fila['FECHA']
            return "No encontrada", None, None, None
        # Agregar columnas de Colonia_Robo, Fecha_Robo, Colonia_Recuperacion, Fecha_Recuperacion
        datos_robo = series_repetidas_df['SERIE'].apply(
            lambda serie: obtener_colonia_y_fecha(self.df[self.df['SERIE'] == serie], 'robo')
        )
        datos_recuperacion = series_repetidas_df['SERIE'].apply(
            lambda serie: obtener_colonia_y_fecha(self.df[self.df['SERIE'] == serie], 'recuperación')
        )

        series_repetidas_df['Colonia_Robo'] = datos_robo.apply(lambda x: x[0])
        series_repetidas_df['LATITUD'] = datos_robo.apply(lambda x: x[1])
        series_repetidas_df['LONGITUD'] = datos_robo.apply(lambda x: x[2])
        series_repetidas_df['Fecha_Robo'] = datos_robo.apply(lambda x: x[3])

        series_repetidas_df['Colonia_Recuperacion'] = datos_recuperacion.apply(lambda x: x[0])
        series_repetidas_df['LATITUD_Recuperacion'] = datos_recuperacion.apply(lambda x: x[1])
        series_repetidas_df['LONGITUD_Recuperacion'] = datos_recuperacion.apply(lambda x: x[2])
        series_repetidas_df['Fecha_Recuperacion'] = datos_recuperacion.apply(lambda x: x[3])
        
            
        
        
        
        
        




        # Combinar con los datos originales para obtener INCIDENTE, CLASIFICACION y COLONIA
        series_repetidas_df = pd.merge(
            series_repetidas_df,
            self.df[['SERIE', 'INCIDENTE', 'CLASIFICACION']].drop_duplicates(subset=['SERIE']),
            on='SERIE',
            how='left'
        )

        return series_repetidas_df
    
    def mostrar_series_repetidas(self):
        series_repetidas_df = self.encontrar_series_repetidas()
        self.tabla_series_repetidas.clear()
        self.tabla_series_repetidas.setRowCount(0)
        self.tabla_series_repetidas.setColumnCount(0)

        if not series_repetidas_df.empty:
            self.tabla_series_repetidas.setColumnCount(len(series_repetidas_df.columns))
            self.tabla_series_repetidas.setHorizontalHeaderLabels(series_repetidas_df.columns)
            for i, row in series_repetidas_df.iterrows():
                self.tabla_series_repetidas.insertRow(i)
                for j, col in enumerate(series_repetidas_df.columns):
                    # Formatear fechas si son columnas de fechas
                    if col in ['Fecha_Robo', 'Fecha_Recuperacion'] and pd.notnull(row[col]):
                        fecha_formateada = pd.to_datetime(row[col]).strftime('%d-%m-%Y')
                        self.tabla_series_repetidas.setItem(i, j, QTableWidgetItem(fecha_formateada))
                    else:
                        self.tabla_series_repetidas.setItem(i, j, QTableWidgetItem(str(row[col])))
            self.tabla_series_repetidas.resizeColumnsToContents()
        else:
            self.tabla_series_repetidas.setRowCount(1)
            self.tabla_series_repetidas.setColumnCount(1)
            item = QTableWidgetItem("No se encontraron series repetidas")
            self.tabla_series_repetidas.setItem(0, 0, item)
            self.tabla_series_repetidas.resizeColumnsToContents()

    def aplicar_filtros(self):
        if self.df_original is None:
            return
        año_seleccionado = self.año_combo.currentText()
        mes_seleccionado = self.mes_combo.currentText()
        colonia_seleccionada = self.colonia_combo.currentText()
        clasificacion_seleccionada = self.clasificacion_combo.currentText()
        # Crear una copia del DataFrame original
        self.df = self.df_original.copy()
        # Validar el valor del año seleccionado
        if año_seleccionado != "Todos" and año_seleccionado.isdigit():
            self.df = self.df[self.df['FECHA'].dt.year == int(año_seleccionado)]

        # Validar el valor del mes seleccionado
        if mes_seleccionado != "Todos":
            meses_a_numero = {
                "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
                "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
                "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
            }
            mes_numero = meses_a_numero.get(mes_seleccionado)
            if mes_numero:
                self.df = self.df[self.df['FECHA'].dt.month == mes_numero]
        if colonia_seleccionada != "Todas":
            self.df = self.df[self.df['COLONIA'] == colonia_seleccionada]
        if clasificacion_seleccionada != "Todas":
            self.df = self.df[self.df['CLASIFICACION'] == clasificacion_seleccionada]
        self.actualizar_mapa(self.mapa_selector.currentIndex())
        self.actualizar_grafico_principal(self.grafico_principal_selector.currentIndex())
        self.actualizar_totales()

    def mostrar_mapa_puntos(self):
        if self.df is not None and not self.df.empty:
            try:
                # Centrar el mapa en Morelia
                mapa = folium.Map(location=[19.7008, -101.1838], zoom_start=13)  # Coordenadas aproximadas de Morelia
                for _, fila in self.df.iterrows():
                    folium.CircleMarker(location=[fila["LATITUD"], fila["LONGITUD"]], radius=5, color='red', fill=True, fill_color='red').add_to(mapa)
                mapa.save("mapa_puntos.html")
                self.mapa_view.setUrl(QUrl.fromLocalFile(os.path.abspath("mapa_puntos.html")))
            except Exception as e:
                print(f"Error al mostrar el mapa de puntos: {e}")

    def mostrar_mapa_calor(self):
        if self.df is not None and not self.df.empty:
            try:
                # Centrar el mapa en Morelia
                mapa_calor = folium.Map(location=[19.7008, -101.1838], zoom_start=13)
                heat_data = [[row['LATITUD'], row['LONGITUD']] for index, row in self.df.iterrows()]
                HeatMap(heat_data).add_to(mapa_calor)
                mapa_calor.save("mapa_calor.html")
                self.mapa_view.setUrl(QUrl.fromLocalFile(os.path.abspath("mapa_calor.html")))
            except ImportError:
                print("Error: La librería 'folium.plugins' no está disponible.")
            except Exception as e:
                print(f"Error al mostrar el mapa de calor: {e}")

    def mostrar_mapa_riesgo_colonias(self):
        if self.df is not None and not self.df.empty and self.modelo_riesgo is not None and not self.modelo_riesgo.empty:
            try:
                # Centrar el mapa en Morelia
                mapa_riesgo = folium.Map(location=[19.7008, -101.1838], zoom_start=13)
                riesgo_por_colonia = self.modelo_riesgo.set_index('COLONIA')['nivel_riesgo'].to_dict()
                color_map = {'Alto': 'red', 'Medio': 'yellow', 'Bajo': 'green'}
                for _, fila in self.df.iterrows():
                    colonia = fila.get('COLONIA')
                    nivel_riesgo = riesgo_por_colonia.get(colonia, 'Bajo')
                    color = color_map.get(nivel_riesgo, 'gray')
                    if colonia is not None and fila["LATITUD"] is not None and fila["LONGITUD"] is not None:
                        folium.CircleMarker(location=[fila["LATITUD"], fila["LONGITUD"]],
                                          radius=5, color=color, fill=True, fill_color=color).add_to(mapa_riesgo)
                mapa_riesgo.save("mapa_riesgo_colonias.html")
                self.mapa_view.setUrl(QUrl.fromLocalFile(os.path.abspath("mapa_riesgo_colonias.html")))
            except Exception as e:
                print(f"Error al mostrar el mapa de riesgo por colonias: {e}")

    def mostrar_mapa_clusters(self):
        if self.df is not None and not self.df.empty:
            try:
                # Centrar el mapa en Morelia
                mapa_clusters = folium.Map(location=[19.7008, -101.1838], zoom_start=13)
                coords = self.df[['LATITUD', 'LONGITUD']].values
                dbscan = DBSCAN(eps=0.005, min_samples=10).fit(coords)
                labels = dbscan.labels_
                n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
                unique_labels = set(labels)
                cmap = plt.get_cmap('tab20b')
                cluster_colors = [cmap(i) if i >= 0 else (0.5, 0.5, 0.5, 1) for i in range(max(labels) + 1)]
                for i, label in enumerate(unique_labels):
                    if label == -1:
                        continue
                    class_member_mask = (labels == label)
                    xy = coords[class_member_mask]
                    color = matplotlib.colors.to_hex(cluster_colors[label])
                    for j in range(len(xy)):
                        folium.CircleMarker(location=[xy[j, 0], xy[j, 1]], radius=5, color=color, fill=True, fill_color=color).add_to(mapa_clusters)
                mapa_clusters.save("mapa_clusters.html")
                self.mapa_view.setUrl(QUrl.fromLocalFile(os.path.abspath("mapa_clusters.html")))
            except Exception as e:
                print(f"Error al mostrar el mapa de clusters: {e}")

    def mostrar_mapa_placas_repetidas(self):
        if self.placas_repetidas_df is not None and not self.placas_repetidas_df.empty:
            try:
                # Centrar el mapa en Morelia
                mapa_placas = folium.Map(location=[19.7008, -101.1838], zoom_start=13)

                # Agregar puntos de placas repetidas
                for _, fila in self.placas_repetidas_df.iterrows():
                    # Validar que las coordenadas no sean nulas
                    if pd.notnull(fila["LATITUD"]) and pd.notnull(fila["LONGITUD"]):
                    # Puntos de robo
                     if fila['Colonia_Robo'] != "No encontrada":
                         folium.CircleMarker(
                             location=[fila["LATITUD"], fila["LONGITUD"]],
                              radius=5,
                              color='red',
                              fill=True,
                              fill_color='red',
                              tooltip=f"Placa: {fila['PLACA']} - Robo en {fila['Colonia_Robo']}"
                        ).add_to(mapa_placas)
                    

                    # Puntos de recuperación
                    if fila['Colonia_Recuperacion'] != "No encontrada" and pd.notnull(fila["LATITUD_Recuperacion"]) and pd.notnull(fila["LONGITUD_Recuperacion"]):
                        folium.CircleMarker(
                            location=[fila["LATITUD_Recuperacion"], fila["LONGITUD_Recuperacion"]],
                            radius=5,
                            color='blue',
                            fill=True,
                            fill_color='blue',
                            tooltip=f"Placa: {fila['PLACA']} - Recuperación en {fila['Colonia_Recuperacion']}"
                        ).add_to(mapa_placas)

                    # Agregar una leyenda al mapa
                    leyenda_html = '''
                    <div style="
                         position: fixed; 
                         bottom: 50px; left: 50px;
                         width: 200px; height: 100px;
                         background-color: white;
                         border:2px solid grey; z-index:9999; font-size:14px;
                          padding: 10px;
                          ">
                          <b>Leyenda:</b><br>
                          <i style="color:red;">●</i> Robados<br>
                          <i style="color:blue;">●</i> Recuperados
                    </div>
                    '''
                    folium.Marker([0, 0], icon=folium.DivIcon(html=leyenda_html)).add_to(mapa_placas)


                    
                # Guardar el mapa y mostrarlo
                mapa_placas.save("mapa_placas_repetidas.html")
                self.mapa_view.setUrl(QUrl.fromLocalFile(os.path.abspath("mapa_placas_repetidas.html")))
            except Exception as e:
                 print(f"Error al mostrar el mapa de placas repetidas: {e}")

    def mostrar_mapa_series_repetidas(self):
         if self.series_repetidas_df is not None and not self.series_repetidas_df.empty:
             try:
                 # Centrar el mapa en Morelia
                 mapa_series = folium.Map(location=[19.7008, -101.1838], zoom_start=13)

                 # Agregar puntos de series repetidas
                 for _, fila in self.series_repetidas_df.iterrows():
                      # Validar que las coordenadas no sean nulas
                     if pd.notnull(fila["LATITUD"]) and pd.notnull(fila["LONGITUD"]):
                          # Puntos de robo
                          if fila['Colonia_Robo'] != "No encontrada":
                              folium.CircleMarker(
                                  location=[fila["LATITUD"], fila["LONGITUD"]],
                                  radius=5,
                                  color='red',
                                  fill=True,
                                  fill_color='red',
                                  tooltip=f"Serie: {fila['SERIE']} - Robo en {fila['Colonia_Robo']} - Fecha: {fila['Fecha_Robo']}"
                                ).add_to(mapa_series)
                          
                              
                    # Validar que las coordenadas de recuperación no sean nulas
                     if pd.notnull(fila["LATITUD_Recuperacion"]) and pd.notnull(fila["LONGITUD_Recuperacion"]):
                         # Puntos de recuperación
                         if fila['Colonia_Recuperacion'] != "No encontrada":
                             folium.CircleMarker(
                                 location=[fila["LATITUD_Recuperacion"], fila["LONGITUD_Recuperacion"]],
                                 radius=5,
                                 color='blue',
                                 fill=True,
                                 fill_color='blue',
                                 tooltip=f"Serie: {fila['SERIE']} - Recuperación en {fila['Colonia_Recuperacion']} - Fecha: {fila['Fecha_Recuperacion']}"
                            ).add_to(mapa_series)
                         
                              
                          
                        
                 # Agregar una leyenda al mapa
                 leyenda_html = '''
                 <div style="
                      position: fixed;
                      bottom: 50px; left: 50px;
                      width: 200px; height: 100px;
                      background-color: white;
                      border:2px solid grey; z-index:9999; font-size:14px;
                      padding: 10px;
                      ">
                      <b>Leyenda:</b><br>
                      <i style="color:red;">●</i> Robados<br>
                      <i style="color:blue;">●</i> Recuperados
                  </div>
                  '''
                 folium.Marker([0, 0], icon=folium.DivIcon(html=leyenda_html)).add_to(mapa_series) 
                    


                         
                 if fila['Colonia_Recuperacion'] != "No encontrada" and fila["LATITUD"] is not None and fila["LONGITUD"] is not None:
                     folium.CircleMarker(
                         location=[fila["LATITUD"], fila["LONGITUD"]],
                         radius=5,
                         color='blue',
                         fill=True,
                         fill_color='blue',
                         tooltip=f"Serie: {fila['SERIE']} - Recuperación en {fila['Colonia_Recuperacion']}"
                    ).add_to(mapa_series)
                     
                # Guardar el mapa y mostrarlo
                 mapa_series.save("mapa_series_repetidas.html")
                 self.mapa_view.setUrl(QUrl.fromLocalFile(os.path.abspath("mapa_series_repetidas.html")))
             except Exception as e:
                 print(f"Error al mostrar el mapa de series repetidas: {e}")
             
    
                 
        
    


                




    def actualizar_mapa(self, index):
        if index == 0:
            self.mostrar_mapa_puntos()
        elif index == 1:
            self.mostrar_mapa_calor()
        elif index == 2:
            self.mostrar_mapa_riesgo_colonias()
        elif index == 3:
            self.mostrar_mapa_clusters()
        elif index == 4:  # Placas Repetidas
            self.mostrar_mapa_placas_repetidas()
        elif index == 5:  # Series Repetidas
             self.mostrar_mapa_series_repetidas()

    def mostrar_grafico_barras_año(self):
        if self.df is not None and not self.df.empty:
            try:
                robos_por_año = self.df['FECHA'].dt.year.value_counts().sort_index()
                plt.figure(figsize=(10, 5))
                robos_por_año.plot(kind='bar', color='#61a5c2')
                plt.title('Total de Robos por Año', color='white')
                plt.xlabel('Año', color='white')
                plt.ylabel('Número de Robos', color='white')
                plt.xticks(rotation=45, color='white')
                plt.yticks(color='white')
                plt.gca().spines['bottom'].set_color('white')
                plt.gca().spines['left'].set_color('white')
                plt.gca().xaxis.label.set_color('white')
                plt.gca().yaxis.label.set_color('white')
                plt.gcf().set_facecolor('#2a2f38')
                plt.gca().set_facecolor('#2a2f38')
                buf = BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                im = Image.open(buf)
                qimage = QImage(im.tobytes("raw", "RGB"), im.size[0], im.size[1], QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
                self.grafico_principal_view.setPixmap(pixmap)
                plt.close()
            except Exception as e:
                print(f"Error al mostrar el gráfico de barras por año: {e}")

    def mostrar_grafico_horas(self):
        if self.df is not None and not self.df.empty:
            try:
                robos_por_hora = self.df['HORA REDONDEADA'].value_counts().sort_index()
                horas = robos_por_hora.index.tolist()
                horas_etiquetas = [h.hour for h in horas]
                plt.figure(figsize=(10, 5))
                robos_por_hora.plot(kind='bar', color='#61a5c2')
                plt.title('Robos por Hora', color='white')
                plt.xlabel('Hora', color='white')
                plt.ylabel('Número de Robos', color='white')
                plt.xticks(range(len(horas)), horas_etiquetas, rotation=0, color='white')
                plt.yticks(color='white')
                plt.gca().spines['bottom'].set_color('white')
                plt.gca().spines['left'].set_color('white')
                plt.gca().xaxis.label.set_color('white')
                plt.gca().yaxis.label.set_color('white')
                plt.gcf().set_facecolor('#2a2f38')
                plt.gca().set_facecolor('#2a2f38')
                buf = BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                im = Image.open(buf)
                qimage = QImage(im.tobytes("raw", "RGB"), im.size[0], im.size[1], QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
                self.grafico_principal_view.setPixmap(pixmap)
                plt.close()
            except Exception as e:
                print(f"Error al mostrar el gráfico de robos por hora: {e}")

    def mostrar_grafico_clasificacion(self):
        if self.df is not None and not self.df.empty:
            try:
                robos_por_clasificacion = self.df['CLASIFICACION'].value_counts()
                plt.figure(figsize=(10, 5))
                robos_por_clasificacion.plot(kind='bar', color='#61a5c2')
                plt.title('Robos por Clasificación', color='white')
                plt.xlabel('Clasificación', color='white')
                plt.ylabel('Número de Robos', color='white')
                plt.xticks(rotation=45, ha='right', color='white')
                plt.yticks(color='white')
                plt.gca().spines['bottom'].set_color('white')
                plt.gca().spines['left'].set_color('white')
                plt.gca().xaxis.label.set_color('white')
                plt.gca().yaxis.label.set_color('white')
                plt.gcf().set_facecolor('#2a2f38')
                plt.gca().set_facecolor('#2a2f38')
                buf = BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                im = Image.open(buf)
                qimage = QImage(im.tobytes("raw", "RGB"), im.size[0], im.size[1], QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
                self.grafico_principal_view.setPixmap(pixmap)
                plt.close()
            except Exception as e:
                print(f"Error al mostrar el gráfico de robos por clasificación: {e}")
                

    def actualizar_totales(self):
        if self.df is not None and not self.df.empty:
            total_robos = len(self.df)
            colonia_mas_frecuente = self.df['COLONIA'].mode()[0] if not self.df['COLONIA'].empty else "N/A"
            hora = datetime.now().time()
            fecha = datetime.now().date()
            clasificacion = self.df['CLASIFICACION'].mode()[0] if not self.df['CLASIFICACION'].empty else "N/A"
            probabilidad = self.calcular_probabilidad_robo(colonia_mas_frecuente, hora, fecha, clasificacion)
             # Totales de series repetidas y placas repetidas
            total_series_repetidas = len(self.series_repetidas_df) if self.series_repetidas_df is not None else 0
            total_placas_repetidas = len(self.placas_repetidas_df) if self.placas_repetidas_df is not None else 0
            self.total_robos_label.setText(f"Total Robos: {total_robos}")
            self.probabilidad_label.setText(f"Probabilidad de Robo: {probabilidad:.2f}%")
            self.total_series_repetidas_label.setText(f"Total Series Repetidas: {total_series_repetidas}")
            self.total_placas_repetidas_label.setText(f"Total Placas Repetidas: {total_placas_repetidas}")
            self.actualizar_tabla_colonias()  # Actualizar la tabla de colonias
            

        else:
            self.total_robos_label.setText("Total Robos: N/A")
            self.probabilidad_label.setText("Probabilidad de Robo: N/A")
            self.total_series_repetidas_label.setText("Total Series Repetidas: N/A")
            self.total_placas_repetidas_label.setText("Total Placas Repetidas: N/A")
            self.tabla_colonias.clear()
            self.tabla_colonias.setRowCount(0)
            self.tabla_colonias.setColumnCount(0)
        # Debugging: Imprimir los DataFrames para verificar su contenido
        print("Contenido de series_repetidas_df:")
        print(self.series_repetidas_df)
        print("Contenido de placas_repetidas_df:")
        print(self.placas_repetidas_df)

    def calcular_probabilidad_robo(self, colonia, hora, fecha, clasificacion):
        if self.df is None or self.df.empty:
            return 0.0
        puntaje_base = 0.1
        puntaje_colonia = self.calcular_riesgo_colonia(colonia)
        hora_riesgo = self.calcular_riesgo_hora(hora)
        dia_semana_riesgo = self.calcular_riesgo_dia_semana(fecha.weekday())
        clasificacion_riesgo = self.calcular_riesgo_clasificacion(clasificacion)
        probabilidad = puntaje_base + 0.3 * puntaje_colonia + 0.2 * hora_riesgo + 0.2 * dia_semana_riesgo + 0.3 * clasificacion_riesgo
        return max(0, min(probabilidad, 1)) * 100

    def calcular_riesgo_colonia(self, colonia):
        if self.df is None or self.df.empty:
            return 0.5
        robos_colonia = self.df['COLONIA'].value_counts()
        total_colonias = len(self.df['COLONIA'].unique())
        if colonia in robos_colonia:
            return robos_colonia[colonia] / robos_colonia.sum()
        else:
            return 1 / total_colonias

    def calcular_riesgo_hora(self, hora):
        if isinstance(hora, time):
            hora_int = hora.hour
        else:
            try:
                hora_int = int(hora)
            except ValueError:
                return 0.5
        if 18 <= hora_int <= 22:
            return 0.8
        elif 6 <= hora_int <= 9 or 12 <= hora_int <= 14:
            return 0.6
        else:
            return 0.3

    def calcular_riesgo_dia_semana(self, dia_semana):
        if 4 <= dia_semana <= 6:
            return 0.7
        else:
            return 0.5

    def calcular_riesgo_clasificacion(self, clasificacion):
        clasificaciones_riesgo = {
            'AUTOMOVIL': 0.7,
            'MOTOCICLETA': 0.8,
            'CAMIONETA': 0.6,
            'TAXI': 0.5,
            'TRANSPORTE PUBLICO': 0.4
        }
        return clasificaciones_riesgo.get(clasificacion, 0.5)

    def generar_caracteristicas_riesgo(self):
        if self.df is None or self.df.empty:
            self.anomalias_text.setText("No hay datos cargados para generar características de riesgo.")
            return pd.DataFrame()
        df = self.df.copy()
        df['FECHA'] = pd.to_datetime(df['FECHA'], errors='coerce')
        df = df.dropna(subset=['FECHA', 'COLONIA', 'HORA REDONDEADA', 'CLASIFICACION'])
        fecha_maxima = df['FECHA'].max()
        fecha_limite_6_meses = fecha_maxima - timedelta(days=6 * 30)
        fecha_limite_periodo_anterior = fecha_maxima - timedelta(days=365) # Aproximación de un año

        # Imprimir el rango de fechas del DataFrame original para referencia
        if self.df_original is not None and not self.df_original.empty:
            print(f"Fecha mínima original: {self.df_original['FECHA'].min()}")
            print(f"Fecha máxima original: {self.df_original['FECHA'].max()}")

        caracteristicas_por_colonia = df.groupby('COLONIA').agg(
            total_robos=('FECHA', 'count'),
            robos_ultimos_6_meses=('FECHA', lambda x: sum(x >= fecha_limite_6_meses)),
            robos_periodo_anterior=('FECHA', lambda x: sum((x >= fecha_limite_periodo_anterior) & (x < (fecha_limite_periodo_anterior + timedelta(days=90))))), # Robos aprox. 3 meses anteriores
            horas_robos=('HORA REDONDEADA', lambda x: list(x)),
            dias_semana_robos=('FECHA', lambda x: list(x.dt.day_name())),
            tipos_vehiculos=('CLASIFICACION', lambda x: list(x))
        ).reset_index()

        caracteristicas_por_colonia['hora_pico_robo'] = caracteristicas_por_colonia['horas_robos'].apply(
            lambda x: Counter([h.hour if isinstance(h, time) else -1 for h in x]).most_common(1)[0][0] if x else -1)
        caracteristicas_por_colonia['dia_pico_robo'] = caracteristicas_por_colonia['dias_semana_robos'].apply(
            lambda x: Counter(x).most_common(1)[0][0] if x else 'N/A')
        caracteristicas_por_colonia['tipo_vehiculo_mas_robado'] = caracteristicas_por_colonia['tipos_vehiculos'].apply(
            lambda x: Counter(x).most_common(1)[0][0] if x else 'N/A')
        umbral_alto = caracteristicas_por_colonia['total_robos'].quantile(0.75)
        umbral_bajo = caracteristicas_por_colonia['total_robos'].quantile(0.25)

        def asignar_riesgo(total):
            if total >= umbral_alto:
                return 'Alto'
            elif total > umbral_bajo:
                return 'Medio'
            else:
                return 'Bajo'

        caracteristicas_por_colonia['nivel_riesgo'] = caracteristicas_por_colonia[
            'total_robos'].apply(
            asignar_riesgo)
        caracteristicas_por_colonia['desviacion_robos'] = caracteristicas_por_colonia['total_robos'] - caracteristicas_por_colonia['robos_periodo_anterior']

        # Imprimir los valores de total_robos y robos_periodo_anterior para algunas colonias
        print("\nValores de Total Robos y Robos del Periodo Anterior (aprox. 3 meses antes):")
        for index, row in caracteristicas_por_colonia.head().iterrows():  # Imprimir para las primeras 5 colonias
            colonia = row['COLONIA']
            total_robos = row['total_robos']
            robos_periodo_anterior = row['robos_periodo_anterior']
            desviacion = row['desviacion_robos']
            print(f"Colonia: {colonia}, Total Robos: {total_robos}, Robos Periodo Anterior: {robos_periodo_anterior}, Desviación: {desviacion}")

        caracteristicas_por_colonia = caracteristicas_por_colonia.drop(
            columns=['horas_robos', 'dias_semana_robos', 'tipos_vehiculos'])
        return caracteristicas_por_colonia

    def ejecutar_modelo_ia(self):
        caracteristicas_riesgo = self.generar_caracteristicas_riesgo()
        if not caracteristicas_riesgo.empty:
            # Ordenar por total de robos (de mayor a menor)
            caracteristicas_riesgo_ordenado = caracteristicas_riesgo.sort_values(
                by='total_robos', ascending=False)

            print("Shape de caracteristicas_riesgo_ordenado:", caracteristicas_riesgo_ordenado.shape)
            print("Columnas de caracteristicas_riesgo_ordenado:", caracteristicas_riesgo_ordenado.columns.tolist())

            # Mostrar la tabla de características de riesgo en la parte derecha inferior
            self.tabla_colonias.setRowCount(caracteristicas_riesgo_ordenado.shape[0])
            self.tabla_colonias.setColumnCount(caracteristicas_riesgo_ordenado.shape[1])
            self.tabla_colonias.setHorizontalHeaderLabels(caracteristicas_riesgo_ordenado.columns)

            for i, index in enumerate(caracteristicas_riesgo_ordenado.index):
                row_data = caracteristicas_riesgo_ordenado.loc[index].to_list()
                print(f"Fila {i}: {row_data}")
                for j, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value))
                    self.tabla_colonias.setItem(i, j, item)

            self.tabla_colonias.resizeColumnsToContents()
            self.modelo_riesgo = caracteristicas_riesgo  # Guardar para usar en el mapa de riesgo

            # Llamar a la función para detectar anomalías
            self.detectar_anomalias()
        else:
            self.anomalias_text.setHtml("<p>No hay datos suficientes para generar el modelo de IA.</p>")

    def actualizar_tabla_colonias(self):
        if self.modelo_riesgo is not None and not self.modelo_riesgo.empty:
            self.tabla_colonias.setRowCount(0)
            self.tabla_colonias.setColumnCount(0)
            self.tabla_colonias.setColumnCount(2)  # Dos columnas: Colonia y Probabilidad
            self.tabla_colonias.setHorizontalHeaderLabels(['Colonia', 'Nivel de Riesgo'])
            for index, row in self.modelo_riesgo.iterrows():
                self.tabla_colonias.insertRow(index)
                self.tabla_colonias.setItem(index, 0, QTableWidgetItem(row['COLONIA']))
                self.tabla_colonias.setItem(index, 1, QTableWidgetItem(str(row['nivel_riesgo'])))
            self.tabla_colonias.resizeColumnsToContents()
        else:
            self.tabla_colonias.clear()
            self.tabla_colonias.setRowCount(0)
            self.tabla_colonias.setColumnCount(0)

    def guardar_informe_pdf(self):
      nombre_archivo, _ = QFileDialog.getSaveFileName(self, "Guardar Informe PDF", "", "Archivos PDF (*.pdf)")
      if nombre_archivo:
        doc = SimpleDocTemplate(nombre_archivo, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Título del informe
        titulo = Paragraph("Informe de Análisis de Robos de Vehículos", styles['h1'])
        story.append(titulo)
        story.append(Spacer(1, 0.2*inch))

        # Fecha de generación
        fecha_generacion = Paragraph(f"Fecha de Generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal'])
        story.append(fecha_generacion)
        story.append(Spacer(1, 0.2*inch))

        # Obtener las fechas de inicio y fin del filtro aplicado
        fecha_inicio_str = "Inicio"  # Valores por defecto
        fecha_fin_str = "Fin"
        año_seleccionado = self.año_combo.currentText()
        mes_seleccionado = self.mes_combo.currentText()
        if self.df is not None and not self.df.empty:
            fecha_inicio = self.df['FECHA'].min()
            fecha_fin = self.df['FECHA'].max()
            if isinstance(fecha_inicio, pd.Timestamp):
                fecha_inicio_str = fecha_inicio.strftime('%d/%m/%Y')
            if isinstance(fecha_fin, pd.Timestamp):
                fecha_fin_str = fecha_fin.strftime('%d/%m/%Y')
            if año_seleccionado != "Todos":
                fecha_inicio_str = f"01/01/{año_seleccionado}"
                fecha_fin_str = f"31/12/{año_seleccionado}"
            if mes_seleccionado != "Todos":
                mes_numero = {
                    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
                    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
                    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
                }.get(mes_seleccionado)
                if mes_numero:
                   fecha_inicio_str = f"01/{mes_numero:02}/{fecha_inicio.year if isinstance(fecha_inicio, pd.Timestamp) else año_seleccionado}"
                   fecha_fin_str = f"{calendar.monthrange(fecha_inicio.year if isinstance(fecha_inicio, pd.Timestamp) else int(año_seleccionado), mes_numero)[1]:02}/{mes_numero:02}/{fecha_fin.year if isinstance(fecha_fin, pd.Timestamp) else año_seleccionado}"

        # Análisis de datos para el resumen ejecutivo
        total_robos = len(self.df) if self.df is not None else 0
        zonas_riesgo = self.df['COLONIA'].value_counts().head(3).index.tolist() if self.df is not None and not self.df.empty else []
        porcentaje_zonas_riesgo = (self.df['COLONIA'].value_counts().head(3).sum() / len(self.df)) * 100 if self.df is not None and not self.df.empty else 0
        dias_semana_pico = self.df['FECHA'].dt.day_name().value_counts().head(2).index.tolist() if self.df is not None and not self.df.empty else []
        horas_pico = self.df['HORA REDONDEADA'].value_counts().head(2).index.tolist() if self.df is not None and not self.df.empty else []
        tipos_vehiculos_mas_frecuentes = self.df['CLASIFICACION'].value_counts().head(2).index.tolist() if self.df is not None and not self.df.empty else []

        # Formatear las horas pico para mostrarlas correctamente
        horas_pico_str = [str(h) for h in horas_pico]

        # Traducir los días de la semana al español
        dias_semana_pico_espanol = [self.traducir_dia(dia) for dia in dias_semana_pico]

        # Resumen Ejecutivo
        resumen_ejecutivo_texto = f"""
        En el presente informe, se analizan los robos de vehículos registrados en el periodo de {fecha_inicio_str} - {fecha_fin_str}.
        Se observa un total de {total_robos} robos.
        Las zonas de mayor riesgo son {', '.join(zonas_riesgo)}, donde se concentra el {porcentaje_zonas_riesgo:.2f}% de los robos.
        Los robos tienden a ocurrir con mayor frecuencia los días <b>{', '.join(dias_semana_pico_espanol)}</b> en el horario de {', '.join(horas_pico_str)} horas.
        Los tipos de vehículos más afectados son {', '.join(tipos_vehiculos_mas_frecuentes)}.
        """
        resumen_ejecutivo = Paragraph(resumen_ejecutivo_texto, styles['Normal'])
        story.append(resumen_ejecutivo)
        story.append(Spacer(1, 0.2*inch))
        

        # Gráfico de robos por año
        ruta_grafico_año = self.guardar_grafico_matplotlib(self.grafico_principal_view)
        if ruta_grafico_año:
            imagen_grafico_año = ReportLabImage(ruta_grafico_año, width=6*inch, height=4*inch)
            story.append(Paragraph("Total de Robos por Año", styles['h2']))
            story.append(imagen_grafico_año)
            story.append(Spacer(1, 0.2*inch))

        # Mapa de puntos
        ruta_mapa_puntos = self.guardar_vista_web(self.mapa_view)
        if ruta_mapa_puntos:
            imagen_mapa_puntos = ReportLabImage(ruta_mapa_puntos, width=6*inch, height=4*inch)
            story.append(Paragraph("Mapa de Puntos de Robos", styles['h2']))
            story.append(imagen_mapa_puntos)
            story.append(Spacer(1, 0.2*inch))

        # Tabla de totales
        tabla_totales_data = [["Total Robos:", str(total_robos)],  
                      ["Probabilidad de Robo (Estimada):", self.probabilidad_label.text()]]  # Corrección aquí
        tabla_totales = Table(tabla_totales_data)
        tabla_totales.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(Paragraph("Totales", styles['h2']))
        story.append(tabla_totales)
        story.append(Spacer(1, 0.2*inch))

        # **NUEVO: Tabla de Colonias de Mayor Riesgo con Detalles**
        if self.df is not None and not self.df.empty:
            # Calcular robos por colonia
            robos_por_colonia = self.df['COLONIA'].value_counts()
            # Seleccionar las 5 colonias con más robos
            top_5_colonias = robos_por_colonia.nlargest(5)

            # Preparar los datos detallados para la tabla
            tabla_colonias_riesgo_data = [['Colonia', 'Total Robos', 'Hora Pico', 'Día Pico', 'Probabilidad']]
            for colonia in top_5_colonias.index:
                # Filtrar el DataFrame por la colonia
                df_colonia = self.df[self.df['COLONIA'] == colonia]
                # Calcular la hora pico para la colonia
                hora_pico_colonia = df_colonia['HORA REDONDEADA'].value_counts().idxmax()
                hora_pico_str = str(hora_pico_colonia)  # Formatear la hora
                # Calcular el día pico para la colonia
                dia_pico_colonia = df_colonia['FECHA'].dt.day_name().value_counts().idxmax()
                dia_pico_espanol = self.traducir_dia(dia_pico_colonia)
                # Calcular la probabilidad de robo para la colonia (usando tu función existente)
                probabilidad_colonia = self.calcular_probabilidad_robo(colonia, datetime.now().time(), datetime.now().date(), self.df['CLASIFICACION'].mode()[0] if not self.df['CLASIFICACION'].empty else "N/A")

                tabla_colonias_riesgo_data.append([
                    colonia,
                    str(top_5_colonias[colonia]),  # Total de robos
                    hora_pico_str,
                    dia_pico_espanol,
                    f"{probabilidad_colonia:.2f}%"
                ])

            tabla_colonias_riesgo = Table(tabla_colonias_riesgo_data)
            tabla_colonias_riesgo.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(Paragraph("Colonias de Mayor Riesgo con Detalles", styles['h2']))
            story.append(tabla_colonias_riesgo)
            story.append(Spacer(1, 0.2*inch))

        # **NUEVO: Tabla de Placas Repetidas (Simplificada)**
        placas_repetidas_detalles = self.obtener_placas_repetidas_con_detalles_simplificado()  # Nueva función
        if placas_repetidas_detalles:
            tabla_placas_data = [["Placa", "Clasificación del Vehículo", "Incidente"]]
            for placa, detalles_lista in placas_repetidas_detalles.items():
                for detalle in detalles_lista:
                    tabla_placas_data.append([str(placa), str(detalle['CLASIFICACION']), str(detalle['INCIDENTE'])])

            tabla_placas = Table(tabla_placas_data, colWidths=[1.5*inch, 2.0*inch, 2.0*inch])
            tabla_placas.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ]))
            story.append(Paragraph("Placas de Vehículos Repetidas", styles['h2']))
            story.append(tabla_placas)
            story.append(Spacer(1, 0.2*inch))

        # **NUEVO: Tabla de Series Repetidas (Simplificada)**
        series_repetidas_detalles = self.obtener_series_repetidas_con_detalles_simplificado()  # Nueva función
        if series_repetidas_detalles:
            tabla_series_data = [["Serie", "Clasificación del Vehículo", "Incidente"]]
            for serie, detalles_lista in series_repetidas_detalles.items():
                for detalle in detalles_lista:
                    tabla_series_data.append([str(serie), str(detalle['CLASIFICACION']), str(detalle['INCIDENTE'])])

            tabla_series = Table(tabla_series_data, colWidths=[1.5*inch, 2.0*inch, 2.0*inch])
            tabla_series.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ]))
            story.append(Paragraph("Series de Vehículos Repetidas", styles['h2']))
            story.append(tabla_series)
            story.append(Spacer(1, 0.2*inch))

        # Agregar filtros aplicados
        filtros_activos = []
        if self.año_combo.currentText() != "Todos":
            filtros_activos.append(f"Año: {self.año_combo.currentText()}")
        if self.mes_combo.currentText() != "Todos":
            filtros_activos.append(f"Mes: {self.mes_combo.currentText()}")
        if self.colonia_combo.currentText() != "Todas":
            filtros_activos.append(f"Colonia: {self.colonia_combo.currentText()}")
        if self.clasificacion_combo.currentText() != "Todas":
            filtros_activos.append(f"Clasificación: {self.clasificacion_combo.currentText()}")
        if filtros_activos:
            story.append(Paragraph("Filtros Aplicados:", styles['h2']))
            story.append(Spacer(1, 0.1*inch))
            for filtro in filtros_activos:
                story.append(Paragraph(filtro, styles['Normal']))
            story.append(Spacer(1, 0.2*inch))

        doc.build(story)
    def traducir_dia(self, dia_en_ingles):
        dias_semana = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
        }
        return dias_semana.get(dia_en_ingles, dia_en_ingles)

    def obtener_placas_repetidas_con_detalles_simplificado(self):
        placas_repetidas = {}
        if self.df is not None and not self.df.empty:
            conteo_placas = self.df['PLACA'].value_counts()
            placas_con_repeticiones = conteo_placas[conteo_placas > 1].index.tolist()
            for placa in placas_con_repeticiones:
                detalles = self.df[self.df['PLACA'] == placa][['INCIDENTE', 'CLASIFICACION']].to_dict('records')
                placas_repetidas[placa] = detalles
        return placas_repetidas

    def obtener_series_repetidas_con_detalles_simplificado(self):
        series_repetidas = {}
        if self.df is not None and not self.df.empty:
            conteo_series = self.df['SERIE'].value_counts()
            series_con_repeticiones = conteo_series[conteo_series > 1].index.tolist()
            for serie in series_con_repeticiones:
                detalles = self.df[self.df['SERIE'] == serie][['INCIDENTE', 'CLASIFICACION']].to_dict('records')
                series_repetidas[serie] = detalles
        return series_repetidas

    def guardar_vista_web(self, view: QWebEngineView, filename="temp_map.png"):
        ruta_absoluta = os.path.abspath(filename)
        try:
            view.grab().toImage().save(ruta_absoluta, "png")
            print(f"Mapa guardado temporalmente como: {ruta_absoluta}")
            return ruta_absoluta
        except Exception as e:
            print(f"Error al guardar el mapa temporal: {e}")
            return None

    def guardar_grafico_matplotlib(self, label: QLabel, filename="temp_graph.png"):
        ruta_absoluta = os.path.abspath(filename)
        pixmap = label.pixmap()
        if pixmap:
            try:
                image = pixmap.toImage()
                image.save(ruta_absoluta, "PNG")
                print(f"Gráfico guardado temporalmente como: {ruta_absoluta}")
                return ruta_absoluta
            except Exception as e:
                print(f"Error al guardar el gráfico temporal: {e}")
                return None
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.actualizar_grafico_principal(self.grafico_principal_selector.currentIndex())

    def detectar_anomalias_colonia(self, df, num_desviaciones=2):
        print("Ejecutando detectar_anomalias_colonia")
        robos_por_colonia = df['COLONIA'].value_counts()
        media_robos = robos_por_colonia.mean()
        desviacion_estandar_robos = robos_por_colonia.std()
        umbral_anomalia = media_robos + num_desviaciones * desviacion_estandar_robos
        colonias_anomalas = robos_por_colonia[robos_por_colonia > umbral_anomalia].index.tolist()
        print("Fin de ejecutar detectar_anomalias_colonia")
        return colonias_anomalas

    def detectar_anomalias_hora(self, df, num_desviaciones=2):
        print("Ejecutando detectar_anomalias_hora")
        robos_por_hora = df['HORA REDONDEADA'].value_counts().sort_index()
        media_robos = robos_por_hora.mean()
        desviacion_estandar_robos = robos_por_hora.std()
        umbral_anomalia = media_robos + num_desviaciones * desviacion_estandar_robos
        horas_anomalas = robos_por_hora[robos_por_hora > umbral_anomalia].index.tolist()
        print("Fin de ejecutar detectar_anomalias_hora")
        return horas_anomalas

    def detectar_anomalias_dia_semana(self, df, num_desviaciones=2):
        print("Ejecutando detectar_anomalias_dia_semana")
        robos_por_dia_semana = df['FECHA'].dt.day_name().value_counts()
        media_robos = robos_por_dia_semana.mean()
        desviacion_estandar_robos = robos_por_dia_semana.std()
        umbral_anomalia = media_robos + num_desviaciones * desviacion_estandar_robos
        dias_semana_anomalos = robos_por_dia_semana[robos_por_dia_semana > umbral_anomalia].index.tolist()
        print("Fin de ejecutar detectar_anomalias_dia_semana")
        return dias_semana_anomalos

    def detectar_outliers_zscore(self, df, columna, umbral_zscore=3):
        print("Ejecutando detectar_outliers_zscore")
        df_columna = df[columna]
        media = df_columna.mean()
        desviacion_estandar = df_columna.std()
        z_scores = np.abs((df_columna - media) / desviacion_estandar)
        outliers = df[z_scores > umbral_zscore]
        print("Fin de ejecutar detectar_outliers_zscore")
        return outliers

    def detectar_anomalias(self):
        """
        Detecta anomalías en los datos de robos y las muestra en el QTextEdit de anomalías.
        """
        if self.df is None or self.df.empty:
            print("No hay datos cargados para detectar anomalías.")
            self.anomalias_text.setHtml("<p>No hay datos cargados para detectar anomalías.</p>")
            return

        print("Ejecutando detectar_anomalias")
        anomalias_colonia = self.detectar_anomalias_colonia(self.df)
        anomalias_hora = self.detectar_anomalias_hora(self.df)
        anomalias_dia_semana = self.detectar_anomalias_dia_semana(self.df)
        outliers_latitud = self.detectar_outliers_zscore(self.df, 'LATITUD')
        outliers_longitud = self.detectar_outliers_zscore(self.df, 'LONGITUD')

        self.anomalias = {
            'colonias': anomalias_colonia,
            'horas': anomalias_hora,
            'dias_semana': anomalias_dia_semana,
            'outliers_latitud': outliers_latitud.to_dict(orient='records'),
            'outliers_longitud': outliers_longitud.to_dict(orient='records')
        }

        print("Anomalías detectadas:", self.anomalias)

        # Generar la tabla HTML para las anomalías
        html_tabla_anomalias = "<table style='border-collapse: collapse; width: 100%;'>"
        html_tabla_anomalias += "<tr style='background-color: #3a3f4b; color: white;'><th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Tipo</th><th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Valor</th></tr>"

        for tipo, valores in self.anomalias.items():
            if tipo in ['colonias', 'horas', 'dias_semana']:
                if valores:
                    html_tabla_anomalias += f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>Anomalías {tipo.capitalize()}</td><td style='border: 1px solid #ddd; padding: 8px;'>{', '.join(map(str, valores))}</td></tr>"
                else:
                    html_tabla_anomalias += f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>Anomalías {tipo.capitalize()}</td><td style='border: 1px solid #ddd; padding: 8px;'>Ninguna</td></tr>"
            elif tipo in ['outliers_latitud', 'outliers_longitud']:
                if valores:
                    for outlier in valores:
                        html_tabla_anomalias += f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>Outlier {tipo.capitalize()}</td><td style='border: 1px solid #ddd; padding: 8px;'>Latitud: {outlier['LATITUD']}, Longitud: {outlier['LONGITUD']}</td></tr>"
                else:
                    html_tabla_anomalias += f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>Outliers {tipo.capitalize()}</td><td style='border: 1px solid #ddd; padding: 8px;'>Ninguno</td></tr>"

        html_tabla_anomalias += "</table>"
        # Mostrar la tabla de anomalías en el QTextEdit de anomalías (izquierda inferior)
        self.anomalias_text.setHtml(html_tabla_anomalias)
        print("Fin de ejecutar detectar_anomalias")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

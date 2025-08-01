import sys
from logging import Logger

import requests
import time
import socket

from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer

API_URL = "https://www.bitmex.com/api/v1/trade?symbol=XBT&count=1&reverse=true"
BTC_UPDATE_INTERVAL_MS = 5000  # refrescar cada 5 s
UPDATE_INTERVAL_MS = 1000  # refrescar cada 1 s
SUMMARY_UPDATE_INTERVAL_MS = 1000  # refrescar summary cada 1 s
LONG_PRESS_DURATION = 2  # segundos para considerar como pulsación larga


class BTCViewer(QWidget):
    def __init__(self):
        super().__init__()
        # Configuración ventana
        self.setWindowTitle("BTC Price")

        # Variables para el clic prolongado
        self.press_start_time = 0
        self.press_pos = None

        # Crear layout principal
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Eliminar márgenes
        self.setLayout(layout)

        # Preparar imagen de fondo
        self.background_label = QLabel(self)
        self.background_label.setAlignment(Qt.AlignCenter)

        # Cargar imagen original
        original_pixmap = QPixmap("/home/nocoiner/NoCoinerBoxNativeApp/splash.png")
        if original_pixmap.isNull():
            original_pixmap = QPixmap("./splash.png")
            if original_pixmap.isNull():
                # Crea un fondo negro de emergencia
                original_pixmap = QPixmap(480, 320)
                original_pixmap.fill(Qt.black)


        # Recortar para obtener ratio 480:320 (3:2)
        img_width = original_pixmap.width()
        img_height = original_pixmap.height()
        target_ratio = 480 / 320  # = 1.5

        current_ratio = img_width / img_height
        if current_ratio > target_ratio:
            # La imagen es más ancha, recortar los lados
            new_width = int(img_height * target_ratio)
            x_offset = (img_width - new_width) // 2
            original_pixmap = original_pixmap.copy(x_offset, 0, new_width, img_height)
        else:
            # La imagen es más alta, recortar arriba y abajo
            new_height = int(img_width / target_ratio)
            y_offset = (img_height - new_height) // 2
            original_pixmap = original_pixmap.copy(0, y_offset, img_width, new_height)


        # Invertir colores
        inverted_pixmap = QPixmap(original_pixmap.size())

        inverted_pixmap.fill(Qt.black)

        painter = QPainter(inverted_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_Difference)
        painter.drawPixmap(0, 0, original_pixmap)
        painter.end()

        # Oscurecer la imagen
        dark_pixmap = QPixmap(inverted_pixmap.size())
        dark_painter = QPainter(dark_pixmap)
        dark_painter.drawPixmap(0, 0, inverted_pixmap)
        dark_painter.fillRect(dark_pixmap.rect(), QColor(0, 0, 0, 150))
        dark_painter.end()

        self.original_dark_pixmap = dark_pixmap  # Guardar referencia del pixmap original
        self.background_label.setPixmap(dark_pixmap)
        layout.addWidget(self.background_label)

        self.background_label.setPixmap(dark_pixmap)
        layout.addWidget(self.background_label)

        # Label para mostrar el precio (encima de la imagen)
        self.label = QLabel("Cargando...", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 36px; font-weight: bold;")
        self.label.raise_()  # Elevar por encima del fondo

        # Nuevo label para mostrar la IP
        self.ip_label = QLabel("Obteniendo ip...", self)
        self.ip_label.setAlignment(Qt.AlignCenter)
        self.ip_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        self.ip_label.raise_()

        # Nuevo label para mostrar la IP del minero
        self.config_natio_box_ip_label = QLabel("Obteniendo ip del minero ...", self)
        self.config_natio_box_ip_label.setAlignment(Qt.AlignCenter)
        self.config_natio_box_ip_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        self.config_natio_box_ip_label.raise_()

        # Label para hashrate
        self.hashrate_label = QLabel("Hashrate: --", self)
        self.hashrate_label.setAlignment(Qt.AlignCenter)
        self.hashrate_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.hashrate_label.raise_()

        # Label para temperatura
        self.temp_label = QLabel("Temperatura: --", self)
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.temp_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.temp_label.raise_()

        # Label para pool
        self.pool_label = QLabel("Pool: --", self)
        self.pool_label.setAlignment(Qt.AlignCenter)
        self.pool_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.pool_label.raise_()

        # Botón para cerrar (inicialmente oculto)
        self.close_button = QPushButton("Cerrar", self)
        self.close_button.setStyleSheet("background-color: #333; color: white; font-size: 16px; padding: 8px;")
        self.close_button.clicked.connect(self.close)
        self.close_button.setVisible(False)
        self.close_button.raise_()  # Elevar por encima del fondo

        # Temporizador para actualizar precio de BTC
        price_timer = QTimer(self)
        price_timer.timeout.connect(self.update_btc_price)
        price_timer.start(BTC_UPDATE_INTERVAL_MS)

        # Temporizador para actualizar datos de summary
        summary_timer = QTimer(self)
        summary_timer.timeout.connect(self.update_summary)
        summary_timer.start(SUMMARY_UPDATE_INTERVAL_MS)

        # Ejecutar una vez al inicio
        self.update_btc_price()
        self.update_summary()

        self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Ajustar el fondo
        self.background_label.setGeometry(0, 0, self.width(), self.height())

        # Escalar imagen
        scaled_pixmap = self.original_dark_pixmap.scaled(
            self.width(), self.height(),
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        self.background_label.setPixmap(scaled_pixmap)

        # Configuración para el centrado
        label_height = 25
        spacing = 10
        num_labels = 6  # Precio, IP local, IP minero, hashrate, temp, pool

        # Cálculo de la altura total del grupo de elementos
        total_height = (label_height * num_labels) + (spacing * (num_labels - 1))

        # Posición inicial para centrar verticalmente (restando altura del botón)
        start_y = (self.height() - total_height) // 2 - 20

        # Precio de Bitcoin (elemento principal, más grande)
        self.label.setGeometry(0, start_y, self.width(), 40)
        y_pos = start_y + 40 + spacing


        # Resto de etiquetas
        self.ip_label.setGeometry(0, y_pos, self.width(), label_height)
        y_pos += label_height + spacing

        self.config_natio_box_ip_label.setGeometry(0, y_pos, self.width(), label_height)
        y_pos += label_height + spacing

        self.hashrate_label.setGeometry(0, y_pos, self.width(), label_height)
        y_pos += label_height + spacing

        self.temp_label.setGeometry(0, y_pos, self.width(), label_height)
        y_pos += label_height + spacing

        self.pool_label.setGeometry(0, y_pos, self.width(), label_height)

        # Botón de cerrar (en la parte inferior)
        self.close_button.setGeometry(
            self.width() // 2 - 50,
            self.height() - 50,
            100, 35
        )

    def mousePressEvent(self, event):
        self.press_start_time = time.time()
        self.press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.press_start_time > 0:
            duration = time.time() - self.press_start_time
            if duration >= LONG_PRESS_DURATION and self.press_pos:
                width = self.width()
                height = self.height()
                x, y = self.press_pos.x(), self.press_pos.y()

                if x > width * 0.5 and y > height * 0.5:
                    self.close_button.setVisible(True)

        self.press_start_time = 0
        self.press_pos = None
        super().mouseReleaseEvent(event)

    '''def update_price(self):
        try:
            resp = requests.get(API_URL, timeout=3)
            data = resp.json()
            price = data[0]["price"]
            self.label.setText(f"₿ {price:,.0f}")
        except Exception as e:
            self.label.setText("Error al obtener precio")
            print("Fetch error:", e)'''

    def update_info(self):
        # (Método antiguo, ya no se usa con temporizador)
        pass

    def update_btc_price(self):
        """Fetch and display only the BTC price."""
        try:
            resp = requests.get(API_URL, timeout=3)
            data = resp.json()
            price = data[0]["price"]
            self.label.setText(f"₿ {price:,.0f}")
        except Exception as e:
            self.label.setText("Error al obtener precio")
            print("Fetch BTC price error:", e)

    def update_summary(self):
        """Fetch and display only the miner summary info."""
        summary = self.get_summary_data()
        miner = summary.get("miner", {})
        instant_hashrate = miner.get("instant_hashrate", "--")
        pcb_temp = miner.get("pcb_temp", {})
        temp_max = pcb_temp.get("max", "--")
        pools = miner.get("pools", [])
        pool0_url = pools[0].get("url", "--") if pools else "--"

        # Formatear hashrate a dos decimales
        if isinstance(instant_hashrate, (int, float)):
            formatted_hashrate = f"{instant_hashrate:.2f}"
        else:
            formatted_hashrate = instant_hashrate

        self.hashrate_label.setText(f"Hashrate: {formatted_hashrate} TH/s")
        self.temp_label.setText(f"Temperatura PCB: {temp_max} °C")
        self.pool_label.setText(f"Pool: {pool0_url}")

        # Actualizar IP del minero
        self.config_natio_box_ip_label.setText(f"Config: {self.get_local_ip()}:8000")

    # Añade esta función para obtener la IP local
    def get_local_ip(self):
        try:
            # Conectar a un servidor externo para determinar la interfaz que usa internet
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "IP desconocida"

    def get_summary_data(self) -> dict:
        """Fetch all summary data from the miner and return as a dict."""
        try:
            resp = requests.get("http://192.168.220.3/api/v1/summary", timeout=3)
            return resp.json()
        except Exception as e:
            print(f"Fetch summary error: {e}")
            return {}




if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = BTCViewer()
    viewer.show()
    sys.exit(app.exec_())
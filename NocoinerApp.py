import sys
import requests
import time

from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer

API_URL = "https://www.bitmex.com/api/v1/trade?symbol=XBT&count=1&reverse=true"
UPDATE_INTERVAL_MS = 5000  # refrescar cada 5 s
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

        # En el método __init__, modifica la carga y procesamiento de imagen:
        # Cargar y procesar imagen
        original_pixmap = QPixmap("dosc.png")

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
        dark_painter.fillRect(dark_pixmap.rect(), QColor(0, 0, 0, 200))
        dark_painter.end()

        self.original_dark_pixmap = dark_pixmap  # Guardar referencia del pixmap original
        self.background_label.setPixmap(dark_pixmap)
        layout.addWidget(self.background_label)

        self.background_label.setPixmap(dark_pixmap)
        layout.addWidget(self.background_label)

        # Label para mostrar el precio (encima de la imagen)
        self.label = QLabel("Cargando...", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 48px; font-weight: bold;")
        self.label.raise_()  # Elevar por encima del fondo

        # Botón para cerrar (inicialmente oculto)
        self.close_button = QPushButton("Cerrar", self)
        self.close_button.setStyleSheet("background-color: #333; color: white; font-size: 16px; padding: 8px;")
        self.close_button.clicked.connect(self.close)
        self.close_button.setVisible(False)
        self.close_button.raise_()  # Elevar por encima del fondo

        # Temporizador para actualizar
        timer = QTimer(self)
        timer.timeout.connect(self.update_price)
        timer.start(UPDATE_INTERVAL_MS)

        self.update_price()
        self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Ajustar el fondo al tamaño completo de la ventana
        self.background_label.setGeometry(0, 0, self.width(), self.height())

        # Escalar la imagen al tamaño de la ventana sin mantener proporción para cubrir todo
        scaled_pixmap = self.original_dark_pixmap.scaled(
            self.width(), self.height(),
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )

        # Actualizar la imagen mostrada
        self.background_label.setPixmap(scaled_pixmap)

        # Centrar elementos en la pantalla
        self.label.setGeometry(0, self.height() // 2 - 50, self.width(), 100)
        self.close_button.setGeometry(
            self.width() // 2 - 50,
            self.height() // 2 + 50,
            100, 40
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

                if x > width * 0.8 and y > height * 0.8:
                    self.close_button.setVisible(True)

        self.press_start_time = 0
        self.press_pos = None
        super().mouseReleaseEvent(event)

    def update_price(self):
        try:
            resp = requests.get(API_URL, timeout=3)
            data = resp.json()
            price = data[0]["price"]
            self.label.setText(f"₿ {price:,.0f}")
        except Exception as e:
            self.label.setText("Error al obtener precio")
            print("Fetch error:", e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = BTCViewer()
    viewer.show()
    sys.exit(app.exec_())
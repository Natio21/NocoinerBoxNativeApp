import sys
import requests
import time

from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer

API_URL = "https://www.bitmex.com/api/v1/trade?symbol=XBT&count=1&reverse=true"
UPDATE_INTERVAL_MS = 5000  # refrescar cada 5 s
LONG_PRESS_DURATION = 5  # segundos para considerar como pulsación larga


class BTCViewer(QWidget):
    def __init__(self):
        super().__init__()
        # Configuración ventana
        self.setWindowTitle("BTC Price")
        self.setStyleSheet("background-color: black;")

        # Variables para el clic prolongado
        self.press_start_time = 0
        self.press_pos = None

        # Crear layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Añadir imagen
        '''self.image_label = QLabel(self)
        pixmap = QPixmap("dosc.png")
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)'''

        # Añadir imagen
        self.image_label = QLabel(self)
        original_pixmap = QPixmap("dosc.png")

        # Crear una nueva imagen con fondo negro
        inverted_pixmap = QPixmap(original_pixmap.size())
        inverted_pixmap.fill(Qt.black)

        # Pintar la imagen original con color invertido
        painter = QPainter(inverted_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_Difference)
        painter.drawPixmap(0, 0, original_pixmap)
        painter.end()

        self.image_label.setPixmap(inverted_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        # Label para mostrar el precio
        self.label = QLabel("Cargando...", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 128px;")
        layout.addWidget(self.label)

        # Botón para cerrar (inicialmente oculto)
        self.close_button = QPushButton("Cerrar", self)
        self.close_button.setStyleSheet("background-color: #333; color: white; font-size: 160px; padding: 80px;")
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button, alignment=Qt.AlignCenter)
        self.close_button.setVisible(False)  # Inicialmente invisible

        # Temporizador para actualizar
        timer = QTimer(self)
        timer.timeout.connect(self.update_price)
        timer.start(UPDATE_INTERVAL_MS)

        self.update_price()
        self.showFullScreen()

    def mousePressEvent(self, event):
        # Registrar cuándo y dónde se presionó el mouse
        self.press_start_time = time.time()
        self.press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Verificar si fue un clic prolongado
        if self.press_start_time > 0:
            duration = time.time() - self.press_start_time
            # Verificar si el clic fue en la esquina inferior derecha
            if duration >= LONG_PRESS_DURATION and self.press_pos:
                width = self.width()
                height = self.height()
                x, y = self.press_pos.x(), self.press_pos.y()

                # Definir la zona de detección (20% inferior y derecha de la pantalla)
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
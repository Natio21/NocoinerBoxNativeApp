# NocoinerApp.py
import os
import sys
import time
import requests
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer

API_URL = "https://www.bitmex.com/api/v1/trade?symbol=XBT&count=1&reverse=true"
UPDATE_INTERVAL_MS = 5000
LONG_PRESS_DURATION = 2

def wait_for_display(timeout=120):
    """Espera hasta que X esté listo."""
    for _ in range(timeout * 10):
        if os.path.exists("/tmp/.X11-unix/X0"):
            return True
        time.sleep(0.1)
    return False

class BTCViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.press_start_time = 0
        self.press_pos = None
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)

        self.background_label = QLabel(self)
        self.background_label.setAlignment(Qt.AlignCenter)
        original_pixmap = QPixmap("dosc.png")
        iw, ih = original_pixmap.width(), original_pixmap.height()
        tr = 480/320
        cr = iw/ih
        if cr > tr:
            nw = int(ih * tr)
            xo = (iw - nw)//2
            original_pixmap = original_pixmap.copy(xo,0,nw,ih)
        else:
            nh = int(iw / tr)
            yo = (ih - nh)//2
            original_pixmap = original_pixmap.copy(0,yo,iw,nh)

        inv = QPixmap(original_pixmap.size())
        inv.fill(Qt.black)
        p = QPainter(inv)
        p.setCompositionMode(QPainter.CompositionMode_Difference)
        p.drawPixmap(0,0,original_pixmap)
        p.end()

        dark = QPixmap(inv.size())
        dp = QPainter(dark)
        dp.drawPixmap(0,0,inv)
        dp.fillRect(dark.rect(), QColor(0,0,0,200))
        dp.end()

        self.original_dark_pixmap = dark
        self.background_label.setPixmap(dark)
        layout.addWidget(self.background_label)

        self.label = QLabel("Cargando...", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 48px; font-weight: bold;")
        self.label.raise_()

        self.close_button = QPushButton("Cerrar", self)
        self.close_button.setStyleSheet("background-color: #333; color: white; font-size: 16px; padding: 8px;")
        self.close_button.clicked.connect(self.close)
        self.close_button.setVisible(False)
        self.close_button.raise_()

        timer = QTimer(self)
        timer.timeout.connect(self.update_price)
        timer.start(UPDATE_INTERVAL_MS)
        self.update_price()
        self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.background_label.setGeometry(0,0,self.width(),self.height())
        scaled = self.original_dark_pixmap.scaled(self.width(), self.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.background_label.setPixmap(scaled)
        self.label.setGeometry(0, self.height()//2 - 50, self.width(), 100)
        self.close_button.setGeometry(self.width()//2 - 50, self.height()//2 + 50, 100, 40)

    def mousePressEvent(self, event):
        self.press_start_time = time.time()
        self.press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.press_start_time > 0:
            duration = time.time() - self.press_start_time
            if duration >= LONG_PRESS_DURATION and self.press_pos:
                x,y = self.press_pos.x(), self.press_pos.y()
                w,h = self.width(), self.height()
                if x > w*0.5 and y > h*0.5:
                    self.close_button.setVisible(True)
        self.press_start_time = 0
        self.press_pos = None
        super().mouseReleaseEvent(event)

    def update_price(self):
        try:
            resp = requests.get(API_URL, timeout=3)
            price = resp.json()[0]["price"]
            self.label.setText(f"₿ {price:,.0f}")
        except Exception as e:
            self.label.setText("Error al obtener precio")
            print("Fetch error:", e)

if __name__ == "__main__":
    if not wait_for_display():
        print("ERROR: DISPLAY no está listo.")
        sys.exit(1)
    app = QApplication(sys.argv)
    viewer = BTCViewer()
    sys.exit(app.exec_())
import logging
import sys
from logging import Logger

import requests
import time
import socket
import subprocess
import shutil
from functools import partial
from typing import Tuple

from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QGridLayout,
    QDialog,
    QLineEdit,
    QFormLayout,
    QHBoxLayout,
    QCheckBox,
    QMessageBox,
    QSizePolicy,
    QScrollArea,
    QButtonGroup,
)
from PyQt5.QtCore import Qt, QTimer, QEvent

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

        # Credenciales de WiFi configurables
        self.ssid = ""
        self.password = ""

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
        self.label.setStyleSheet("color: white; font-size: 26px; font-weight: bold;")
        self.label.raise_()  # Elevar por encima del fondo

        # Nuevo label para mostrar la IP
        self.ip_label = QLabel("Obteniendo ip...", self)
        self.ip_label.setAlignment(Qt.AlignCenter)
        self.ip_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        self.ip_label.raise_()

        # Label para hashrate
        self.hashrate_label = QLabel("Hashrate: --", self)
        self.hashrate_label.setAlignment(Qt.AlignCenter)
        self.hashrate_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        self.hashrate_label.raise_()

        # Nuevo label para mostrar la IP del minero
        self.config_natio_box_ip_label = QLabel("Obteniendo ip del minero ...", self)
        self.config_natio_box_ip_label.setAlignment(Qt.AlignCenter)
        self.config_natio_box_ip_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.config_natio_box_ip_label.raise_()

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

        # Botón de configuración (siempre visible en la esquina superior derecha)
        self.settings_button = QPushButton("Config", self)
        self.settings_button.setStyleSheet(
            "background-color: #444; color: white; font-size: 14px; padding: 6px;"
        )
        self.settings_button.clicked.connect(self.open_config_dialog)
        self.settings_button.raise_()

        # Botón para cerrar (inicialmente oculto)
        self.close_button = QPushButton("Cerrar", self)
        self.close_button.setStyleSheet("background-color: #333; color: white; font-size: 16px; padding: 8px;")
        self.close_button.clicked.connect(self.close)
        self.close_button.setVisible(False)
        self.close_button.raise_()  # Elevar por encima del fondo

        # Temporizador para actualizar precio de BTC
        self.price_timer = QTimer(self)
        self.price_timer.timeout.connect(self.update_btc_price)
        self.price_timer.start(BTC_UPDATE_INTERVAL_MS)

        # Temporizador para actualizar datos de summary
        self.summary_timer = QTimer(self)
        self.summary_timer.timeout.connect(self.update_summary)
        self.summary_timer.start(SUMMARY_UPDATE_INTERVAL_MS)

        # Ejecutar una vez al inicio
        self.update_btc_price()
        self.update_summary()
        self._next_summary_retry = 0

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

        # Botón de configuración (esquina superior derecha)
        self.settings_button.setGeometry(
            self.width() - 110,
            10,
            100,
            35,
        )

        # Botón de cerrar (en la parte inferior)
        self.close_button.setGeometry(
            self.width() // 2 - 50,
            self.height() - 50,
            100, 35
        )

    def open_config_dialog(self):
        self.pause_updates()
        dialog = ConfigDialog(self.ssid, self.password, self)
        try:
            if dialog.exec_() == QDialog.Accepted:
                self.ssid, self.password = dialog.get_credentials()
        finally:
            self.resume_updates()
            # Refrescar información tras reanudar
            self.update_btc_price()
            self.update_summary()

    def pause_updates(self):
        if hasattr(self, "price_timer") and self.price_timer.isActive():
            self.price_timer.stop()
        if hasattr(self, "summary_timer") and self.summary_timer.isActive():
            self.summary_timer.stop()

    def resume_updates(self):
        if hasattr(self, "price_timer") and not self.price_timer.isActive():
            self.price_timer.start(BTC_UPDATE_INTERVAL_MS)
        if hasattr(self, "summary_timer") and not self.summary_timer.isActive():
            self.summary_timer.start(SUMMARY_UPDATE_INTERVAL_MS)


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
        if getattr(self, "_next_summary_retry", 0) > time.time():
            return

        summary = self.get_summary_data()
        if summary is None:
            self._next_summary_retry = time.time() + 4
            return

        self._next_summary_retry = 0
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
        self.ip_label.setText(f"Ip: {self.get_local_ip()}")
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
            #resp = requests.get("http://192.168.1.62/api/v1/summary", timeout=3)
            resp = requests.get("http://192.168.220.3/api/v1/summary", timeout=3)
            return resp.json()
        except Exception as e:
            print(f"Fetch summary error: {e}")
            return None


class ConfigDialog(QDialog):
    def __init__(self, current_ssid: str, current_password: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar WiFi")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: #111; color: white;")

        self.selected_ssid = current_ssid
        self.wifi_interface = self._detect_wifi_interface()

        self.ssid_scroll = QScrollArea()
        self.ssid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ssid_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ssid_scroll.setWidgetResizable(True)
        self.ssid_scroll.setFixedHeight(58)
        self.ssid_scroll.setMaximumWidth(280)
        self.ssid_scroll.setStyleSheet("QScrollArea { background-color: #1a1a1a; border: 1px solid #222; }")

        self.ssid_container = QWidget()
        self.ssid_layout = QHBoxLayout(self.ssid_container)
        self.ssid_layout.setContentsMargins(4, 4, 4, 4)
        self.ssid_layout.setSpacing(6)
        self.ssid_scroll.setWidget(self.ssid_container)
        self.ssid_button_group = QButtonGroup(self)
        self.ssid_button_group.setExclusive(True)
        self.ssid_button_group.buttonClicked.connect(self._handle_ssid_button_clicked)

        self.ssid_edit = QLineEdit(current_ssid)
        self.ssid_edit.setStyleSheet("font-size: 14px; padding: 4px 6px;")
        self.ssid_edit.textEdited.connect(self._clear_ssid_selection)
        self.password_edit = QLineEdit(current_password)
        self.password_edit.setStyleSheet("font-size: 14px; padding: 4px 6px;")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.installEventFilter(self)

        self.show_password_checkbox = QCheckBox("Mostrar contraseña")
        self.show_password_checkbox.setStyleSheet("font-size: 12px;")
        self.show_password_checkbox.stateChanged.connect(self._toggle_password_visibility)

        password_row_widget = QWidget()
        password_row_layout = QHBoxLayout(password_row_widget)
        password_row_layout.setContentsMargins(0, 0, 0, 0)
        password_row_layout.setSpacing(6)
        password_row_layout.addWidget(self.password_edit)
        password_row_layout.addWidget(self.show_password_checkbox)

        form_layout = QFormLayout()
        form_layout.setSpacing(4)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.addRow("SSID manual:", self.ssid_edit)
        form_layout.addRow("Password:", password_row_widget)

        self.keyboard = OnScreenKeyboard(self.password_edit, self)
        self.keyboard.setVisible(False)
        self.keyboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.keyboard.setMinimumWidth(320)

        self.toggle_keyboard_button = QPushButton("Mostrar teclado")
        self.toggle_keyboard_button.setStyleSheet("font-size: 12px; padding: 4px 8px;")
        self.toggle_keyboard_button.clicked.connect(self._toggle_keyboard_visibility)
        self.toggle_keyboard_button.setFixedHeight(58)

        self.connect_button = QPushButton("Conectar")
        self.cancel_button = QPushButton("Cancelar")
        for btn in (self.cancel_button, self.connect_button):
            btn.setStyleSheet("font-size: 12px; padding: 4px 10px;")
        self.connect_button.clicked.connect(self._handle_connect)
        self.cancel_button.clicked.connect(self.reject)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        header_layout.addWidget(self.cancel_button)
        header_layout.addStretch(1)

        title_label = QLabel("Selecciona una red WiFi visible:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title_label, 0, Qt.AlignCenter)

        header_layout.addStretch(1)
        header_layout.addWidget(self.connect_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        ssid_controls_layout = QHBoxLayout()
        ssid_controls_layout.setContentsMargins(0, 0, 0, 0)
        ssid_controls_layout.setSpacing(6)
        ssid_controls_layout.addWidget(self.ssid_scroll)
        ssid_controls_layout.addWidget(self.toggle_keyboard_button)

        layout.addLayout(header_layout)
        layout.addLayout(ssid_controls_layout)
        layout.addLayout(form_layout)
        layout.addWidget(self.keyboard, 0, Qt.AlignCenter)
        layout.addStretch(1)
        self.setLayout(layout)

        self._load_wifi_networks()

    def _handle_ssid_button_clicked(self, button):
        self.selected_ssid = button.text()
        self.ssid_edit.setText(self.selected_ssid)

    def _clear_ssid_selection(self):
        for btn in self.ssid_button_group.buttons():
            btn.setChecked(False)
        self.selected_ssid = self.ssid_edit.text()

    def _populate_ssid_buttons(self, networks):
        while self.ssid_layout.count():
            item = self.ssid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for btn in list(self.ssid_button_group.buttons()):
            self.ssid_button_group.removeButton(btn)

        if networks:
            for ssid in networks:
                button = QPushButton(ssid)
                button.setCheckable(True)
                button.setStyleSheet(
                    "QPushButton { background-color: #222; color: white; font-size: 12px; padding: 6px 10px; border-radius: 4px; }"
                    "QPushButton:checked { background-color: #2f6fed; }"
                    "QPushButton:pressed { background-color: #444; }"
                )
                button.setMinimumWidth(120)
                self.ssid_layout.addWidget(button)
                self.ssid_button_group.addButton(button)
                if ssid == self.selected_ssid:
                    button.setChecked(True)
            self.ssid_layout.addStretch(1)
        else:
            info_label = QLabel("No se encontraron redes WiFi visibles")
            info_label.setStyleSheet("font-size: 12px; color: #bbb;")
            self.ssid_layout.addWidget(info_label)
            self.ssid_layout.addStretch(1)

    def _toggle_password_visibility(self, state):
        if state == Qt.Checked:
            self.password_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)

    def _handle_connect(self):
        ssid = self.ssid_edit.text().strip()
        password = self.password_edit.text()

        if not ssid:
            QMessageBox.warning(self, "SSID requerido", "Selecciona o introduce un SSID para continuar.")
            return

        try:
            success = False
            message = ""

            if self._command_available("nmcli"):
                success, message = self._connect_with_nmcli(ssid, password)
            elif self._command_available("wpa_cli"):
                success, message = self._connect_with_wpa_cli(ssid, password)
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se encontró ninguna herramienta compatible (nmcli o wpa_cli) para gestionar la WiFi.",
                )
                return

            if success:
                QMessageBox.information(self, "Conectado", message or f"Se estableció conexión con '{ssid}'.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error de conexión", message or "No se pudo establecer la conexión.")
        except subprocess.TimeoutExpired:
            QMessageBox.critical(self, "Error de conexión", "La conexión tardó demasiado y fue cancelada.")
        except Exception as exc:
            QMessageBox.critical(self, "Error de conexión", str(exc))

    def _load_wifi_networks(self):
        networks = self._scan_wifi_networks()
        self._populate_ssid_buttons(networks)

    def eventFilter(self, obj, event):
        if obj is self.password_edit and event.type() in (QEvent.FocusIn, QEvent.MouseButtonPress):
            self._show_keyboard()
        return super().eventFilter(obj, event)

    def _toggle_keyboard_visibility(self):
        if self.keyboard.isVisible():
            self._hide_keyboard()
        else:
            self._show_keyboard()

    def _show_keyboard(self):
        self.keyboard.reset()
        self.keyboard.setVisible(True)
        self.toggle_keyboard_button.setText("Ocultar teclado")

    def _hide_keyboard(self):
        self.keyboard.setVisible(False)
        self.toggle_keyboard_button.setText("Mostrar teclado")
        self.keyboard.reset()

    def _command_available(self, command: str) -> bool:
        return shutil.which(command) is not None

    def _connect_with_nmcli(self, ssid: str, password: str) -> Tuple[bool, str]:
        command = ["nmcli", "dev", "wifi", "connect", ssid]
        if password:
            command.extend(["password", password])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return True, result.stdout.strip() or f"Se estableció conexión con '{ssid}'."

        error_output = result.stderr.strip() or result.stdout.strip()
        if not error_output:
            error_output = "Error desconocido al conectar con nmcli."
        return False, error_output

    def _connect_with_wpa_cli(self, ssid: str, password: str) -> Tuple[bool, str]:
        try:
            network_id = self._get_or_create_wpa_network(ssid)
        except RuntimeError as exc:
            return False, str(exc)

        try:
            self._configure_wpa_network(network_id, ssid, password)
            self._enable_wpa_network(network_id)
            if self._wait_for_wpa_connection():
                return True, f"Se estableció conexión con '{ssid}' usando wpa_cli."
            return False, "La red no se conectó en el tiempo esperado (wpa_cli)."
        except RuntimeError as exc:
            return False, str(exc)

    def _run_wpa_cli(self, *args: str) -> str:
        command = ["wpa_cli", "-i", self.wifi_interface, *args]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            message = stderr or stdout or "Fallo al ejecutar wpa_cli."
            raise RuntimeError(message)

        return result.stdout.strip()

    def _get_or_create_wpa_network(self, ssid: str) -> str:
        try:
            networks_output = self._run_wpa_cli("list_networks")
        except RuntimeError as exc:
            raise RuntimeError(f"No se pudo listar redes en wpa_cli: {exc}") from exc

        network_id = None
        for line in networks_output.splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1] == ssid:
                network_id = parts[0]
                break

        if network_id is None:
            network_id = self._run_wpa_cli("add_network").strip()
            if not network_id.isdigit():
                raise RuntimeError(f"wpa_cli devolvió un identificador inválido: '{network_id}'.")

        return network_id

    def _configure_wpa_network(self, network_id: str, ssid: str, password: str) -> None:
        quoted_ssid = f'"{ssid}"'
        self._run_wpa_cli("set_network", network_id, "ssid", quoted_ssid)

        if password:
            quoted_psk = f'"{password}"'
            self._run_wpa_cli("set_network", network_id, "psk", quoted_psk)
            self._run_wpa_cli("set_network", network_id, "key_mgmt", "WPA-PSK")
        else:
            self._run_wpa_cli("set_network", network_id, "key_mgmt", "NONE")
            try:
                self._run_wpa_cli("set_network", network_id, "psk", '""')
            except RuntimeError:
                pass

    def _enable_wpa_network(self, network_id: str) -> None:
        self._run_wpa_cli("enable_network", network_id)
        self._run_wpa_cli("select_network", network_id)
        self._run_wpa_cli("save_config")
        self._run_wpa_cli("reconnect")

    def _wait_for_wpa_connection(self, timeout: int = 25) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                status = self._run_wpa_cli("status")
            except RuntimeError:
                break

            if "wpa_state=COMPLETED" in status:
                return True
            time.sleep(1)
        return False

    def _detect_wifi_interface(self) -> str:
        default_interface = "wlan0"
        try:
            result = subprocess.run(
                ["iw", "dev"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("Interface "):
                    return line.split()[1]
        except Exception:
            pass
        return default_interface

    def _scan_wifi_networks(self):
        try:
            if shutil.which("nmcli"):
                output = subprocess.check_output(
                    ["nmcli", "-t", "-f", "SSID", "dev", "wifi"],
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=8,
                )
                networks = []
                for line in output.splitlines():
                    ssid = line.strip()
                    if ssid:
                        networks.append(ssid)
                return self._deduplicate_networks(networks)

            if shutil.which("wpa_cli"):
                subprocess.run(
                    ["wpa_cli", "-i", self.wifi_interface, "scan"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                time.sleep(2)
                result = subprocess.run(
                    ["wpa_cli", "-i", self.wifi_interface, "scan_results"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    return []
                networks = []
                for line in result.stdout.splitlines()[2:]:
                    parts = line.split("\t")
                    if len(parts) >= 5:
                        ssid = parts[4].strip()
                        if ssid:
                            networks.append(ssid)
                return self._deduplicate_networks(networks)
        except Exception:
            return []

        return []

    @staticmethod
    def _deduplicate_networks(networks):
        seen = set()
        unique_networks = []
        for ssid in networks:
            if ssid not in seen:
                seen.add(ssid)
                unique_networks.append(ssid)
        return unique_networks

    def get_credentials(self):
        return self.ssid_edit.text(), self.password_edit.text()


class OnScreenKeyboard(QWidget):
    def __init__(self, target_input: QLineEdit, parent=None):
        super().__init__(parent)
        self.target_input = target_input
        self.shift_enabled = False
        self.char_buttons = []

        self.setStyleSheet(
            "QPushButton { background-color: #222; color: white; padding: 4px; font-size: 12px; border-radius: 3px; }"
            "QPushButton:pressed { background-color: #444; }"
        )

        self._button_size_increase = 12

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(4)
        main_layout.setContentsMargins(0, 0, 0, 0)

        keys_container = QHBoxLayout()
        keys_container.setSpacing(10)

        numeric_keys = [
            ("1", "!"),
            ("2", "@"),
            ("3", "#"),
            ("4", "$"),
            ("5", "%"),
            ("6", "^"),
            ("7", "&"),
            ("8", "*"),
            ("9", "("),
            ("0", ")"),
        ]

        numeric_layout = QGridLayout()
        numeric_layout.setSpacing(4)
        numeric_columns = 4
        for index, (char, shift_char) in enumerate(numeric_keys):
            row = index // numeric_columns
            column = index % numeric_columns
            button = self._create_char_button(char, shift_char)
            numeric_layout.addWidget(button, row, column)

        numeric_container = QVBoxLayout()
        numeric_container.setSpacing(4)
        numeric_container.addLayout(numeric_layout)
        numeric_container.addStretch(1)


        letter_rows_layout = QVBoxLayout()
        letter_rows_layout.setSpacing(4)

        rows = [
            [("q", "Q"), ("w", "W"), ("e", "E"), ("r", "R"), ("t", "T"), ("y", "Y"), ("u", "U"), ("i", "I"), ("o", "O"), ("p", "P")],
            [("a", "A"), ("s", "S"), ("d", "D"), ("f", "F"), ("g", "G"), ("h", "H"), ("j", "J"), ("k", "K"), ("l", "L"), ("ñ", "Ñ")],
            [("z", "Z"), ("x", "X"), ("c", "C"), ("v", "V"), ("b", "B"), ("n", "N"), ("m", "M")],
        ]

        for row_chars in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            for char, shift_char in row_chars:
                button = self._create_char_button(char, shift_char)
                row_layout.addWidget(button)
            letter_rows_layout.addLayout(row_layout)

        symbols_row = [
            ("-", "_"),
            ("=", "+"),
            ("@", "@"),
            ("#", "#"),
            ("$", "$"),
            ("%", "%"),
            ("&", "&"),
            ("*", "*"),
            (".", ">"),
            (",", "<"),
            (";", ":"),
            ("'", '"'),
            ("/", "?"),
            ("\\", "|"),
        ]

        symbols_layout = QGridLayout()
        symbols_layout.setSpacing(4)
        symbols_columns = 5
        for index, (char, shift_char) in enumerate(symbols_row):
            row = index // symbols_columns
            column = index % symbols_columns
            button = self._create_char_button(char, shift_char)
            button.setFixedHeight(28)
            symbols_layout.addWidget(button, row, column)

        symbols_container = QVBoxLayout()
        symbols_container.setSpacing(4)
        symbols_container.addLayout(symbols_layout)
        symbols_container.addStretch(1)

        keys_container.addLayout(numeric_container)
        keys_container.addLayout(letter_rows_layout)
        keys_container.addLayout(symbols_container)

        main_layout.addLayout(keys_container)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(4)

        self.shift_button = QPushButton("Shift")
        self._apply_button_size(self.shift_button)
        self.shift_button.setCheckable(True)
        self.shift_button.toggled.connect(self._toggle_shift)
        control_layout.addWidget(self.shift_button)

        space_button = QPushButton("Espacio")
        self._apply_button_size(space_button)
        space_button.clicked.connect(lambda: self.target_input.insert(" "))
        control_layout.addWidget(space_button)

        backspace_button = QPushButton("Borrar")
        self._apply_button_size(backspace_button)
        backspace_button.clicked.connect(self.target_input.backspace)
        control_layout.addWidget(backspace_button)

        clear_button = QPushButton("Limpiar")
        self._apply_button_size(clear_button)
        clear_button.clicked.connect(self.target_input.clear)
        control_layout.addWidget(clear_button)

        main_layout.addLayout(control_layout)

    def _create_char_button(self, char: str, shift_char: str = None) -> QPushButton:
        button = QPushButton(char)
        button.setProperty("char_lower", char)
        button.setProperty("char_upper", shift_char if shift_char is not None else char.upper())
        button.clicked.connect(partial(self._handle_char_button, button))
        self.char_buttons.append(button)
        self._apply_button_size(button)
        return button


    '''
        Apply size increase to button based on its size hint.
        Args:
            button (QPushButton): The button to apply size increase to.
        
    '''
    def _apply_button_size(self, button: QPushButton):
        size_hint = button.sizeHint()
        #log size_hint
        print(f"Button '{button.text()}' size hint: {size_hint.width()}")
        button.setMinimumSize(
            size_hint.width()//4,
            #self._button_size_increase,
            #size_hint.width() + self._button_size_increase,
            size_hint.height()# + self._button_size_increase,
            #self._button_size_increase,self._button_size_increase
        )

    def _handle_char_button(self, button: QPushButton):
        lower_char = button.property("char_lower")
        upper_char = button.property("char_upper")
        if not lower_char:
            return
        char_to_insert = upper_char if self.shift_enabled and upper_char else lower_char
        self.target_input.insert(char_to_insert)

    def _toggle_shift(self, checked: bool):
        self.shift_enabled = checked
        self._update_char_buttons()

    def _update_char_buttons(self):
        for button in self.char_buttons:
            lower_char = button.property("char_lower")
            upper_char = button.property("char_upper")
            if lower_char:
                if self.shift_enabled and upper_char:
                    button.setText(upper_char)
                else:
                    button.setText(lower_char)

    def reset(self):
        if self.shift_button.isChecked():
            self.shift_button.setChecked(False)
        else:
            self._toggle_shift(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = BTCViewer()
    viewer.show()
    sys.exit(app.exec_())


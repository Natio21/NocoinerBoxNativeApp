# NocoinerBoxNativeApp

> **Español** | **English**

---

## Descripción / Description

**NocoinerBoxNativeApp** es una app ligera en **Python 3 + PyQt5** que muestra el precio de Bitcoin en pantalla completa con fondo negro.  
Ideal para una Raspberry Pi conectada a un minero que hace de calefactor, con futura expansión para datos del hardware.

**NocoinerBoxNativeApp** is a lightweight **Python 3 + PyQt5** application that displays Bitcoin price fullscreen on a black background.  
Perfect for a Raspberry Pi attached to a miner acting as a heater, with future expansion for hardware telemetry.

---

## Tabla de contenidos / Table of Contents

- [Requisitos / Requirements](#requisitos--requirements)  
- [Instalación / Installation](#instalación--installation)  
- [Uso / Usage](#uso--usage)  
- [Estructura del proyecto / Project Structure](#estructura-del-proyecto--project-structure)  
- [Buenas prácticas / Best Practices](#buenas-prácticas--best-practices)  
- [Roadmap / Roadmap](#roadmap--roadmap)  
- [Contribuciones / Contributing](#contribuciones--contributing)  
- [Licencia / License](#licencia--license)  

---

## Requisitos / Requirements

- **SO / OS**: Ubuntu (o Raspberry Pi OS 64 bit basado en Debian/Ubuntu)  
- **Python**: 3.7+  
- **Paquetes**: PyQt5, requests  

---

## Instalación / Installation

1. Clonar el repositorio / Clone the repo:
   ```bash
   git clone https://github.com/tu-usuario/NocoinerBoxNativeApp.git
   cd NocoinerBoxNativeApp




# NoCoinerBoxNativeApp — Guía de Instalación y Autostart en Raspberry Pi

Documentación paso a paso para instalar, configurar y dejar en autostart la aplicación PyQt en una Raspberry Pi, incluyendo splash screen personalizado.  
Pensado tanto para reinstalaciones futuras como para otros colaboradores.

---

## Índice

1. [Requisitos previos](#requisitos-previos)
2. [Instalación de dependencias](#instalación-de-dependencias)
3. [Configurar splash de arranque](#configurar-splash-de-arranque)
4. [Despliegue y autostart de la app PyQt](#despliegue-y-autostart-de-la-app-pyqt)
5. [Solución de problemas comunes](#solución-de-problemas-comunes)
6. [Referencias útiles](#referencias-útiles)
7. [Estructura recomendada](#estructura-recomendada)

---

## 1. Requisitos previos

- Raspberry Pi con Raspbian (Bullseye o Bookworm recomendado)
- Usuario con permisos sudo
- Conexión a internet
- Archivo `splash.png` (PNG válido, preferiblemente 480x320 o 1920x1080)
- Script Python: `NocoinerApp.py`

---

## 2. Instalación de dependencias

```bash
sudo apt-get update
sudo apt-get install python3-pyqt5 python3-pip python3-requests
# Opcional: ocultar cursor si es modo kiosk
sudo apt-get install unclutter
```

---

## 3. Configurar splash de arranque (opcional)

> Si no necesitas cambiar el splash de arranque del sistema, salta a la sección 4.

1. Instala Plymouth y temas:

    ```bash
    sudo apt-get install plymouth plymouth-themes
    ```

2. Sustituye la imagen del tema `pix`:

    ```bash
    sudo cp /ruta/a/splash.png /usr/share/plymouth/themes/pix/splash.png
    ```

3. Aplica el tema y reconstruye el initrd:

    ```bash
    sudo plymouth-set-default-theme pix --rebuild-initrd
    ```

4. Edita `/boot/cmdline.txt` y añade al final (todo en una línea):

    ```
    splash quiet loglevel=0 plymouth.ignore-serial-consoles logo.nologo vt.global_cursor_default=0
    ```

5. Reinicia la Raspberry Pi para comprobar el splash personalizado:

    ```bash
    sudo reboot
    ```

---

## 4. Despliegue y autostart de la app PyQt

### A. Estructura de archivos recomendada

```
/home/nocoiner/NoCoinerBoxNativeApp/
  ├── NocoinerApp.py
  └── splash.png
```

### B. Código robusto de carga de imagen en `NocoinerApp.py`

Reemplaza la carga del QPixmap por este bloque para evitar crasheos si falta la imagen:

```python
import os
from PyQt5.QtGui import QPixmap, QColor

original_pixmap = QPixmap("/home/nocoiner/NoCoinerBoxNativeApp/splash.png")
if original_pixmap.isNull():
    print("ERROR: No se pudo cargar splash.png")
    original_pixmap = QPixmap(480, 320)
    original_pixmap.fill(QColor("black"))
```

### C. Crear servicio systemd para autostart

1. Crea el archivo de servicio:

    ```bash
    sudo nano /etc/systemd/system/nocoiner.service
    ```

2. Añade el siguiente contenido (ajusta usuario si no es `nocoiner`):

    ```ini
    [Unit]
    Description=NoCoinerApp Launcher
    After=graphical.target
    Wants=graphical.target

    [Service]
    Type=simple
    User=nocoiner
    Group=nocoiner
    Environment="DISPLAY=:0"
    Environment="XAUTHORITY=/home/nocoiner/.Xauthority"
    ExecStart=/usr/bin/python3 /home/nocoiner/NoCoinerBoxNativeApp/NocoinerApp.py
    Restart=no

    [Install]
    WantedBy=graphical.target
    ```

3. Recarga y habilita el servicio:

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable nocoiner.service
    sudo systemctl start nocoiner.service
    ```

### D. Comprobaciones manuales y troubleshooting

- Ejecuta el script manualmente para verificar errores:

    ```bash
    sudo -u nocoiner DISPLAY=:0 XAUTHORITY=/home/nocoiner/.Xauthority /usr/bin/python3 /home/nocoiner/NoCoinerBoxNativeApp/NocoinerApp.py
    ```

- Consulta logs para depuración:

    ```bash
    sudo systemctl status nocoiner.service
    sudo journalctl -u nocoiner.service --no-pager
    ```

---

## 5. Solución de problemas comunes

- **ZeroDivisionError en la app**  
  La imagen `splash.png` no existe o está corrupta. Usa ruta absoluta y asegúrate de que el archivo existe con `ls`.

- **El servicio no arranca**  
  Verifica usuario, rutas, permisos y que el entorno gráfico (`DISPLAY=:0`) está activo.  
  Comprueba con `who` que el usuario aparece en `:0`.

- **No se ve el splash**  
  Asegúrate de que la imagen es un PNG válido. Exporta desde GIMP, Paint o similar.

- **Arranca pero se ve el entorno LXDE/panel**  
  Habilita autologin, desactiva el panel si quieres modo kiosk.  
  Instala `unclutter` para ocultar el cursor si es necesario.

---

## 6. Referencias útiles

- [Arch Wiki: Plymouth](https://wiki.archlinux.org/title/Plymouth)
- [Raspberry Pi Forums: Custom Splash](https://forums.raspberrypi.com/viewtopic.php?t=20614)
- [Systemd service docs](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [PyQt5 QPixmap docs](https://doc.qt.io/qtforpython-5/PySide2/QtGui/QPixmap.html)

---

## 7. Estructura recomendada

```
/home/nocoiner/NoCoinerBoxNativeApp/
  ├── NocoinerApp.py
  └── splash.png
/etc/systemd/system/nocoiner.service
```

---

**Última actualización:** Junio 2025  
**Autor:** Alejandro Cordón — [alejandrocordon.com](https://alejandrocordon.com/?utm_source=chatgpt.com)

---


# 📚 Raspberry Pi: Compartir Internet por Ethernet usando WiFi

## Escenario
- Raspberry Pi conectada a Internet vía WiFi (`wlan0`)
- Se conecta un dispositivo por cable al puerto Ethernet (`eth0`) y se desea que tenga acceso a Internet
- Opcional: Que el dispositivo cableado esté en la **misma subred** que el WiFi, o simplemente tenga salida a Internet (subred distinta)

---

## Requisitos
- Raspberry Pi con Raspberry Pi OS o Debian-based
- Acceso de superusuario (`sudo`)
- Conexión establecida a la WiFi
- Acceso a terminal local o SSH

---

## Opción 1: Bridge real (Misma subred)
> **Nota:** Normalmente la WiFi integrada de la Raspberry Pi **NO soporta bridging** real. Solo algunos dongles USB soportan “client mode bridging”. Si esto falla, usa la opción 2.

### 1. Instala utilidades de red
```bash
sudo apt update
sudo apt install bridge-utils ebtables
```

### 2. Edita la configuración de red
```bash
sudo nano /etc/network/interfaces
```
Añade:
```bash
auto br0
iface br0 inet dhcp
  bridge_ports eth0 wlan0
```

### 3. Reinicia la Raspberry Pi
```bash
sudo reboot
```
**Si tras reiniciar no tienes red por cable, tu WiFi no soporta bridging. Usa la Opción 2.**

---

## Opción 2: Compartir Internet vía NAT (Router)
La opción más robusta. El dispositivo conectado por cable tendrá una IP diferente (subred privada), pero tendrá Internet.

### 1. Activa el reenvío de paquetes
```bash
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
```
Para hacerlo permanente:
```bash
sudo nano /etc/sysctl.conf
# Descomenta o añade:
net.ipv4.ip_forward=1
```

### 2. Configura NAT con iptables
```bash
sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
```
Para hacerlo permanente (ejemplo sencillo, añadir al final de `/etc/rc.local` antes de `exit 0`):
```bash
sudo nano /etc/rc.local
# Añade:
iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
```

### 3. Configura un servidor DHCP para `eth0`
Instala y configura `dnsmasq`:
```bash
sudo apt install dnsmasq
sudo nano /etc/dnsmasq.conf
```
Añade al final:
```
interface=eth0
dhcp-range=192.168.220.2,192.168.220.20,255.255.255.0,24h
```

### 4. Configura IP estática para la interfaz `eth0`
```bash
sudo nano /etc/dhcpcd.conf
```
Añade al final:
```
interface eth0
static ip_address=192.168.220.1/24
nohook wpa_supplicant
```

### 5. Reinicia servicios o la Raspberry Pi
```bash
sudo systemctl restart dnsmasq
sudo systemctl restart dhcpcd
sudo reboot
```

### 6. Prueba la conexión
- Conecta tu dispositivo por cable a la Raspberry Pi
- Debe recibir una IP del rango `192.168.220.x`
- Debe tener acceso a Internet

---

## Notas y buenas prácticas
- **Usuarios avanzados:** Puedes automatizar todo esto con un script bash.
- **Seguridad:** Cambia el password de la Raspberry (`passwd`).  
- **SSH:** Puedes activar SSH así:
  - Si tienes acceso al sistema:  
    ```bash
    sudo systemctl enable ssh
    sudo systemctl start ssh
    ```
  - Si preparas la SD en otro equipo:  
    - Crea un archivo vacío llamado `ssh` en la partición boot.
- **Referencias oficiales:**
  - [Documentación Raspberry Pi – Bridge/NAT](https://www.raspberrypi.com/documentation/computers/configuration.html#using-your-raspberry-pi-as-a-wifi-access-point)
  - [dnsmasq](https://thekelleys.org.uk/dnsmasq/doc.html)

---

## Troubleshooting
- Si tu dispositivo **no recibe IP**, revisa los logs de `dnsmasq` (`/var/log/syslog`).
- Si **no navega**, revisa el firewall y el forwarding (`sysctl` y `iptables`).

---

## Anexo: Cambiar el password y activar SSH
- **Cambiar password**:
  ```bash
  passwd
  ```
- **Activar SSH**:
  ```bash
  sudo systemctl enable ssh
  sudo systemctl start ssh
  ```

---


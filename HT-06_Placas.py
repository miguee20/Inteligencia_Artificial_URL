import sys
import cv2
import numpy as np
import pytesseract
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QFont

DARK_BG      = "#1a1a1a"
PANEL_BG     = "#242424"
GROUP_BG     = "#2c2c2c"
BORDER_COLOR = "#3a3a3a"
ACCENT       = "#e05c00"
TEXT_MAIN    = "#e8e8e8"
TEXT_DIM     = "#888888"
SUCCESS      = "#4caf50"
FAIL         = "#e05c00"

GLOBAL_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_MAIN};
    font-family: 'Courier New', monospace;
    font-size: 12px;
}}
QPushButton {{
    background-color: {PANEL_BG};
    color: {TEXT_MAIN};
    border: 1px solid {BORDER_COLOR};
    border-radius: 2px;
    padding: 8px 20px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    letter-spacing: 1px;
}}
QPushButton:hover {{
    background-color: {ACCENT};
    color: #ffffff;
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: #b34700;
}}
QFrame[frameShape="4"] {{
    background: {BORDER_COLOR};
    border: none;
    max-height: 1px;
}}
"""


def cv2_to_qpixmap(cv_img):
    if cv_img is None:
        return QPixmap()
    if len(cv_img.shape) == 2:
        h, w = cv_img.shape
        qimg = QImage(cv_img.data, w, h, w, QImage.Format_Grayscale8)
    else:
        img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        qimg = QImage(img_rgb.data, w, h, ch * w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


def identificar_placa(image):
    img_result = image.copy()

    gray = cv2.cvtColor(img_result, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.blur(gray, (3, 3))

    canny = cv2.Canny(gray_blur, 150, 200)
    canny = cv2.dilate(canny, None, iterations=1)

    contornos, _ = cv2.findContours(canny, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)[:80]

    placa_texto = "No detectada"

    for c in contornos:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        relAspec = float(w) / h

        if 800 < area < 45000 and 1.2 < relAspec < 6.5:
            placa = gray[y:y+h, x:x+w]
            placa_zoom = cv2.resize(placa, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            _, placa_bin = cv2.threshold(placa_zoom, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

            for img_tess in [placa_zoom, placa_bin]:
                tess_config = '--psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                texto = pytesseract.image_to_string(img_tess, config=tess_config).strip()
                texto_limpio = "".join(filter(str.isalnum, texto)).upper()

                for i in range(len(texto_limpio)):
                    if texto_limpio[i] == 'P':
                        candidato = texto_limpio[i:i+7]
                        if len(candidato) >= 6 and "PNC" not in candidato:
                            if sum(char.isdigit() for char in candidato) >= 1:
                                placa_texto = candidato
                                cv2.rectangle(img_result, (x, y), (x+w, y+h), (0, 200, 80), 3)
                                cv2.putText(img_result, candidato, (x, y - 10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 200, 80), 3)
                                return placa_texto, img_result

    return placa_texto, img_result


class ImageLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(800, 560)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            f"border: 1px solid {BORDER_COLOR};"
            f"background-color: {PANEL_BG};"
            f"color: {TEXT_DIM};"
            f"font-family: 'Courier New', monospace;"
        )
        self.setText("[ sin imagen ]\ncargar archivo para comenzar")

    def set_cv_image(self, cv_img):
        if cv_img is None:
            self.setText("[ sin imagen ]")
            return
        pixmap = cv2_to_qpixmap(cv_img)
        scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)

    def resizeEvent(self, e):
        super().resizeEvent(e)


class ALPRWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALPR // detector de placas")
        self.resize(1200, 860)
        self.setStyleSheet(GLOBAL_STYLE)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(44)
        header.setStyleSheet(
            f"background-color: {PANEL_BG}; border-bottom: 1px solid {BORDER_COLOR};"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        title = QLabel("ALPR")
        title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {ACCENT}; letter-spacing: 3px;"
        )
        sub = QLabel("detector de placas automotrices")
        sub.setStyleSheet(f"font-size: 10px; color: {TEXT_DIM}; letter-spacing: 1px;")
        hl.addWidget(title)
        hl.addWidget(sub)
        hl.addStretch()
        root.addWidget(header)

        toolbar = QWidget()
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(f"background-color: {GROUP_BG}; border-bottom: 1px solid {BORDER_COLOR};")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(16, 0, 16, 0)
        tl.setSpacing(16)

        btn_load = QPushButton("CARGAR IMAGEN")
        btn_load.setFixedWidth(180)
        btn_load.clicked.connect(self._process_image)
        tl.addWidget(btn_load)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {BORDER_COLOR};")
        tl.addWidget(sep)

        lbl_static = QLabel("RESULTADO:")
        lbl_static.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; letter-spacing: 1px;")
        tl.addWidget(lbl_static)

        self.lbl_result = QLabel("---")
        self.lbl_result.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {ACCENT}; letter-spacing: 4px;"
        )
        tl.addWidget(self.lbl_result)
        tl.addStretch()

        self.lbl_status = QLabel("listo")
        self.lbl_status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        tl.addWidget(self.lbl_status)

        root.addWidget(toolbar)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(12, 12, 12, 12)

        self.img_view = ImageLabel()
        bl.addWidget(self.img_view, stretch=1)

        root.addWidget(body, stretch=1)

    def _process_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", "",
            "Imagenes (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return

        image = cv2.imread(path)
        if image is None:
            self.lbl_status.setText("error al leer imagen")
            return

        self.lbl_status.setText(f"procesando: {path.split('/')[-1].split(chr(92))[-1]}")
        QApplication.processEvents()

        h, w = image.shape[:2]
        new_w = 800
        new_h = int((new_w / w) * h)
        image_resized = cv2.resize(image, (new_w, new_h))

        texto_placa, imagen_procesada = identificar_placa(image_resized)

        if texto_placa == "No detectada":
            self.lbl_result.setText("NO DETECTADA")
            self.lbl_result.setStyleSheet(
                f"font-size: 22px; font-weight: bold; color: {FAIL}; letter-spacing: 4px;"
            )
            self.lbl_status.setText("sin coincidencias")
        else:
            self.lbl_result.setText(texto_placa)
            self.lbl_result.setStyleSheet(
                f"font-size: 22px; font-weight: bold; color: {SUCCESS}; letter-spacing: 4px;"
            )
            self.lbl_status.setText("placa encontrada")

        self.img_view.set_cv_image(imagen_procesada)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = ALPRWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
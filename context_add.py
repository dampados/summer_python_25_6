from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QSpinBox, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal

class ContextWindow_add(QDialog):
    sgnl_submitted = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Добавление . . . ")
        self.setGeometry(100, 50, 400, 150)

        self.layout_root = QVBoxLayout()

        self.spin_box = QSpinBox()
        self.text_box = QLineEdit()
        self.button_submit = QPushButton("Добавить!")

        self.spin_box.setMaximum(999999)
        self.spin_box.setValue(50)
        self.text_box.setText("2023-01-31,A,350,7.92,False")

        self.layout_root.addWidget(self.spin_box)
        self.layout_root.addWidget(self.text_box)
        self.layout_root.addWidget(self.button_submit)

        self.button_submit.clicked.connect(self._on_submit)

        self.setLayout(self.layout_root)

    def _on_submit(self):
        self.sgnl_submitted.emit(self.spin_box.value(), self.text_box.text()) 
        self.close()
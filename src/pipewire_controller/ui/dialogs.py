"""UI dialogs for the application."""

from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt


class AboutDialog(QDialog):
    """About dialog showing application information."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("About")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()
        
        info_html = """
        <h1 style='text-align: center;'>PipeWire Controller</h1>
        <h2 style='text-align: center;'>Version 2.0.0</h2>
        <p style='text-align: center;'>A system tray application to control PipeWire</p>
        <p style='text-align: center;'>Author: <b>Andrianos Papamarkou</b></p>
        <p style='text-align: center;'>
            <a href='https://github.com/apapamarkou/pipewire-controller'>Visit on GitHub</a>
        </p>
        """
        
        label = QLabel(info_html)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setOpenExternalLinks(True)
        
        layout.addWidget(label)
        self.setLayout(layout)

    def closeEvent(self, event):
        """Hide instead of close."""
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        """Handle Escape key to hide dialog."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

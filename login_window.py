from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QLabel, QMessageBox)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from google_auth import GoogleAuthManager
import os

class LoginWindow(QMainWindow):
    login_successful = pyqtSignal(object)  # Emit credentials when login is successful

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(100, 100, 400, 500)
        self.auth_manager = GoogleAuthManager()

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Add Google logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("resources/google_logo.png")
        logo_label.setPixmap(logo_pixmap.scaled(200, 200))
        layout.addWidget(logo_label)

        # Welcome text
        welcome_label = QLabel("Welcome to WhissleTranscriber")
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #0f9eef;
                margin: 20px;
            }
        """)
        layout.addWidget(welcome_label)

        # Login button
        self.login_button = QPushButton("Sign in with Google")
        self.login_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                padding: 15px;
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 5px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        self.login_button.clicked.connect(self.handle_login)
        layout.addWidget(self.login_button)

    def handle_login(self):
        try:
            # Show information about test-only access
            QMessageBox.information(
                self,
                "Test Mode",
                "This app is currently in testing mode.\n"
                "Only authorized test users can sign in.\n"
                "Please contact the developer for access."
            )
            
            creds = self.auth_manager.get_credentials()
            if creds and creds.valid:
                user_info = self.auth_manager.get_user_info()
                QMessageBox.information(
                    self,
                    "Login Successful",
                    f"Welcome {user_info.get('name')}!"
                )
                self.login_successful.emit(creds)
                self.close()
            else:
                QMessageBox.warning(
                    self,
                    "Login Failed",
                    "Could not authenticate with Google.\n"
                    "Make sure you are an authorized test user."
                )
        except Exception as e:
            error_msg = str(e)
            if "invalid_client" in error_msg:
                QMessageBox.critical(
                    self,
                    "Configuration Error",
                    "OAuth client configuration is invalid.\n"
                    "Please check credentials.json file."
                )
            elif "access_denied" in error_msg:
                QMessageBox.warning(
                    self,
                    "Access Denied",
                    "You are not authorized to use this application.\n"
                    "Please contact the developer for access."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred: {error_msg}"
                ) 
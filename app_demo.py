from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QWidget, QTextEdit, QLabel, QMenu, QRadioButton, QCheckBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QPoint
from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QActionGroup, QIcon
import socketio
import speech_recognition as sr
import sys
import queue
import logging
import threading
from datetime import datetime
import pyaudio
import wave
import io
import subprocess

class AudioRecorder(QThread):
    chunk_ready = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Match web implementation exactly
        self.sample_rate = 16000  # Changed to match desiredSampRate from web
        self.chunk_duration = 0.8  # 800ms chunks
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.is_recording = False
        self.audio = pyaudio.PyAudio()

    def run(self):
        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_recording = True
            
            while self.is_recording:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                print(f"Recording chunk of size: {len(data)} bytes")
                self.chunk_ready.emit(data)
                
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"Audio recording error: {str(e)}")
            self.error_occurred.emit(str(e))
        finally:
            self.is_recording = False

    def stop(self):
        self.is_recording = False
        self.wait()

class WebSocketThread(QThread):
    transcription_received = pyqtSignal(str, bool)
    connection_status = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.setup_socket_handlers()
        self.audio_queue = queue.Queue()
        
    def setup_socket_handlers(self):
        @self.sio.on('connect')
        def on_connect():
            print("Socket connected successfully")
            self.connection_status.emit("Connected to server")

        @self.sio.on('disconnect')
        def on_disconnect():
            print("Socket disconnected")
            self.connection_status.emit("Disconnected from server")

        @self.sio.on('connect_error')
        def on_connect_error(data):
            print(f"Connection error: {data}")
            self.error_occurred.emit(f"Connection error: {data}")

        @self.sio.on('transcript')
        def on_transcript(data):
            print("=================== TRANSCRIPT RECEIVED ===================")
            print(f"Raw transcript data: {data}")
            if isinstance(data, dict) and 'transcript' in data:
                transcript = data['transcript']
                is_final = data.get('is_final', False)
                print(f"Transcript: {transcript}")
                print(f"Is Final: {is_final}")
                self.transcription_received.emit(transcript, is_final)
            print("======================================================")

        @self.sio.on('*')
        def catch_all(event, data):
            print(f"Caught event: {event} with data: {data}")

    def connect_to_server(self, model_name):
        try:
            if self.sio.connected:
                self.sio.disconnect()
            
            print(f"Connecting with model: {model_name}")
            
            # Create new socket with query parameter exactly like web:
            # const socketio = io('https://api.whissle.ai', { query: `model_name=${option}` });
            self.sio = socketio.Client()
            self.setup_socket_handlers()
            
            # Create connection URL with query parameter
            url = f'https://api.whissle.ai/socket.io/?model_name={model_name}'
            self.sio.connect(
                url,
                transports=['websocket']
            )
            
        except Exception as e:
            print(f"Connection error: {str(e)}")
            self.error_occurred.emit(f"Connection error: {str(e)}")

    def add_audio_chunk(self, chunk):
        if self.sio.connected:
            try:
                print(f"Sending audio chunk of size {len(chunk)}")
                # Send raw binary data like web implementation
                self.sio.emit('audio_in', chunk)
            except Exception as e:
                print(f"Error sending audio: {str(e)}")
                self.error_occurred.emit(f"Error sending audio: {str(e)}")

    def handle_emit_callback(self, *args):
        print(f"Audio chunk emit callback received: {args}")

    def disconnect_from_server(self):
        if self.sio.connected:
            self.sio.disconnect()

class TranscriptionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Speech Transcription")
        
        # Initialize instance variables first
        self.final_transcript = ""
        self.last_chunk_time = None
        self.is_connecting = False
        
        # Initialize audio recorder and websocket early
        self.audio_recorder = AudioRecorder()
        self.websocket_thread = WebSocketThread()
        
        # Create transcript display early
        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        self.transcript_display.setAcceptRichText(True)
        self.transcript_display.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 3px solid #0f9eef;
                border-radius: 10px;
                padding: 20px;
                font-family: Arial;
                font-size: 20px;
                line-height: 1.8;
            }
        """)
        
        # Set application icon - add error handling
        try:
            icon = QIcon("logo.png")
            self.setWindowIcon(icon)
            QApplication.setWindowIcon(icon)
        except Exception as e:
            print(f"Warning: Could not load logo.png: {e}")
        
        self.setGeometry(100, 100, 800, 800)  # Increased height from 600 to 800
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(20)  # Increase spacing between major sections

        # Create model selector header with more compact styling
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)  # Reduce spacing between header elements
        label = QLabel("Choose a model:")
        label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
            color: #333;
        """)
        header_layout.addWidget(label)

        # Create more compact radio button group for models
        self.models = [
            "speech-tagger_en_ner-emotion",
            "hindi_adapter-ai4bharat",
            "indoaryan-adapter-ai4bharat2",
            "speech-tagger_en_slurp-iot"
        ]
        
        self.model_buttons = []
        models_layout = QVBoxLayout()
        models_layout.setSpacing(2)  # Reduce spacing between radio buttons
        
        for model in self.models:
            radio = QRadioButton(model)
            radio.setStyleSheet("""
                QRadioButton {
                    font-size: 16px;
                    padding: 8px;
                    border: 2px solid transparent;
                    border-radius: 6px;
                    background-color: #e8f0fe;
                    color: #0f9eef;
                    font-weight: bold;
                    margin: 2px;
                }
                QRadioButton:hover {
                    background-color: #d0e3fc;
                }
                QRadioButton:checked {
                    border-color: #0f9eef;
                    background-color: #d0e3fc;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 2px solid #0f9eef;
                    margin-right: 8px;
                }
                QRadioButton::indicator:checked {
                    background-color: #0f9eef;
                    border: 2px solid #0f9eef;
                }
            """)
            radio.toggled.connect(lambda checked, m=model: self.on_model_selected(m) if checked else None)
            models_layout.addWidget(radio)
            self.model_buttons.append(radio)
        
        # Set first model as checked by default
        self.model_buttons[0].setChecked(True)
        
        # Add models layout to header with some margin control
        header_layout.addLayout(models_layout)
        header_layout.addSpacing(10)  # Add space after model selection
        layout.addLayout(header_layout)

        # Make transcript display take more vertical space
        self.transcript_display.setMinimumHeight(400)  # Set minimum height
        self.transcript_display.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 3px solid #0f9eef;
                border-radius: 10px;
                padding: 20px;
                font-family: Arial;
                font-size: 20px;
                line-height: 1.8;
                min-height: 400px;
            }
        """)
        layout.addWidget(self.transcript_display, stretch=1)  # Add stretch factor

        # Make status and latency labels more compact
        status_layout = QVBoxLayout()
        status_layout.setSpacing(2)
        
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("font-size: 16px; color: #555; margin: 2px;")
        self.latency_label = QLabel("Latency: 0ms")
        self.latency_label.setStyleSheet("font-size: 16px; color: #555; margin: 2px;")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.latency_label)

        # Add checkbox for external typing
        self.type_externally_checkbox = QCheckBox("Type transcriptions to focused window")
        self.type_externally_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 16px;
                color: #333;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #0f9eef;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #0f9eef;
                border: 2px solid #0f9eef;
                image: url(checkmark.png);
            }
        """)
        status_layout.addWidget(self.type_externally_checkbox)
        
        layout.addLayout(status_layout)

        # Make buttons more compact but still prominent
        button_layout = QVBoxLayout()
        button_layout.setSpacing(5)
        
        self.start_button = QPushButton("Start Recording")
        self.stop_button = QPushButton("Stop Recording")
        
        button_style = """
            QPushButton {
                font-size: 18px;
                padding: 12px 25px;
                margin: 5px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                color: white;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        
        self.start_button.setStyleSheet(button_style + "QPushButton { background-color: #4caf50; }")
        self.stop_button.setStyleSheet(button_style + "QPushButton { background-color: #f44336; }")
        
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        # Connect signals
        self.setup_connections()
        
        # Setup text formats for different token types
        self.setup_text_formats()

    def setup_text_formats(self):
        # Define colors directly as hex strings
        self.text_formats = {
            'EMOTION_': self.create_format('#e91e63', 24),  # Pink
            'NER_': self.create_format('#2196f3', 24),      # Blue
            'END': self.create_format('#4caf50', 24),       # Green
            'INTENT_': self.create_format('#ff9800', 24),   # Orange
            'AGE_': self.create_format('#9c27b0', 24),      # Purple
            'DIALECT_': self.create_format('#795548', 24),  # Brown
            'GENDER_': self.create_format('#009688', 24),   # Teal
            'ENTITY_': self.create_format('#673ab7', 24),   # Deep Purple
            'regular': self.create_format('#000000', 20)    # Black
        }

    def create_format(self, color, size):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFontWeight(QFont.Weight.Bold)
        fmt.setFontPointSize(size)
        return fmt

    def colorize_text(self, text):
        words = text.split()
        result = []
        for word in words:
            format_key = 'regular'
            for key in self.text_formats.keys():
                if key != 'regular' and word.startswith(key):
                    format_key = key
                    break
            result.append((word, format_key))
        return result

    def setup_connections(self):
        self.start_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        
        self.audio_recorder.chunk_ready.connect(self.websocket_thread.add_audio_chunk)
        self.audio_recorder.error_occurred.connect(self.handle_error)
        
        self.websocket_thread.transcription_received.connect(self.update_transcript)
        self.websocket_thread.connection_status.connect(self.update_status)
        self.websocket_thread.error_occurred.connect(self.handle_error)

    def on_model_selected(self, model_name):
        """Handle model selection"""
        print(f"Model selected: {model_name}")
        
        # Clear the transcript display and stored transcript
        self.final_transcript = ""
        self.transcript_display.clear()
        
        # If currently connected, stop and restart with new model
        if self.websocket_thread.sio.connected:
            self.stop_recording()
            self.start_recording()

    def start_recording(self):
        if self.is_connecting:
            return
            
        try:
            self.is_connecting = True
            self.start_button.setEnabled(False)
            self.status_label.setText("Status: Connecting...")
            
            # Clear previous transcript
            self.final_transcript = ""
            self.transcript_display.clear()
            
            # Get selected model from radio buttons
            model_name = next(button.text() for button in self.model_buttons if button.isChecked())
            print(f"Starting recording with model: {model_name}")
            self.websocket_thread.connect_to_server(model_name)
            
            # Start a timer to check connection status
            QTimer.singleShot(100, self.check_connection_status)

        except Exception as e:
            self.is_connecting = False
            self.handle_error(str(e))

    def check_connection_status(self):
        if not self.websocket_thread.sio.connected:
            # If not connected yet, check again in 100ms
            if self.is_connecting:
                QTimer.singleShot(100, self.check_connection_status)
            return
            
        # Connection successful, start recording
        self.is_connecting = False
        self.stop_button.setEnabled(True)
        self.audio_recorder.start()

    def stop_recording(self):
        self.is_connecting = False
        self.audio_recorder.stop()
        self.websocket_thread.disconnect_from_server()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Status: Stopped")

    def update_transcript(self, text, is_final):
        print(f"Updating display - Text: '{text}', Is Final: {is_final}")
        
        # Format the current text
        formatted_text = ""
        plain_text = ""  # Store plain text version for external typing
        
        for word, format_key in self.colorize_text(text):
            # Get the color from the format
            if format_key != 'regular':
                color = self.text_formats[format_key].foreground().color().name()
                formatted_text += f'<span style="color: {color}; font-weight: bold; font-size: 24px">{word}</span> '
            else:
                formatted_text += f'<span style="color: black; font-size: 20px">{word}</span> '
            plain_text += word + " "
        
        if is_final:
            self.final_transcript += formatted_text + "<br>"
            
            # If external typing is enabled, type the text in the focused window
            if self.type_externally_checkbox.isChecked():
                try:
                    # Properly encode the text for AppleScript, including Unicode characters
                    text_to_type = plain_text.strip()
                    
                    # Use UTF-8 text input method for better Unicode support
                    apple_script = f'''
                    tell application "System Events"
                        set the clipboard to "{text_to_type} "
                        keystroke "v" using command down
                    end tell
                    '''
                    
                    # Execute the AppleScript
                    subprocess.run(['osascript', '-e', apple_script], text=True, encoding='utf-8')
                    
                except Exception as e:
                    print(f"Error typing externally: {e}")
        
        # Display both final and interim results in our window
        display_text = self.final_transcript
        if not is_final:
            display_text += "<br>" + formatted_text
        
        # Update the display with HTML formatting
        self.transcript_display.setHtml(display_text)
        
        # Scroll to bottom
        scrollbar = self.transcript_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_status(self, status):
        self.status_label.setText(f"Status: {status}")

    def handle_error(self, error_message):
        self.is_connecting = False
        self.status_label.setText(f"Error: {error_message}")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.audio_recorder.stop()
        if self.websocket_thread.sio.connected:
            self.websocket_thread.disconnect_from_server()

    def closeEvent(self, event):
        self.stop_recording()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set macOS-specific style
    app.setStyle('Fusion')
    
    window = TranscriptionApp()
    window.show()
    sys.exit(app.exec())

from setuptools import setup
import os
import subprocess
import site
import sys

# Add site-packages to path to help py2app find packages
site_packages = site.getsitepackages()[0]
sys.path.insert(0, site_packages)

# Find libffi path using homebrew
try:
    libffi_path = subprocess.check_output(['brew', '--prefix', 'libffi']).decode().strip()
except:
    libffi_path = '/usr/local/opt/libffi'  # Default Homebrew path

# Find OpenSSL path using homebrew
try:
    openssl_path = subprocess.check_output(['brew', '--prefix', 'openssl@3']).decode().strip()
except:
    openssl_path = '/usr/local/opt/openssl@3'  # Default Homebrew path

APP = ['app_demo.py']
DATA_FILES = [
    ('', ['logo.png'])  # Removed google_client_secret.json
]

OPTIONS = {
    'argv_emulation': True,
    'packages': [
        'PyQt6',
        'socketio',
        'pyaudio',
        'websocket',
        'engineio',
        'pkg_resources',
        'speech_recognition',
    ],
    'includes': [
        'packaging',
        'packaging.version',
        'packaging.specifiers',
        'packaging.requirements',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
    ],
    'extra_scripts': [],
    'site_packages': True,
    'excludes': ['matplotlib', 'google', 'google.*', 'googleapiclient'],
    'frameworks': [
        os.path.join(libffi_path, 'lib/libffi.8.dylib'),
        os.path.join(openssl_path, 'lib/libssl.3.dylib'),
        os.path.join(openssl_path, 'lib/libcrypto.3.dylib'),
    ],
    'dylib_excludes': ['libffi.8.dylib', 'libssl.3.dylib', 'libcrypto.3.dylib'],
    'iconfile': 'logo.png',
    'plist': {
        'CFBundleIconFile': 'logo.png',
        'CFBundleName': 'WhissleTranscriber',
        'CFBundleDisplayName': 'Whissle Transcriber',
        'CFBundleIdentifier': 'ai.whissle.transcriber',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '10.10',
        'NSMicrophoneUsageDescription': 'This app needs access to the microphone for speech recognition.',
    }
}

setup(
    name="WhissleTranscriber",
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'PyQt6==6.4.0',
        'python-socketio==5.7.2',
        'pyaudio==0.2.13',
        'websocket-client==1.6.1',
        'SpeechRecognition==3.8.1',
    ],
) 
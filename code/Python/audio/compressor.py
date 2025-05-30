import sys
import numpy as np
import sounddevice as sd
import soundfile as sf
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QSlider, QPushButton, QHBoxLayout, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor

class SSLBusCompressor:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.threshold_db = -10.0
        self.ratio = 4.0
        self.attack_ms = 10.0
        self.release_ms = 300.0
        self.makeup_gain_db = 0.0
        self.envelope = 0.0

    def set_params(self, threshold_db, ratio, attack_ms, release_ms, makeup_gain_db):
        self.threshold_db = threshold_db
        self.threshold = 10 ** (threshold_db / 20.0)
        self.ratio = ratio
        self.attack_coeff = np.exp(-1.0 / (0.001 * attack_ms * self.sample_rate))
        self.release_coeff = np.exp(-1.0 / (0.001 * release_ms * self.sample_rate))
        self.makeup_gain_db = makeup_gain_db
        self.makeup_gain = 10 ** (makeup_gain_db / 20.0)
        self.envelope = 0.0  # reset envelope for new processing

    def process(self, input_signal):
        output = np.zeros_like(input_signal)
        for i, x in enumerate(input_signal):
            rectified = abs(x)
            if rectified > self.envelope:
                self.envelope = self.attack_coeff * (self.envelope - rectified) + rectified
            else:
                self.envelope = self.release_coeff * (self.envelope - rectified) + rectified

            if self.envelope > self.threshold:
                gain_reduction_db = (20 * np.log10(self.envelope / self.threshold)) * (1.0 - 1.0 / self.ratio)
                gain = 10 ** (-gain_reduction_db / 20.0)
            else:
                gain = 1.0

            output[i] = x * gain * self.makeup_gain
        return output

class VUMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0.0  # 0.0 to 1.0

    def set_level(self, level):
        self.level = max(0.0, min(1.0, level))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        # Background
        painter.fillRect(rect, QColor(30, 30, 30))
        # VU bar
        bar_height = int(rect.height() * self.level)
        painter.fillRect(0, rect.height() - bar_height, rect.width(), bar_height, QColor(0, 220, 0))

class CompressorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SSL Bus Compressor (Python)")

        self.comp = SSLBusCompressor()

        layout = QVBoxLayout()

        # Controls and sliders
        self.threshold_slider = self.create_slider(-60, 0, -10, "Threshold (dB)")
        self.ratio_slider = self.create_slider(1, 20, 4, "Ratio")
        self.attack_slider = self.create_slider(1, 100, 10, "Attack (ms)")
        self.release_slider = self.create_slider(10, 1000, 300, "Release (ms)")
        self.makeup_slider = self.create_slider(-12, 12, 0, "Makeup Gain (dB)")

        layout.addLayout(self.threshold_slider['layout'])
        layout.addLayout(self.ratio_slider['layout'])
        layout.addLayout(self.attack_slider['layout'])
        layout.addLayout(self.release_slider['layout'])
        layout.addLayout(self.makeup_slider['layout'])

        # Buttons
        self.load_button = QPushButton("Load WAV File")
        self.load_button.clicked.connect(self.load_file)
        layout.addWidget(self.load_button)

        self.play_button = QPushButton("Play Processed Audio")
        self.play_button.clicked.connect(self.play_processed_audio)
        self.play_button.setEnabled(False)
        layout.addWidget(self.play_button)

        # File info label
        self.file_info_label = QLabel("No file loaded")
        layout.addWidget(self.file_info_label)

        # VU Meter
        self.vu_meter = VUMeter()
        self.vu_meter.setFixedHeight(30)
        layout.addWidget(self.vu_meter)

        self.setLayout(layout)

        self.audio_data = None
        self.processed_data = None
        self.sample_rate = 44100

        # VU Timer
        self.vu_timer = QTimer()
        self.vu_timer.setInterval(50)  # update every 50 ms
        self.vu_timer.timeout.connect(self.update_vu)

    def create_slider(self, min_val, max_val, init_val, label_text):
        layout = QHBoxLayout()
        label = QLabel(f"{label_text}: {init_val}")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(init_val)
        slider.setTickInterval(max(1, (max_val - min_val) // 10))
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.valueChanged.connect(lambda val, l=label, t=label_text: l.setText(f"{t}: {val}"))
        layout.addWidget(label)
        layout.addWidget(slider)
        return {'layout': layout, 'slider': slider, 'label': label}

    def load_file(self):
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Open WAV file", "", "WAV Files (*.wav)")
        if file_path:
            self.audio_data, self.sample_rate = sf.read(file_path)
            if self.audio_data.ndim > 1:
                # Convert to mono by averaging channels
                self.audio_data = self.audio_data.mean(axis=1)
            self.file_info_label.setText(f"Loaded: {file_path} | Sample Rate: {self.sample_rate} Hz")
            self.process_audio()
            self.play_button.setEnabled(True)

    def process_audio(self):
        self.comp.sample_rate = self.sample_rate
        self.comp.set_params(
            self.threshold_slider['slider'].value(),
            self.ratio_slider['slider'].value(),
            self.attack_slider['slider'].value(),
            self.release_slider['slider'].value(),
            self.makeup_slider['slider'].value()
        )
        self.processed_data = self.comp.process(self.audio_data)

    def play_processed_audio(self):
        if self.processed_data is not None:
            sd.play(self.processed_data, self.sample_rate)
            self.vu_timer.start()
            # Stop VU updates after playback
            duration_ms = int(len(self.processed_data) / self.sample_rate * 1000)
            QTimer.singleShot(duration_ms, self.vu_timer.stop)

    def update_vu(self):
        if self.processed_data is not None and sd.get_stream() is not None:
            # Get current playback position
            stream_time = sd.get_stream().time
            idx = int(stream_time * self.sample_rate)
            window = self.processed_data[idx:idx+1024]
            if len(window) > 0:
                rms = np.sqrt(np.mean(window**2))
                vu_level = min(rms / 0.5, 1.0)  # normalize for display
                self.vu_meter.set_level(vu_level)
            else:
                self.vu_meter.set_level(0.0)
        else:
            self.vu_meter.set_level(0.0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CompressorGUI()
    window.resize(500, 350)
    window.show()
    sys.exit(app.exec())
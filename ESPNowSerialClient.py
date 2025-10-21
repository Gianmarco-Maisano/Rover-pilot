import serial
import json
import threading
import time

class ESPNowSerialClient:
    def __init__(self, port: str, baudrate: int = 115200):
        self.ser = serial.Serial(port, baudrate, timeout=0.1)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self.callbacks = []

    def start(self):
        self._stop_event.clear()
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=1.0)
        self.ser.close()

    def _read_loop(self):
        buffer = ""
        while not self._stop_event.is_set():
            if self.ser.in_waiting:
                buffer += self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        self._handle_line(line)
            time.sleep(0.01)

    def _handle_line(self, line: str):
        try:
            data = json.loads(line)
            for cb in self.callbacks:
                cb(data)
        except json.JSONDecodeError:
            print("Invalid JSON:", line)

    def send(self, state):
        payload = {
            "linear": round(state.linear, 2),
            "angular": round(state.angular, 2),
            "b1": state.b1,
            "b2": state.b2,
            "sw1": state.sw1,
            "sw2": state.sw2,
            "sw3": state.sw3,
            "sw4": state.sw4,
        }


    def add_callback(self, callback):
        self.callbacks.append(callback)

from __future__ import annotations

# robot_controller.py

import time
import json
import threading
from dataclasses import dataclass, field
from typing import Optional, Tuple

import requests
from ping3 import ping
from websocket import WebSocket
from websocket._exceptions import WebSocketConnectionClosedException

from ESPNowSerialClient import ESPNowSerialClient

# ================== CONFIG ==================
HTTP_TIMEOUT_S = 3
PING_TIMEOUT_S = 5.0
SEND_INTERVAL_S = 0.1     # 10 Hz max
KEEPALIVE_S = 5.0          # 5 s
WS_PORT = 81               # websocket
WS_PATH = "/"
# ============================================

linear_speed_value = 0.0
angular_speed_value = 0.0

Device_connected = False
robot_ip = "0.0.0.0"
Lora = False
WSocket = False

stop_event = threading.Event()
last_command_time = 0.0
last_command_data = None

sw1_state = False
sw2_state = False
sw3_state = False
sw4_state = False

# ============================================
    
@dataclass
class CommandState:
    linear: float = 0.0
    angular: float = 0.0
    b1: bool = False
    b2: bool = False
    sw1: bool = False
    sw2: bool = False
    sw3: bool = False
    sw4: bool = False


@dataclass
class _Client:
    use_ws: bool = False
    _ws: Optional[WebSocket] = field(default=None, init=False)
    _connected: bool = field(default=False, init=False)
    _stop_ev: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)
    _pending: CommandState = field(default_factory=CommandState, init=False)
    _last_sent: Optional[CommandState] = field(default=None, init=False)
    _last_send_ts: float = field(default=0.0, init=False)
    _last_b1: bool = field(default=False, init=False)
    _last_b2: bool = field(default=False, init=False)
    use_espnow: bool = False
    _esp_serial: Optional[ESPNowSerialClient] = field(default=None, init=False)


    # ---------- publlic ----------
    def start(self):
        self._stop_ev.clear()
        if self.use_ws:
            self._ensure_ws()
        self._thread = threading.Thread(target=self._tx_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_ev.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._close_ws()

    def ping_robot(self) -> bool:
        global Device_connected, robot_ip
        try:
            rtt = ping(robot_ip, timeout=PING_TIMEOUT_S)
            self._connected = (rtt is not None and rtt <= 1.0)
        except Exception:
            self._connected = False
        Device_connected = self._connected
        return self._connected

    def send(self, state: CommandState):
        self._pending = state
        if (state.b1 and not self._last_b1) or (state.b2 and not self._last_b2):
            self._send_once(state)
        self._last_b1 = state.b1
        self._last_b2 = state.b2

    def get_status(self) -> Tuple[Optional[int], Optional[float], Optional[str]]:
        if not self._connected:
            return None, None, None
        try:
            url = f"http://{robot_ip}/response_data"
            r = requests.get(url, timeout=HTTP_TIMEOUT_S)
            if r.status_code == 200:
                js = r.json()
                if js.get("status") == "success":
                    return js.get("wifiStrength"), js.get("voltage"), "success"
        except Exception:
            pass
        return None, None, None

# ---------- internal ----------
    def _tx_loop(self):
        while not self._stop_ev.is_set():
            self.ping_robot()
            now = time.time()
            changed = (self._last_sent != self._pending)
            keepalive = (now - self._last_send_ts) >= KEEPALIVE_S
            if changed or keepalive:
                self._send_once(self._pending)
            time.sleep(SEND_INTERVAL_S)

    def _payload(self, s: CommandState) -> str:
        return json.dumps({
            "linear": round(s.linear, 2),
            "angular": round(s.angular, 2),
            "b1": bool(s.b1),
            "b2": bool(s.b2),
            "sw1": bool(s.sw1),
            "sw2": bool(s.sw2),
            "sw3": bool(s.sw3),
            "sw4": bool(s.sw4),
        }, separators=(",", ":"))

    def _send_once(self, state: CommandState):
        if self.use_espnow and self._esp_serial:
            self._esp_serial.send(state)
            self._last_sent = CommandState(**state.__dict__)
            self._last_send_ts = time.time()
        elif self.use_ws:
            if self._ensure_ws():
                self._ws_send(state)
            else:
                self._http_send(state)
        else:
            self._http_send(state)


    def _http_send(self, state: CommandState):
        if not self._connected:
            return
        try:
            url = f"http://{robot_ip}/cmd"
            headers = {"Content-Type": "application/json"}
            payload = self._payload(state)
            r = requests.post(url, data=payload, headers=headers, timeout=HTTP_TIMEOUT_S)
            print(f"HTTP {r.status_code} {r.text[:80]}")
            self._last_sent = CommandState(**state.__dict__)
            self._last_send_ts = time.time()
        except requests.exceptions.RequestException:
            pass

    def _ensure_ws(self) -> bool:
        if not self.use_ws:
            return False
        if WebSocket is None:
            return False
        if self._ws:
            return True
        try:
            self._ws = WebSocket()
            self._ws.connect(f"ws://{robot_ip}:{WS_PORT}{WS_PATH}", timeout=HTTP_TIMEOUT_S)
            return True
        except Exception:
            self._ws = None
            return False

    def _ws_send(self, state: CommandState):
        if not self._ws and not self._ensure_ws():
            return
        try:
            payload = self._payload(state)
            self._ws.send(payload)
            self._last_sent = CommandState(**state.__dict__)
            self._last_send_ts = time.time()
        except (WebSocketConnectionClosedException, OSError) as e:
            print(f"⚠️ WS send failed: {e}")
            self._close_ws()

    def _close_ws(self):
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        self._ws = None

_client = _Client(use_ws=False)

# ========= API =========

def lora_connection():
    global Lora
    Lora = True

def WS_connection():
    global WSocket, _client
    _client.use_ws = True
    WSocket = True

def espnow_connection(port: str = "COM3", baudrate: int = 115200):
    global _client
    _client.use_espnow = True
    _client._esp_serial = ESPNowSerialClient(port, baudrate)
    _client._esp_serial.start()


def set_robot_ip(ip: str):
    global robot_ip
    robot_ip = ip

def check_connection(ip: Optional[str] = None) -> bool:
    if ip:
        set_robot_ip(ip)
    return _client.ping_robot()

def send_robot_commands(
    linear_speed: float,
    angular_speed: float,
    *,
    b1: bool = False,
    b2: bool = False,
    sw1: Optional[bool] = None,
    sw2: Optional[bool] = None,
    sw3: Optional[bool] = None,
    sw4: Optional[bool] = None,
):

    global linear_speed_value, angular_speed_value
    global sw1_state, sw2_state, sw3_state, sw4_state

    linear_speed_value = round(float(linear_speed), 2)
    angular_speed_value = round(float(angular_speed), 2)

    if sw1 is not None: sw1_state = bool(sw1)
    if sw2 is not None: sw2_state = bool(sw2)
    if sw3 is not None: sw3_state = bool(sw3)
    if sw4 is not None: sw4_state = bool(sw4)

    state = CommandState(
        linear=linear_speed_value,
        angular=angular_speed_value,
        b1=bool(b1),
        b2=bool(b2),
        sw1=sw1_state,
        sw2=sw2_state,
        sw3=sw3_state,
        sw4=sw4_state,
    )
    _client.send(state)

def get_data(ip: Optional[str] = None):
    if ip:
        set_robot_ip(ip)
    return _client.get_status()

# ====== Thread/ client ======

_stop_flag = False
def start_update_thread(ip: str):
    global _stop_flag
    _stop_flag = False
    set_robot_ip(ip)
    _client.start()

def stop_update_thread():
    global _stop_flag
    _stop_flag = True
    _client.stop()

# ====== GUI Helpers  ======

def press_btn1():
    send_robot_commands(linear_speed_value, angular_speed_value, b1=True)

def press_btn2():
    send_robot_commands(linear_speed_value, angular_speed_value, b2=True)

def toggle_sw1() -> bool:
    global sw1_state
    sw1_state = not sw1_state
    send_robot_commands(linear_speed_value, angular_speed_value, sw1=sw1_state)
    return sw1_state

def toggle_sw2() -> bool:
    global sw2_state
    sw2_state = not sw2_state
    send_robot_commands(linear_speed_value, angular_speed_value, sw2=sw2_state)
    return sw2_state

def toggle_sw3() -> bool:
    global sw3_state
    sw3_state = not sw3_state
    send_robot_commands(linear_speed_value, angular_speed_value, sw3=sw3_state)
    return sw3_state

def toggle_sw4() -> bool:
    global sw4_state
    sw4_state = not sw4_state
    send_robot_commands(linear_speed_value, angular_speed_value, sw4=sw4_state)
    return sw4_state

def _set_sw(var_or_bool) -> bool:
    return bool(var_or_bool.get()) if hasattr(var_or_bool, "get") else bool(var_or_bool)

def set_sw1(var_or_bool, label_widget=None):
    global sw1_state
    val = _set_sw(var_or_bool)
    if val != sw1_state:
        sw1_state = val
        send_robot_commands(linear_speed_value, angular_speed_value, sw1=sw1_state)
        try:
            if label_widget:
                label_widget.configure(state="normal")
                label_widget.insert("end", f"\n sw1 {'ON' if sw1_state else 'OFF'}")
                label_widget.configure(state="disabled")
        except Exception:
            pass

def set_sw2(var_or_bool, label_widget=None):
    global sw2_state
    val = _set_sw(var_or_bool)
    if val != sw2_state:
        sw2_state = val
        send_robot_commands(linear_speed_value, angular_speed_value, sw2=sw2_state)
        try:
            if label_widget:
                label_widget.configure(state="normal")
                label_widget.insert("end", f"\n sw2 {'ON' if sw2_state else 'OFF'}")
                label_widget.configure(state="disabled")
        except Exception:
            pass

def set_sw3(var_or_bool, label_widget=None):
    global sw3_state
    val = _set_sw(var_or_bool)
    if val != sw3_state:
        sw3_state = val
        send_robot_commands(linear_speed_value, angular_speed_value, sw3=sw3_state)
        try:
            if label_widget:
                label_widget.configure(state="normal")
                label_widget.insert("end", f"\n sw3 {'ON' if sw3_state else 'OFF'}")
                label_widget.configure(state="disabled")
        except Exception:
            pass

def set_sw4(var_or_bool, label_widget=None):
    global sw4_state
    val = _set_sw(var_or_bool)
    if val != sw4_state:
        sw4_state = val
        send_robot_commands(linear_speed_value, angular_speed_value, sw4=sw4_state)
        try:
            if label_widget:
                label_widget.configure(state="normal")
                label_widget.insert("end", f"\n sw4 {'ON' if sw4_state else 'OFF'}")
                label_widget.configure(state="disabled")
        except Exception:
            pass

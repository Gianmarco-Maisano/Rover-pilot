import threading
import time
from pynput import keyboard
from evdev import InputDevice, ecodes, list_devices
from robot_controller import *
import tkinter
import select


# =============================
# THREAD DATA
# =============================
class TeleopThreadData:
    def __init__(self):
        self.running = False
        self.stop_thread = False

class JoypadThreadData:
    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()
        self.running = False

teleop_thread_data = TeleopThreadData()
joypad_thread_data = JoypadThreadData()

teleop_thread = None
JOYPAD_AVAILABLE = False

linear_speed_set = 0.0
angular_speed_set = 0.0


# =============================
# JOYPAD HANDLING
# =============================
#python3 -m evdev.evtest

def check_joypad_connection(verbose=False):
    global JOYPAD_AVAILABLE
    devices = [InputDevice(path) for path in list_devices()]
    gamepads = [
        dev for dev in devices
        if any(x in dev.name.lower() for x in ["xbox", "gamepad", "controller", "joystick", "pad"])
    ]
    if gamepads:
        if verbose:
            print(f"✅ joypad: {gamepads[0].name} ({gamepads[0].path})")
        return gamepads[0]
    else:
        return False

#slider = 0.0
#btn_a = btn_b = btn_x = btn_y = 0

def joypad_teleop_thread(mod=None):
    global JOYPAD_AVAILABLE

    if not mod or mod not in (1, 2, 3):
        mod = 1

    prev_lin = 0.0
    prev_ang = 0.0
    linear = 0.0
    angular = 0.0
    deadzone = 0.1
    lt = rt = ry = rx = lx = ly = slider = 0.0
    btn_a = btn_b = btn_x = btn_y = 0
    SensCoeff = 1.4

    device = check_joypad_connection(verbose=True)
    JOYPAD_AVAILABLE = bool(device)

    print(f"🎮 Joypad thread started (mod {mod}), device={device.name if device else None}")
    try:
        while not joypad_thread_data.stop_event.is_set():
            if not device:
                device = check_joypad_connection(verbose=False)
                if device:
                    print(f"✅ Joypad connected: {device.name} ({device.path})")
                    JOYPAD_AVAILABLE = True
                else:
                    JOYPAD_AVAILABLE = False
                    time.sleep(0.5)
                    continue

            try:
                r, w, x = select.select([device.fd], [], [], 0.5)
            except Exception as e:
                print(f"[JOY] select error: {e}")
                time.sleep(0.2)
                continue

            if not r:
                continue

            try:
                for event in device.read(): 
                    if joypad_thread_data.stop_event.is_set():
                        break

                    if event.type == ecodes.EV_ABS:
                        val = 0.0
                        if event.code in (ecodes.ABS_X, ecodes.ABS_Y, ecodes.ABS_RX, ecodes.ABS_RY):
                            val = event.value / (32767.0 * SensCoeff) if event.value <= 32767 else 0.0
                        elif event.code in (ecodes.ABS_Z, ecodes.ABS_RZ):
                            val = event.value / 255.0

                        if event.code == ecodes.ABS_RY:
                            ry = -val
                        elif event.code == ecodes.ABS_RX:
                            rx = val
                        elif event.code == ecodes.ABS_Y:
                            ly = -val
                        elif event.code == ecodes.ABS_X:
                            lx = val
                        elif event.code == ecodes.ABS_Z:
                            lt = val
                        elif event.code == ecodes.ABS_RZ:
                            rt = val
                        else:
                            continue

                        if mod == 1:
                            linear = ry
                            angular = rx
                            if lt > 0.2:
                                linear = 0
                                angular = -lt
                            if rt > 0.2:
                                linear = 0
                                angular = rt

                        elif mod == 2:
                            linear = (rt + lt)/2
                            angular = rt - lt

                        elif mod == 3:
                            speed_mod3 = rt - lt
                            linear = ly * abs(speed_mod3)
                            angular = lx * abs(speed_mod3)

                        if abs(linear) < deadzone:
                            linear = 0.0
                        if abs(angular) < deadzone:
                            angular = 0.0

                        linear = round(linear, 2)
                        angular = round(angular, 2)

                        if abs(linear - prev_lin) > 0.05 or abs(angular - prev_ang) > 0.05:
                            send_robot_commands(linear, angular)
                            prev_lin, prev_ang = linear, angular

                    elif event.type == ecodes.EV_KEY and event.value == 1:
                        app = tkinter._default_root
                        btn_map = {
                            ecodes.BTN_SOUTH: (toggle_sw1, "A"),
                            ecodes.BTN_EAST:  (toggle_sw2, "B"),
                            ecodes.BTN_NORTH: (toggle_sw3, "X"),
                            ecodes.BTN_WEST:  (toggle_sw4, "Y"),
                        }
                        if event.code in btn_map:
                            callback, label = btn_map[event.code]
                            if app:
                                app.after(0, callback)
                            print(f"🔘 Pulsante {label} premuto (code {event.code})")

            except OSError:
                if JOYPAD_AVAILABLE:
                    print("⚠️ Joypad disconnected (OSError)")
                JOYPAD_AVAILABLE = False
                device = None
                time.sleep(0.5)
            except BlockingIOError:
                continue
            except Exception as e:
                print(f"Error in joypad thread (read loop): {e}")
                time.sleep(0.1)

    finally:
        # cleanup finale
        JOYPAD_AVAILABLE = False
        joypad_thread_data.running = False
        print("🛑 Joypad thread ended (clean exit)")

def start_joypad_thread(mod=1):
    if joypad_thread_data.running:
        print("⚠️ Active Joypad thread - skipping start")
        return

    joypad_thread_data.stop_event.clear()
    joypad_thread_data.thread = threading.Thread(
        target=joypad_teleop_thread,
        args=(mod,),
        name="JoypadThread",
        daemon=True
    )
    joypad_thread_data.thread.start()
    joypad_thread_data.running = True
    print(f"[JOY] start requested (mod={mod}). Thread started: {joypad_thread_data.thread.name}")

def stop_joypad_thread(timeout=2.0):
    if not joypad_thread_data.running:
        print("[JOY] stop requested but no thread running")
        return
    print("🛑 Aborting joypad thread...")
    joypad_thread_data.stop_event.set()
    if joypad_thread_data.thread:
        joypad_thread_data.thread.join(timeout=timeout)
        if joypad_thread_data.thread.is_alive():
            print("⚠️ Joypad thread did not exit within timeout")
        else:
            print("[JOY] Joypad thread joined successfully")
    joypad_thread_data.running = False


import threading as _th
def print_active_threads():
    print("=== Active threads ===")
    for t in _th.enumerate():
        print(f" - {t.name} (alive={t.is_alive()}, daemon={t.daemon})")
    print("======================")

# =============================
# TELEOP 
# =============================

def keyboard_teleop_thread(mode=2):
    linear_speed = 0.5
    angular_speed = 0.0
    step = 0.15

    cmd_linear = 0.0
    cmd_angular = 0.0

    def send():
        #print(cmd_linear,cmd_angular)
        send_robot_commands(round(cmd_linear, 2), round(cmd_angular, 2))

    def update_set_speeds():
        global linear_speed_set, angular_speed_set
        linear_speed_set = linear_speed
        angular_speed_set = angular_speed


    def on_press(key):
        nonlocal linear_speed, angular_speed, cmd_linear, cmd_angular

        try:
            if mode == 1:
                if key.char == 'i':
                    linear_speed = min(1.0, linear_speed + step)
                elif key.char == ',':
                    linear_speed = max(-1.0, linear_speed - step)
                elif key.char == 'j':
                    angular_speed = max(-1.0, angular_speed - step)
                    linear_speed = 0.0
                elif key.char == 'l':
                    angular_speed = min(1.0, angular_speed + step)
                    linear_speed = 0.0
                elif key.char == 'u':
                    linear_speed = min(1.0, linear_speed + step / 2)
                    angular_speed = -0.3
                elif key.char == 'o':
                    linear_speed = min(1.0, linear_speed + step / 2)
                    angular_speed = 0.3
                elif key.char == 'k':
                    linear_speed = 0.0
                    angular_speed = 0.0

                send_robot_commands(round(linear_speed, 2), round(angular_speed, 2))

            else:
                if key.char == 'w':
                    linear_speed = min(1.0, linear_speed + step)
                elif key.char == 'e':
                    linear_speed = max(-1.0, linear_speed - step)
                elif key.char == 's':
                    angular_speed = max(-1.0, angular_speed - step)
                elif key.char == 'd':
                    angular_speed = min(1.0, angular_speed + step)
                                
                update_set_speeds()

                if key.char == 'i': 
                    cmd_linear = linear_speed
                    cmd_angular = 0.0
                elif key.char == ',':
                    cmd_linear = -linear_speed
                    cmd_angular = 0.0
                elif key.char == 'l':
                    cmd_linear = 0.0
                    cmd_angular = angular_speed
                elif key.char == 'j':
                    cmd_linear = 0.0
                    cmd_angular = -angular_speed
                elif key.char == 'k': 
                    cmd_linear = 0.0
                    cmd_angular = 0.0
                elif key.char == 'o':
                    cmd_linear = linear_speed
                    cmd_angular = angular_speed
                elif key.char == 'u':
                    cmd_linear = linear_speed
                    cmd_angular = -angular_speed

                send()

        except AttributeError:
            pass

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    try:
        while not teleop_thread_data.stop_thread:
            time.sleep(0.1)
    finally:
        send_robot_commands(0.0, 0.0)
        listener.stop()



def start_teleop_thread():
    global teleop_thread
    if not teleop_thread_data.running:
        teleop_thread_data.running = True
        teleop_thread_data.stop_thread = False
        teleop_thread = threading.Thread(target=keyboard_teleop_thread)
        teleop_thread.start()


def stop_teleop_thread():
    global teleop_thread
    teleop_thread_data.stop_thread = True
    if teleop_thread:
        teleop_thread.join()
        teleop_thread_data.running = False

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    start_teleop_thread()
    start_joypad_thread(mod=1)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_teleop_thread()
        stop_joypad_thread()

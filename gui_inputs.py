import threading
import time
from pynput import keyboard
from evdev import InputDevice, ecodes, list_devices
from robot_controller import *
import tkinter

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


def joypad_teleop_thread(mod=None):
    global JOYPAD_AVAILABLE

    if not mod or mod not in (1, 2, 3):
        #print("⚠️ No valid mod, default: mod 1")
        mod = 1

    prev_lin = 0.0
    prev_ang = 0.0
    linear = 0.0
    angular = 0.0
    deadzone = 0.1
    lt = 0.0
    rt = 0.0
    ry = 0.0
    rx =0.0
    slider = 0.0
    btn_a = btn_b = btn_x = btn_y = 0

    #print(f"🎮 Joypad thread started (mod {mod})")

    device = check_joypad_connection(verbose=True)
    JOYPAD_AVAILABLE = bool(device)

    while not joypad_thread_data.stop_event.is_set():
        if not device:
            device = check_joypad_connection(verbose=False)
            if device:
                #print(f"✅ Joypad connected: {device.name}")
                JOYPAD_AVAILABLE = True
            else:
                JOYPAD_AVAILABLE = False
                time.sleep(1)
                continue

        try:
            for event in device.read_loop():
                if joypad_thread_data.stop_event.is_set():
                    break

                if event.type == ecodes.EV_ABS:
                    val = 0.0
                    if event.code in (ecodes.ABS_X, ecodes.ABS_Y, ecodes.ABS_RX, ecodes.ABS_RY):
                        val = event.value / 32767.0 if event.value <= 32767 else 0.0
                    elif event.code in (ecodes.ABS_Z, ecodes.ABS_RZ):  # trigger (0-255)
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

                    # === DEADZONE ===
                    if abs(linear) < deadzone:
                        linear = 0.0
                    if abs(angular) < deadzone:
                        angular = 0.0

                    linear = round(linear, 2)
                    angular = round(angular, 2)

                    if abs(linear - prev_lin) > 0.05 or abs(angular - prev_ang) > 0.05:
                        send_robot_commands(linear, angular)
                        prev_lin, prev_ang = linear, angular

                elif event.type == ecodes.EV_KEY and event.value == 1:  # only pressure
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
                print("⚠️ Joypad disconnected")
            JOYPAD_AVAILABLE = False
            device = None
            time.sleep(1)
        except Exception as e:
            print(f"Error in joypad thread: {e}")
            time.sleep(0.1)

    JOYPAD_AVAILABLE = False
    print("🛑 Joypad thread ended")


    JOYPAD_AVAILABLE = False
    print("🛑 Joypad thread ended")



def start_joypad_thread(mod=1):
    global mod_global
    mod_global = mod
    if joypad_thread_data.running:
        print("⚠️Active Joypad thread")
        return

    joypad_thread_data.stop_event.clear()
    joypad_thread_data.thread = threading.Thread(
        target=joypad_teleop_thread,
        args=(mod,),
        daemon=True
    )
    joypad_thread_data.thread.start()
    joypad_thread_data.running = True

def stop_joypad_thread():
    if not joypad_thread_data.running:
        return
    print("🛑 Aborting joypad thread...")
    joypad_thread_data.stop_event.set()
    if joypad_thread_data.thread:
        joypad_thread_data.thread.join(timeout=2)
    joypad_thread_data.running = False

# =============================
# TELEOP 
# =============================

def keyboard_teleop_thread(mode=2):
    linear_speed = 0.0
    angular_speed = 0.0
    step = 0.15

    cmd_linear = 0.0
    cmd_angular = 0.0

    def send():
        send_robot_commands(round(cmd_linear, 2), round(cmd_angular, 2))

    def update_set_speeds():
        global linear_speed_set, angular_speed_set
        linear_speed_set = linear_speed
        angular_speed_set = angular_speed


    def on_press(key):
        nonlocal linear_speed, angular_speed, cmd_linear, cmd_angular

        try:
            if mode == 1:
                if key.char == 'w':
                    linear_speed = min(1.0, linear_speed + step)
                elif key.char == 's':
                    linear_speed = max(-1.0, linear_speed - step)
                elif key.char == 'a':
                    angular_speed = max(-1.0, angular_speed - step)
                    linear_speed = 0.0
                elif key.char == 'd':
                    angular_speed = min(1.0, angular_speed + step)
                    linear_speed = 0.0
                elif key.char == 'q':
                    linear_speed = min(1.0, linear_speed + step / 2)
                    angular_speed = -0.3
                elif key.char == 'e':
                    linear_speed = min(1.0, linear_speed + step / 2)
                    angular_speed = 0.3
                elif key.char == ' ':
                    linear_speed = 0.0
                    angular_speed = 0.0

                send_robot_commands(round(linear_speed, 2), round(angular_speed, 2))

            else:
                if key.char == 'w':
                    linear_speed = min(1.0, linear_speed + step)
                elif key.char == 's':
                    linear_speed = max(-1.0, linear_speed - step)
                elif key.char == 'a':
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
                elif key.char == 'j':
                    cmd_linear = 0.0
                    cmd_angular = angular_speed
                elif key.char == 'l':
                    cmd_linear = 0.0
                    cmd_angular = -angular_speed
                elif key.char == 'k': 
                    cmd_linear = 0.0
                    cmd_angular = 0.0
                elif key.char == ' ':
                    linear_speed = 0.0
                    angular_speed = 0.0
                    cmd_linear = 0.0
                    cmd_angular = 0.0

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

import threading
import time
import keyboard
import sdl2
from robot_controller import send_robot_commands

# =============================
# THREAD DATA
# =============================
class TeleopThreadData:
    def __init__(self):
        self.running = False
        self.stop_thread = False

class JoypadThreadData:
    def __init__(self):
        self.stop_event = threading.Event()
        self.running = False

teleop_thread_data = TeleopThreadData()
joypad_thread_data = JoypadThreadData()

teleop_thread = None
joypad_thread = None
mod_global = 1
JOYPAD_AVAILABLE = False

# =============================
# UTILS
# =============================
def apply_deadzone(value, deadzone=0.1):
    return value if abs(value) > deadzone else 0.0

def normalize_axis(value):
    return max(-1.0, min(1.0, value / 32768.0))

def check_joypad_connection():
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS | sdl2.SDL_INIT_JOYSTICK)
    return sdl2.SDL_NumJoysticks() > 0

# =============================
# TELEOP TASTIERA
# =============================
def keyboard_teleop_thread():
    linear_speed = 0.0
    angular_speed = 0.0
    step = 0.2

    try:
        while not teleop_thread_data.stop_thread:
            if keyboard.is_pressed("w"):
                linear_speed = min(1.0, linear_speed + step)
                angular_speed = 0.0
            elif keyboard.is_pressed("s"):
                linear_speed = max(-1.0, linear_speed - step)
                angular_speed = 0.0
            elif keyboard.is_pressed("a"):
                angular_speed = max(-1.0, angular_speed - step)
                linear_speed = 0.0
            elif keyboard.is_pressed("d"):
                angular_speed = min(1.0, angular_speed + step)
                linear_speed = 0.0
            elif keyboard.is_pressed("space"):
                linear_speed = 0.0
                angular_speed = 0.0
            elif keyboard.is_pressed("q"):
                angular_speed = max(-1.0, angular_speed - step)
            elif keyboard.is_pressed("e"):
                angular_speed = min(1.0, angular_speed + step)
            elif keyboard.is_pressed("r"):
                linear_speed = min(1.0, linear_speed + step)
            elif keyboard.is_pressed("f"):
                linear_speed = max(-1.0, linear_speed - step)

            send_robot_commands(round(linear_speed, 2), round(angular_speed, 2))
            time.sleep(0.1)
    finally:
        send_robot_commands(0.0, 0.0)

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
# TELEOP JOYPAD SDL2
# =============================
def joypad_teleop_thread(mod=1):
    global JOYPAD_AVAILABLE
    joystick = None
    prev_lin = 0.0
    prev_ang = 0.0

    try:
        print("Joypad thread started")
        while not joypad_thread_data.stop_event.is_set():
            event = sdl2.SDL_Event()
            while sdl2.SDL_PollEvent(event):
                if event.type == sdl2.SDL_JOYDEVICEADDED and joystick is None:
                    index = event.jdevice.which
                    joystick = sdl2.SDL_JoystickOpen(index)
                    if joystick:
                        name = sdl2.SDL_JoystickName(joystick)
                        JOYPAD_AVAILABLE = True
                        print(f"✅ Joypad connected: {name.decode() if name else 'Unknown'}")
                elif event.type == sdl2.SDL_JOYDEVICEREMOVED and joystick:
                    sdl2.SDL_JoystickClose(joystick)
                    joystick = None
                    JOYPAD_AVAILABLE = False
                    print("❌ Joypad disconnected")

            if joystick is None and sdl2.SDL_NumJoysticks() > 0:
                joystick = sdl2.SDL_JoystickOpen(0)
                if joystick:
                    JOYPAD_AVAILABLE = True
                    name = sdl2.SDL_JoystickName(joystick)
                    print(f"✅ Joypad connected: {name.decode() if name else 'Unknown'}")

            if joystick:
                sdl2.SDL_JoystickUpdate()
                lx = normalize_axis(sdl2.SDL_JoystickGetAxis(joystick, 0))
                ly = normalize_axis(sdl2.SDL_JoystickGetAxis(joystick, 1))
                rx = normalize_axis(sdl2.SDL_JoystickGetAxis(joystick, 3))
                ry = normalize_axis(sdl2.SDL_JoystickGetAxis(joystick, 4))
                lt = (sdl2.SDL_JoystickGetAxis(joystick, 2) + 32768) / 65535.0
                rt = (sdl2.SDL_JoystickGetAxis(joystick, 5) + 32768) / 65535.0
                btn_lb = sdl2.SDL_JoystickGetButton(joystick, 4)
                btn_rb = sdl2.SDL_JoystickGetButton(joystick, 5)

                linear = 0.0
                angular = 0.0

                if mod == 1:
                    linear = -ly
                    angular = lx
                    if lt > 0.2:
                        angular -= lt
                    if rt > 0.2:
                        angular += rt
                elif mod == 2:
                    linear = -ly
                    angular = rx
                elif mod == 3:
                    linear = rt - lt
                    if btn_lb:
                        angular = -0.6
                    elif btn_rb:
                        angular = 0.6

                linear = apply_deadzone(linear)
                angular = apply_deadzone(angular)
                linear = round(linear, 2)
                angular = round(angular, 2)

                if abs(linear - prev_lin) > 0.05 or abs(angular - prev_ang) > 0.05:
                    send_robot_commands(linear, angular)
                    prev_lin = linear
                    prev_ang = angular

            time.sleep(0.05)
    finally:
        if joystick:
            sdl2.SDL_JoystickClose(joystick)
        JOYPAD_AVAILABLE = False
        print("Joypad thread stopped")

def start_joypad_thread(mod=1):
    global joypad_thread, mod_global
    mod_global = mod
    if joypad_thread and joypad_thread.is_alive():
        print("Joypad thread is alive")
        return
    joypad_thread_data.stop_event.clear()
    joypad_thread = threading.Thread(target=joypad_teleop_thread, args=(mod,))
    joypad_thread.daemon = True
    joypad_thread.start()

def stop_joypad_thread():
    joypad_thread_data.stop_event.set()
    if joypad_thread:
        joypad_thread.join()

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    # Init SDL2
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS | sdl2.SDL_INIT_JOYSTICK)

    print("Teleop robot")
    start_teleop_thread()
    start_joypad_thread(mod=1)

    try:
        while True:
            time.sleep(1)
            if check_joypad_connection():
                print("Joypad available")

            if keyboard.is_pressed("1"):
                mod_global = 1
            elif keyboard.is_pressed("2"):
                mod_global = 2
            elif keyboard.is_pressed("3"):
                mod_global = 3
    except KeyboardInterrupt:
        stop_teleop_thread()
        stop_joypad_thread()
        sdl2.SDL_Quit()

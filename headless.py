import os
import time
from pynput import keyboard
from robot_controller import (
    send_robot_commands,
    set_robot_ip,
    WS_connection,
    lora_connection,
    espnow_connection,
    start_update_thread,
    stop_update_thread,
)

def clear_console():
    """Clear terminal screen (cross-platform)"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_hud(mode, linear, angular, cmd_linear=None, cmd_angular=None):
    """Display live HUD in terminal"""
    clear_console()
    print("=== 🧭 HEADLESS TELEOP HUD ===\n")

    if mode == 1:
        print("🎮 MODE 1: Direct Control (WASD + Q/E for wide turns)")
        print(f"➡ Linear speed : {linear:+.2f}")
        print(f"↻ Angular speed: {angular:+.2f}\n")
    else:
        print("🤖 MODE 2: ROS-style Control")
        print(f"Set linear  : {linear:+.2f}")
        print(f"Set angular : {angular:+.2f}")
        print(f"Cmd linear  : {cmd_linear:+.2f}")
        print(f"Cmd angular : {cmd_angular:+.2f}\n")

    # Simple joystick visualization
    grid = [[" " for _ in range(7)] for _ in range(5)]
    center_x, center_y = 3, 2
    x = int(center_x + angular * 3)
    y = int(center_y - linear * 2)
    x = max(0, min(6, x))
    y = max(0, min(4, y))
    grid[y][x] = "●"

    print("     Joystick:")
    for row in grid:
        print("     " + "".join(row))
    print("\n🕹️  Controls:")
    if mode == 1:
        print("W/S: forward/backward | A/D: rotate | Q/E: wide turn | Z: stop | X: exit\n")
    else:
        print("W/S: set linear speed | A/D: set angular speed")
        print("I,J,K,L,,: movement commands | SPACE: reset | X: exit\n")


def start_headless_teleop(ip: str, protocol: str = "http", esp_port: str = "COM3", joy_mod: int = 2):
    """
    Headless keyboard teleoperation with live text HUD.
    joy_mod = 1 -> direct control (WASD + Q/E)
    joy_mod = 2 -> ROS-style control (set + send)
    """
    set_robot_ip(ip)

    # Initialize communication
    if protocol == "websocket":
        print("🔌 WebSocket mode enabled")
        WS_connection()
    elif protocol == "lora":
        print("📡 LoRa mode enabled")
        lora_connection()
    elif protocol == "espnow":
        print(f"📶 ESPNow mode on {esp_port}")
        espnow_connection(esp_port)
    else:
        print("🌐 HTTP mode enabled (default)")

    start_update_thread(ip)

    # Initialize motion vars
    linear_speed = 0.0
    angular_speed = 0.0
    cmd_linear = 0.0
    cmd_angular = 0.0
    step = 0.2
    running = True

    print_hud(joy_mod, linear_speed, angular_speed, cmd_linear, cmd_angular)

    def on_press(key):
        nonlocal linear_speed, angular_speed, cmd_linear, cmd_angular, running

        try:
            if joy_mod == 1:
                # === MODE 1: Direct control ===
                if key.char == "w":
                    linear_speed = min(1.0, linear_speed + step)
                elif key.char == "s":
                    linear_speed = max(-1.0, linear_speed - step)
                elif key.char == "a":
                    angular_speed = max(-1.0, angular_speed - step)
                    linear_speed = 0.0
                elif key.char == "d":
                    angular_speed = min(1.0, angular_speed + step)
                    linear_speed = 0.0
                elif key.char == "q":
                    # Wide left turn
                    linear_speed = min(1.0, linear_speed + step / 2)
                    angular_speed = -0.3
                elif key.char == "e":
                    # Wide right turn
                    linear_speed = min(1.0, linear_speed + step / 2)
                    angular_speed = 0.3
                elif key.char == "z":
                    linear_speed = 0.0
                    angular_speed = 0.0
                elif key.char == "x":
                    running = False
                    return False

                send_robot_commands(linear_speed, angular_speed)
                print_hud(joy_mod, linear_speed, angular_speed)

            else:
                # === MODE 2: ROS-style ===
                if key.char == "w":
                    linear_speed = min(1.0, linear_speed + step)
                elif key.char == "s":
                    linear_speed = max(-1.0, linear_speed - step)
                elif key.char == "a":
                    angular_speed = max(-1.0, angular_speed - step)
                elif key.char == "d":
                    angular_speed = min(1.0, angular_speed + step)
                elif key.char == "i":
                    cmd_linear = linear_speed
                    cmd_angular = 0.0
                elif key.char == ",":
                    cmd_linear = -linear_speed
                    cmd_angular = 0.0
                elif key.char == "j":
                    cmd_linear = 0.0
                    cmd_angular = angular_speed
                elif key.char == "l":
                    cmd_linear = 0.0
                    cmd_angular = -angular_speed
                elif key.char == "k":
                    cmd_linear = 0.0
                    cmd_angular = 0.0
                elif key.char == " ":
                    linear_speed = 0.0
                    angular_speed = 0.0
                    cmd_linear = 0.0
                    cmd_angular = 0.0
                elif key.char == "x":
                    running = False
                    return False

                send_robot_commands(cmd_linear, cmd_angular)
                print_hud(joy_mod, linear_speed, angular_speed, cmd_linear, cmd_angular)

        except AttributeError:
            pass

    # Start keyboard listener
    with keyboard.Listener(on_press=on_press) as listener:
        while running:
            time.sleep(0.05)
        listener.stop()

    # Stop safely
    send_robot_commands(0, 0)
    stop_update_thread()
    clear_console()
    print("✅ Teleop stopped.\n")

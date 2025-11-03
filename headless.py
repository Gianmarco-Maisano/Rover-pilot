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

def start_headless_teleop(ip: str, protocol: str = "http", esp_port: str = "COM3", joy_mod: int = 1):
    """Controllo da tastiera unificato, indipendente dal protocollo."""
    set_robot_ip(ip)

    # Seleziona il tipo di connessione
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

    # Avvia il thread di comunicazione
    start_update_thread(ip)

    linear_speed = 0.0
    angular_speed = 0.0
    acceleration = 0.1
    running = True

    def on_press(key):
        nonlocal linear_speed, angular_speed, running
        try:
            if key.char == "w":
                linear_speed = min(1.0, linear_speed + acceleration)
            elif key.char == "s":
                linear_speed = max(-1.0, linear_speed - acceleration)
            elif key.char == "a":
                angular_speed = max(-1.0, angular_speed - acceleration)
            elif key.char == "d":
                angular_speed = min(1.0, angular_speed + acceleration)
            elif key.char == "z":
                linear_speed = 0
                angular_speed = 0
            elif key.char == "q":
                print("🛑 Exiting teleop...")
                running = False
                return False
        except AttributeError:
            pass

        send_robot_commands(linear_speed, angular_speed)
        print(f"➡ Linear: {linear_speed:.2f}, Angular: {angular_speed:.2f}")

    print("=== HEADLESS TELEOP ===")
    print("Use W/A/S/D to move, Z to stop, Q to quit.")
    print(f"Robot IP: {ip}  |  Protocol: {protocol}")

    with keyboard.Listener(on_press=on_press) as listener:
        while running:
            time.sleep(0.05)
        listener.stop()

    send_robot_commands(0, 0)
    stop_update_thread()
    print("✅ Teleop stopped.")

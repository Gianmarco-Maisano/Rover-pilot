import customtkinter
import tkinter as tk
import json
import uuid


CONFIG_FILE = "recent_configurations.json"

def _default_settings() -> dict:
    return {"devices": [], "preferences": {}}

def _load_settings() -> dict:
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict) and "devices" in data and "preferences" in data:
                if isinstance(data["devices"], list) and isinstance(data["preferences"], dict):
                    return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return _default_settings()

def _save_settings(settings: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def save_configuration(configuration: dict):
    settings = _load_settings()
    devices = settings["devices"]

    if "id" not in configuration:
        configuration["id"] = str(uuid.uuid4())

    devices = [d for d in devices if d.get("id") != configuration["id"]]
    devices.insert(0, configuration)
    settings["devices"] = devices[:5]
    _save_settings(settings)

def load_recent_configurations():
    return _load_settings()["devices"]

def load_recent_settings():
    return _load_settings()

def save_dark_mode(switch_value: int):
    settings = _load_settings()
    settings["preferences"]["dark_mode"] = int(bool(switch_value))
    _save_settings(settings)

def save_joypad_mod(new_value: int):
    settings = _load_settings()
    settings["preferences"]["joypad_mod"] = int(new_value)
    _save_settings(settings)

def new_config_window(window, on_close_callback=None):
    frame = customtkinter.CTkFrame(window)
    frame.grid(row=0, column=0, rowspan=11, columnspan=2, padx=40, pady=10, sticky="nsew")

    def close_frame():
        frame.destroy()
        if on_close_callback:
            on_close_callback()  

    customtkinter.CTkLabel(frame, text="Robot name / configuration").grid(row=0, column=0, padx=20, pady=10, sticky=tk.W)
    name_entry = customtkinter.CTkEntry(frame, placeholder_text="insert robot name")
    name_entry.grid(row=1, column=0, padx=20, pady=10, sticky=tk.W)

    customtkinter.CTkLabel(frame, text="Protocol").grid(row=2, column=0, padx=20, pady=10, sticky=tk.W)
    type_menu = customtkinter.CTkOptionMenu(frame, values=["http", "websocket", "ESP_now"])
    type_menu.grid(row=3, column=0, padx=20, pady=10, sticky=tk.W)
    type_menu.set("http")

    customtkinter.CTkLabel(frame, text="Robot IP").grid(row=4, column=0, padx=20, pady=10, sticky=tk.W)
    ip_entry = customtkinter.CTkEntry(frame, placeholder_text="IP address")
    ip_entry.grid(row=5, column=0, padx=20, pady=10, sticky=tk.W)

    customtkinter.CTkLabel(frame, text="Telemetry").grid(row=0, column=1, padx=20, pady=10, sticky=tk.W)
    battery_sw = customtkinter.CTkSwitch(frame, text="Battery %")
    battery_sw.grid(row=1, column=1, padx=20, pady=10, sticky=tk.W)
    rssi_sw = customtkinter.CTkSwitch(frame, text="RSSI")
    rssi_sw.grid(row=2, column=1, padx=20, pady=10, sticky=tk.W)

    customtkinter.CTkLabel(frame, text="Slider").grid(row=3, column=1, padx=20, pady=10, sticky=tk.W)
    slider_sw = customtkinter.CTkSwitch(frame, text="Enable slider")
    slider_sw.grid(row=4, column=1, padx=20, pady=10, sticky=tk.W)

    btn_label_row = 0
    customtkinter.CTkLabel(frame, text="Buttons").grid(row=btn_label_row, column=2, padx=20, pady=10,sticky=tk.W)
    btn_entries = []
    def update_btn_fields(count_str: str):
        for w in btn_entries: w.destroy()
        btn_entries.clear()
        count = int(count_str); base_row = btn_label_row + 2
        for i in range(count):
            e = customtkinter.CTkEntry(frame, placeholder_text=f" BTN{i+1} name")
            e.grid(row=base_row + i, column=2, padx=20, pady=10, sticky=tk.W)
            btn_entries.append(e)
    btn_count_menu = customtkinter.CTkOptionMenu(frame, values=["0", "1", "2"], command=update_btn_fields)
    btn_count_menu.grid(row=1, column=2, padx=20, pady=10, sticky=tk.W); btn_count_menu.set("0")

    sw_label_row = 0
    customtkinter.CTkLabel(frame, text="Switch (toggle)").grid(row=sw_label_row, column=3, padx=20, pady=10, sticky=tk.W)
    sw_entries = []
    def update_sw_fields(count_str: str):
        for w in sw_entries: w.destroy()
        sw_entries.clear()
        count = int(count_str); base_row = sw_label_row + 2
        for i in range(count):
            e = customtkinter.CTkEntry(frame, placeholder_text=f"SW{i+1} name")
            e.grid(row=base_row + i, column=3, padx=20, pady=10, sticky=tk.W)
            sw_entries.append(e)
    sw_count_menu = customtkinter.CTkOptionMenu(frame, values=["0", "1", "2", "3", "4"], command=update_sw_fields)
    sw_count_menu.grid(row=sw_label_row + 1, column=3, padx=20, pady=10, sticky=tk.W); sw_count_menu.set("0")

    def pick_configuration():
        configuration = {
            "name": name_entry.get().strip(),
            "type": type_menu.get(),
            "ip": ip_entry.get().strip(),
            "battery": int(bool(battery_sw.get())),
            "rssi": int(bool(rssi_sw.get())),
            "slider": int(bool(slider_sw.get())),
            "btn_count": int(btn_count_menu.get()),
            "btn_labels": [e.get().strip() or f"BTN{i+1}" for i, e in enumerate(btn_entries)],
            "sw_count": int(sw_count_menu.get()),
            "sw_labels": [e.get().strip() or f"SW{i+1}" for i, e in enumerate(sw_entries)],
        }
        save_configuration(configuration) 
        close_frame()


    customtkinter.CTkButton(frame, text="Save config ", command=pick_configuration)\
        .grid(row=11, column=0, padx=20, pady=15, sticky=tk.W)
    customtkinter.CTkButton(frame, text="Annulla", command=close_frame)\
        .grid(row=11, column=1, padx=20, pady=15, sticky=tk.W)

def edit_config_window(window, config_id=None, on_close_callback=None):
    frame = customtkinter.CTkFrame(window)
    frame.grid(row=0, column=0, rowspan=11, columnspan=2, padx=40, pady=10, sticky="nsew")

    def close_frame():
        frame.destroy()
        if on_close_callback:
            on_close_callback() 

    recent = load_recent_configurations()
    cfg = next((c for c in recent if c["id"] == config_id), None)
    if cfg is None:
        close_frame()
        return

    name_var   = tk.StringVar(value=cfg.get("name", ""))
    ip_var     = tk.StringVar(value=cfg.get("ip", ""))
    type_var   = tk.StringVar(value=cfg.get("type", "http"))
    bat_var    = tk.IntVar(value=int(bool(cfg.get("battery", 0))))
    rssi_var   = tk.IntVar(value=int(bool(cfg.get("rssi", 0))))
    slider_var = tk.IntVar(value=int(bool(cfg.get("slider", 0))))
    btn_labels = list(cfg.get("btn_labels", []))
    sw_labels  = list(cfg.get("sw_labels", []))
    btn_count_var = tk.StringVar(value=str(min(max(int(cfg.get("btn_count", 0)), 0), 2)))
    sw_count_var  = tk.StringVar(value=str(min(max(int(cfg.get("sw_count", 0)), 0), 4)))

    customtkinter.CTkLabel(frame, text="Robot name/configuration").grid(row=0, column=0, padx=20, pady=10, sticky=tk.W)
    name_entry = customtkinter.CTkEntry(frame, placeholder_text="insert robot name", textvariable=name_var)
    name_entry.grid(row=1, column=0, padx=20, pady=5, sticky=tk.W)

    customtkinter.CTkLabel(frame, text="Protocol").grid(row=2, column=0, padx=20, pady=10, sticky=tk.W)
    type_menu = customtkinter.CTkOptionMenu(frame, values=["http", "websocket", "ESP_now"], variable=type_var)
    type_menu.grid(row=3, column=0, padx=20, pady=5, sticky=tk.W)

    customtkinter.CTkLabel(frame, text="Robot IP").grid(row=4, column=0, padx=20, pady=10, sticky=tk.W)
    ip_entry = customtkinter.CTkEntry(frame, placeholder_text="IP address", textvariable=ip_var)
    ip_entry.grid(row=5, column=0, padx=20, pady=10, sticky=tk.W)

    customtkinter.CTkLabel(frame, text="Telemetry").grid(row=0, column=1, padx=20, pady=10, sticky=tk.W)
    battery_sw = customtkinter.CTkSwitch(frame, text="Battery %", variable=bat_var)
    battery_sw.grid(row=1, column=1, padx=20, pady=10, sticky=tk.W)
    rssi_sw = customtkinter.CTkSwitch(frame, text="RSSI", variable=rssi_var)
    rssi_sw.grid(row=2, column=1, padx=20, pady=10, sticky=tk.W)

    customtkinter.CTkLabel(frame, text="Slider").grid(row=3, column=1, padx=20, pady=10, sticky=tk.W)
    slider_sw = customtkinter.CTkSwitch(frame, text="Abilita slider", variable=slider_var)
    slider_sw.grid(row=4, column=1, padx=20, pady=10, sticky=tk.W)

    btn_label_row = 0
    customtkinter.CTkLabel(frame, text="Button").grid(row=btn_label_row, column=2, padx=20, pady=10, sticky=tk.W)
    btn_entries = []
    def update_btn_fields(count_str: str):
        for w in btn_entries: w.destroy()
        btn_entries.clear()
        count = int(count_str); base_row = btn_label_row + 2
        for i in range(count):
            entry = customtkinter.CTkEntry(frame, placeholder_text=f" BTN{i+1} name")
            entry.grid(row=base_row + i, column=2, padx=20, pady=10, sticky=tk.W)
            if i < len(btn_labels): entry.insert(0, btn_labels[i])
            btn_entries.append(entry)
    btn_count_menu = customtkinter.CTkOptionMenu(frame, values=["0", "1", "2"], variable=btn_count_var, command=update_btn_fields)
    btn_count_menu.grid(row=btn_label_row + 1, column=2, padx=20, pady=10, sticky=tk.W)
    update_btn_fields(btn_count_var.get())

    sw_label_row = 0
    customtkinter.CTkLabel(frame, text="Switch (toggle)").grid(row=sw_label_row, column=3, padx=20, pady=10, sticky=tk.W)
    sw_entries = []
    def update_sw_fields(count_str: str):
        for w in sw_entries: w.destroy()
        sw_entries.clear()
        count = int(count_str); base_row = sw_label_row + 2
        for i in range(count):
            entry = customtkinter.CTkEntry(frame, placeholder_text=f" SW{i+1} name")
            entry.grid(row=base_row + i, column=3, padx=20, pady=10, sticky=tk.W)
            if i < len(sw_labels): entry.insert(0, sw_labels[i])
            sw_entries.append(entry)
    sw_count_menu = customtkinter.CTkOptionMenu(frame, values=["0", "1", "2", "3", "4"], variable=sw_count_var, command=update_sw_fields)
    sw_count_menu.grid(row=sw_label_row + 1, column=3, padx=20, pady=10, sticky=tk.W)
    update_sw_fields(sw_count_var.get())

    def save_conf_mod():
        configuration = {
            "id": cfg["id"],
            "name": name_entry.get().strip(),
            "type": type_menu.get(),
            "ip": ip_entry.get().strip(),
            "battery": int(bool(battery_sw.get())),
            "rssi": int(bool(rssi_sw.get())),
            "slider": int(bool(slider_sw.get())),
            "btn_count": int(btn_count_menu.get()),
            "btn_labels": [e.get().strip() or f"BTN{i+1}" for i, e in enumerate(btn_entries)],
            "sw_count": int(sw_count_menu.get()),
            "sw_labels": [e.get().strip() or f"SW{i+1}" for i, e in enumerate(sw_entries)],
        }
        save_configuration(configuration)
        close_frame()


    customtkinter.CTkButton(frame, text="Save and run", command=save_conf_mod)\
        .grid(row=30, column=0, padx=20, pady=15, sticky=tk.W)
    customtkinter.CTkButton(frame, text="Cancel", command=close_frame)\
        .grid(row=30, column=1, padx=20, pady=15, sticky=tk.W)

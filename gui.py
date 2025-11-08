# guy.py
import tkinter as tk
from customtkinter import CTkImage
from PIL import Image
import customtkinter
from gui_inputs import *
import gui_inputs
from robot_controller import *
import robot_controller
from virtual_joy import JoystickModule
import threading
from lora_plugin import *
from config_manager import *

theme_var = None
last_angular_speed = None
last_linear_speed = None
last_linear_speed_set = None
last_angular_speed_set = None
Joy_status = 0
ultimi_10_valori = []
status_info = None
battery_info = None
connection_qty = None
stop_flag = False
Joy_active=False

def auto_connect_robot(stat_label, robot_ip):
    if robot_ip:
        if check_connection(robot_ip):
            stat_label.configure(text=f"Robot connected /{robot_ip}")
            robot_controller.start_update_thread(robot_ip)
            start_status_thread(robot_ip)
        else:
            stat_label.configure(text=f"Connection failed /{robot_ip}")

# ---------- CONNECT WINDOW ----------
def create_connect_window(window, stat_label):

    def close_connect_window():
        connect_window.destroy()

    def connect_to_http(ip):
        if check_connection(ip) is True:
            stat_label.configure(text=f"Robot connected /{ip}")
            robot_controller.start_update_thread(ip)
            start_status_thread(ip)
            close_connect_window()
        else:
            connection_error_label.configure(text="Connection error")

    def try_http_connection():
        robot_ip = ip_entry.get()
        set_robot_ip(robot_ip)
        connect_to_http(robot_ip)

    connect_window = tk.Toplevel()
    connect_window.title("Connection")
    connect_window.geometry("550x200")

    connection_error_uplabel = customtkinter.CTkLabel(connect_window, text="Insert robot IP")
    connection_error_uplabel.grid(row=0, column=0, padx=10, pady=5)

    connection_error_label = customtkinter.CTkLabel(connect_window, text="")
    connection_error_label.grid(row=2, column=0, padx=10, pady=5)

    ip_entry = customtkinter.CTkEntry(connect_window, placeholder_text="Robot IP address")
    ip_entry.grid(row=1, column=0, padx=20, pady=10)

    http_button = customtkinter.CTkButton(connect_window, text="Connect", command=try_http_connection)
    http_button.grid(row=1, column=1, padx=10, pady=10)

# ---------- SETTINGS WINDOW ----------
def create_settings_window(window, theme):
    global Joy_status, JOYPAD_AVAILABLE, Joy_active
    settings_window = tk.Toplevel(window)
    settings_window.title("Settings")
    options_frame = customtkinter.CTkFrame(settings_window)
    options_frame.pack(pady=10)

    top_settings_label = customtkinter.CTkLabel(options_frame, text="Settings", font=("Helvetica", 15))
    top_settings_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
    settings_label = customtkinter.CTkLabel(options_frame, text="", font=("Helvetica", 13))
    settings_label.grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)


    def create_config_window():

        def close_config_window():
            config_window.destroy()

        config_window = tk.Toplevel(settings_window)
        config_window.title("Configuration")
        config_window.geometry("1300x500")

        def update_joy_var(var):
            global Joy_status
            if var == 1:
                Joy_var_1.set(1); Joy_var_2.set(0); Joy_var_3.set(0)
                Joy_status = 1
            elif var == 2:
                Joy_var_1.set(0); Joy_var_2.set(1); Joy_var_3.set(0)
                Joy_status = 2
            elif var == 3:
                Joy_var_1.set(0); Joy_var_2.set(0); Joy_var_3.set(1)
                Joy_status = 3


        theme_setting = load_recent_settings()
        preferences = theme_setting.get('preferences', {})
        Joy_mod_value = preferences.get('joypad_mod', 1)

        Joy_var_1 = tk.IntVar()
        Joy_var_2 = tk.IntVar()
        Joy_var_3 = tk.IntVar()
        
        
        try:
            current_mode = Joy_status if Joy_status in (1, 2, 3) else Joy_mod_value
        except NameError:
            current_mode = Joy_mod_value    

        update_joy_var(current_mode)

        img_mod1 = CTkImage(light_image=Image.open("imgs/mod1.png"), size=(316, 194))
        img_mod2 = CTkImage(light_image=Image.open("imgs/mod2.png"), size=(316, 194))
        img_mod3 = CTkImage(light_image=Image.open("imgs/mod3.png"), size=(316, 194))

        joy1_button = customtkinter.CTkCheckBox(config_window, text="MOD 1", variable=Joy_var_1, command=lambda: update_joy_var(1))
        joy1_button.grid(row=2, column=0, padx=10, pady=5, sticky=tk.N)
        joy1_img_label = customtkinter.CTkLabel(config_window, image=img_mod1, text="")
        joy1_img_label.grid(row=1, column=0, padx=10, pady=30, sticky=tk.E)

        joy2_button = customtkinter.CTkCheckBox(config_window, text="MOD 2", variable=Joy_var_2, command=lambda: update_joy_var(2))
        joy2_button.grid(row=2, column=1, padx=10, pady=5, sticky=tk.N)
        joy2_img_label = customtkinter.CTkLabel(config_window, image=img_mod2, text="")
        joy2_img_label.grid(row=1, column=1, padx=10, pady=30, sticky=tk.E)

        joy3_button = customtkinter.CTkCheckBox(config_window, text="MOD 3", variable=Joy_var_3, command=lambda: update_joy_var(3))
        joy3_button.grid(row=2, column=2, padx=10, pady=5, sticky=tk.N)
        joy3_img_label = customtkinter.CTkLabel(config_window, image=img_mod3, text="")
        joy3_img_label.grid(row=1, column=2, padx=10, pady=30, sticky=tk.E)

        def apply_joy_conf(mod):
            stop_joypad_thread()
            start_joypad_thread(mod)
            #print("started joy mith mod",mod)
            close_config_window()

        apply_joy_conf_button = customtkinter.CTkButton(config_window, text="Apply", command=lambda: apply_joy_conf(Joy_status))
        apply_joy_conf_button.grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)

        joy_conf_label = customtkinter.CTkLabel(config_window, text="", text_color="red", font=("Helvetica", 11))
        joy_conf_label.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky=tk.W)

        def set_joy_conf(Joy_status):
            save_joypad_mod(Joy_status)
            joy_conf_label.configure(text="Restart to apply")

        save_joy_conf = customtkinter.CTkButton(config_window, text="set as default mode", command=lambda: set_joy_conf(Joy_status))
        save_joy_conf.grid(row=4, column=1, padx=10, pady=10, sticky=tk.W)

        #sens_joy_conf = customtkinter.CTkSlider(config_window, text="sensitivity", command=lambda: set_joy_sens())
        #sens_joy_conf.grid(row=4, column=1, padx=10, pady=10, sticky=tk.W)

    config_button = customtkinter.CTkButton(options_frame, text="Config", command=create_config_window, state=tk.DISABLED)
    config_button.grid(row=5, column=1, padx=5)

    def enable_dark_mode():
        if theme.get() == 1:
            customtkinter.set_appearance_mode("dark")
            actual_theme = 1
        else:
            customtkinter.set_appearance_mode("light")
            actual_theme = 0
        return actual_theme

    dark_mode = customtkinter.CTkSwitch(options_frame, text="Dark mode", variable=theme, command=enable_dark_mode)
    dark_mode.grid(row=1, column=0, pady=10, padx=10, sticky=tk.W)

    def save_preference():
        actual_theme = enable_dark_mode()
        save_dark_mode(actual_theme)

    save_mode = customtkinter.CTkButton(options_frame, text="Set as default", command=save_preference)
    save_mode.grid(row=1, column=1, pady=10, padx=10)

    check_var_ava = tk.IntVar(value=0)

    JOYPAD_AVAILABLE = check_joypad_connection()
    if JOYPAD_AVAILABLE:
        settings_label.configure(text="Joypad available")
        config_button.configure(state=tk.NORMAL)
        if Joy_active:
            check_var_ava.set(1)

    def update_controller_state():
        global Joy_active
        JOYPAD_AVAILABLE = check_joypad_connection()
        if JOYPAD_AVAILABLE and check_var_ava.get() == 1:
            settings_label.configure(text="Joypad available")
            config_button.configure(state=tk.NORMAL)
            start_joypad_thread(Joy_status)
            Joy_active=True

        elif JOYPAD_AVAILABLE is False:
            config_button.configure(state=tk.DISABLED)
            settings_label.configure(text="Joypad not available")
            check_var_ava.set(0)
            stop_joypad_thread()
            Joy_active = False

        elif check_var_ava.get() == 0:
            settings_label.configure(text="Joypad disabled")
            config_button.configure(state=tk.DISABLED)
            stop_joypad_thread()
            Joy_active = False


    check_button_3 = customtkinter.CTkSwitch(options_frame, text="External device", variable=check_var_ava, command=update_controller_state)
    check_button_3.grid(row=5, column=0, padx=5, pady=20, sticky=tk.W)

# ---------- LATERAL FRAME (BTN + fino a 4 SWITCH) ----------
def create_lateral_frame(window, log_label, slider,
                         btn_mode: int,          # 0=/, 1= b1, 2=b1+b2
                         sw_mode: int,           # 0..4 = switch
                         btn_labels: tuple[str, ...] = ("BTN1", "BTN2"),
                         sw_labels: tuple[str, ...] = ("SW1", "SW2", "SW3", "SW4")):
    lat_frame = customtkinter.CTkFrame(window)
    lat_frame.grid(row=1, column=2, columnspan=2, rowspan=1, padx=15, pady=15, sticky="nsew")
    lat_frame.grid_columnconfigure(0, weight=1)
    lat_frame.grid_columnconfigure(1, weight=1)
    for r in range(4):
        lat_frame.grid_rowconfigure(r, weight=1)

    # --- Slider (evita shadowing del parametro) ---
    if slider >= 1:
        lat_frame2 = customtkinter.CTkFrame(window)
        lat_frame2.grid(row=2, column=2, columnspan=2, rowspan=1, padx=15, pady=15, sticky="nsew")
        slider_widget = customtkinter.CTkSlider(lat_frame2)  # TODO: aggiungi command se vuoi inviare valori al FW
        slider_widget.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")

    # --- Pulsanti momentanei (b1, b2) ---
    if btn_mode >= 1:
        btn1 = customtkinter.CTkButton(
            lat_frame,
            text=btn_labels[0] if len(btn_labels) > 0 else "BTN1",
            command=press_btn1
        )
        btn1.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

    if btn_mode >= 2:
        btn2 = customtkinter.CTkButton(
            lat_frame,
            text=btn_labels[1] if len(btn_labels) > 1 else "BTN2",
            command=press_btn2
        )
        btn2.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

    # --- helper log testo ---
    def _log(msg: str):
        try:
            log_label.configure(state="normal")
            log_label.insert("end", f"\n{msg}")
            log_label.configure(state="disabled")
            log_label.yview("end")
        except Exception:
            pass

    # --- Switch 1 (sw1) ---
    if sw_mode >= 1:
        sw1_var = tk.BooleanVar(value=getattr(robot_controller, "sw1_state", False))

        def _on_sw1():
            if hasattr(robot_controller, "set_sw1"):
                set_sw1(sw1_var, log_label)
            _log(f"{sw_labels[0] if len(sw_labels)>0 else 'SW1'} {'ON' if sw1_var.get() else 'OFF'}")

        sw1_switch = customtkinter.CTkSwitch(
            lat_frame,
            text=sw_labels[0] if len(sw_labels) > 0 else "SW1",
            variable=sw1_var,
            command=_on_sw1
        )
        sw1_switch.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

    # --- Switch 2 (sw2) ---
    if sw_mode >= 2:
        sw2_var = tk.BooleanVar(value=getattr(robot_controller, "sw2_state", False))

        def _on_sw2():
            if hasattr(robot_controller, "set_sw2"):
                set_sw2(sw2_var, log_label)
            _log(f"{sw_labels[1] if len(sw_labels)>1 else 'SW2'} {'ON' if sw2_var.get() else 'OFF'}")

        sw2_switch = customtkinter.CTkSwitch(
            lat_frame,
            text=sw_labels[1] if len(sw_labels) > 1 else "SW2",
            variable=sw2_var,
            command=_on_sw2
        )
        sw2_switch.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")

    # --- Switch 3 (sw3) ---
    if sw_mode >= 3:
        sw3_var = tk.BooleanVar(value=getattr(robot_controller, "sw3_state", False))

        def _on_sw3():
            if hasattr(robot_controller, "set_sw3"):
                set_sw3(sw3_var, log_label)
            _log(f"{sw_labels[2] if len(sw_labels)>2 else 'SW3'} {'ON' if sw3_var.get() else 'OFF'}")

        sw3_switch = customtkinter.CTkSwitch(
            lat_frame,
            text=sw_labels[2] if len(sw_labels) > 2 else "SW3",
            variable=sw3_var,
            command=_on_sw3
        )
        sw3_switch.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")

    # --- Switch 4 (sw4) ---
    if sw_mode >= 4:
        sw4_var = tk.BooleanVar(value=getattr(robot_controller, "sw4_state", False))

        def _on_sw4():
            if hasattr(robot_controller, "set_sw4"):
                set_sw4(sw4_var, log_label)
            _log(f"{sw_labels[3] if len(sw_labels)>3 else 'SW4'} {'ON' if sw4_var.get() else 'OFF'}")

        sw4_switch = customtkinter.CTkSwitch(
            lat_frame,
            text=sw_labels[3] if len(sw_labels) > 3 else "SW4",
            variable=sw4_var,
            command=_on_sw4
        )
        sw4_switch.grid(row=2, column=1, padx=20, pady=20, sticky="nsew")

# ---------- MAIN LABEL ----------
def create_main_label(window):
    main_frame = customtkinter.CTkFrame(window, corner_radius=10)
    main_frame.grid(row=1, column=0, columnspan=2, rowspan=3, padx=30, pady=15, sticky="nsew")
    main_frame.grid_columnconfigure(0, weight=1)
    main_frame.grid_rowconfigure(0, weight=1)

    main_label = customtkinter.CTkTextbox(main_frame, font=("Courier", 15))
    main_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
    system_ready_text = (
    "\n"
    "╔═════════════════════════════════════════════╗\n"
    "║                                             ║\n"
    "║               SYSTEM READY ✅               ║\n"
    "║                                             ║\n"
    "║                                             ║\n"
    "║                                             ║\n"
    "║                                             ║\n"
    "╚═════════════════════════════════════════════╝\n"
    )

    main_label.insert(tk.END, system_ready_text)

    main_label.configure(state=tk.DISABLED)
    return main_frame, main_label

def update_label(frame, label):
    global last_linear_speed, last_angular_speed, last_linear_speed_set, last_angular_speed_set

    current_linear_speed = robot_controller.linear_speed_value
    current_angular_speed = robot_controller.angular_speed_value
    linear_speed_set = gui_inputs.linear_speed_set
    angular_speed_set = gui_inputs.angular_speed_set

    updates = []

    if linear_speed_set != last_linear_speed_set:
        updates.append(f"SET | Linear: {linear_speed_set:.2f}")
        last_linear_speed_set = linear_speed_set

    if angular_speed_set != last_angular_speed_set:
        updates.append(f"SET | Angular: {angular_speed_set:.2f}")
        last_angular_speed_set = angular_speed_set

    if current_linear_speed != last_linear_speed or current_angular_speed != last_angular_speed:
        updates.append(f"SENT | Linear: {current_linear_speed:.2f}, Angular: {current_angular_speed:.2f}")
        last_linear_speed = current_linear_speed
        last_angular_speed = current_angular_speed

    if updates:
        label.configure(state=tk.NORMAL)
        label.insert(tk.END, "\n" + "\n".join(updates))
        label.configure(state=tk.DISABLED)
        label.yview(tk.END)

    label.after(50, lambda: update_label(frame, label))


# ---------- STATUS BAR ----------
def create_status_bar(window, battery, rssi, status):

    status_panel = customtkinter.CTkFrame(window)
    status_panel.grid(row=0, column=1, padx=30, pady=15, sticky="nsew")
    status_panel.grid_columnconfigure(0, weight=1)
    status_panel.grid_columnconfigure(1, weight=1)
    status_panel.grid_columnconfigure(2, weight=1)
    status_panel.grid_columnconfigure(3, weight=1)
    status_panel.grid_columnconfigure(4, weight=1)
    status_panel.grid_rowconfigure(1, weight=1)

    status_info = customtkinter.CTkLabel(status_panel, text="No robot connected", text_color="black", bg_color="transparent", anchor=tk.W)
    status_info.grid(row=0, column=0, padx=20, pady=10, sticky=tk.W)

    if status:
        status_info.configure(text="connected")


    if battery == 1:
        battery_logo = customtkinter.CTkLabel(status_panel, text="")
        battery_logo.grid(row=0, column=1, padx=20, pady=10, sticky=tk.E)
        battery_info = customtkinter.CTkLabel(status_panel, text="Battery info n.a.", bg_color="transparent", anchor=tk.E)
        battery_info.grid(row=0, column=2, padx=20, pady=10, sticky=tk.E)
    else:
        battery_info = None
        battery_logo = None

    if rssi == 1:
        wifi_image = customtkinter.CTkImage(Image.open("imgs/wifi_icon.png"))
        connection_logo = customtkinter.CTkLabel(status_panel, image=wifi_image, text="")
        connection_logo.grid(row=0, column=3, padx=20, pady=15, sticky=tk.W)
        connection_qty = customtkinter.CTkLabel(status_panel, text="Connection info n.a.")
        connection_qty.grid(row=0, column=4, padx=20, pady=15, sticky=tk.W)
    else:
        connection_qty = None

    return status_info, battery_logo, battery_info, connection_qty

def calcola_media(ultimo_valore):
    global ultimi_10_valori
    ultimi_10_valori.append(ultimo_valore)
    ultimi_10_valori = ultimi_10_valori[-10:]
    return sum(ultimi_10_valori) / len(ultimi_10_valori)

def update_battery_status(logo_label, text_label, battery_status):
    mean_battery_status = calcola_media(battery_status)
    battery_status_map = round((mean_battery_status - 11.6) / (12.4 - 11.6) * 100)
    text_label.configure(text=f'{battery_status_map} %')
    if 75 < battery_status_map < 100:
        new_image = customtkinter.CTkImage(Image.open("imgs/battery_charge_energy_full_icon.png"))
    elif 50 < battery_status_map <= 75:
        new_image = customtkinter.CTkImage(Image.open("imgs/battery_charge_energy_reduce_icon.png"))
    elif 25 <= battery_status_map <= 50:
        new_image = customtkinter.CTkImage(Image.open("imgs/battery_charge_energy_half_icon.png"))
    else:
        new_image = customtkinter.CTkImage(Image.open("imgs/battery_charge_energy_low_icon.png"))
    logo_label.configure(image=new_image)
    logo_label.image = new_image  # keep ref

def create_settings_button(window, theme):
    settings_image = customtkinter.CTkImage(Image.open("imgs/settings-icon.png"))
    settings_button = customtkinter.CTkButton(window, image=settings_image, text="", command=lambda: create_settings_window(window, theme))
    settings_button.grid(row=0, column=3, padx=15, pady=15, sticky="nsew")

def create_connect_button(window, stat_label):
    connect_button = customtkinter.CTkButton(window, text="Connect", command=lambda: create_connect_window(window, stat_label))
    connect_button.grid(row=0, column=2, padx=15, pady=15, sticky="nsew")

def create_logo_label(window):
    logo_image = customtkinter.CTkImage(Image.open("imgs/logo1.png"), size=(140, 50))
    video_label = customtkinter.CTkLabel(window, image=logo_image, text="")
    video_label.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

# ---------- VIRTUAL JOY ----------
def create_virtual_joy(window, label):
    joy_frame = customtkinter.CTkFrame(window, corner_radius=10)
    joy_frame.grid(row=3, column=2, columnspan=2, padx=15, pady=15, sticky="nsew")
    joy_frame.grid_columnconfigure(0, weight=1)
    joy_frame.grid_rowconfigure(0, weight=1)
    joy_frame.grid_rowconfigure(1, weight=1)

    border_frame = customtkinter.CTkFrame(joy_frame, corner_radius=30, fg_color="grey", width=200)
    border_frame.grid(row=1, column=0, pady=5)

    joy_label = customtkinter.CTkLabel(border_frame, text="Virtual JOY", text_color="white")
    joy_label.grid(row=0, column=0, padx=15, pady=5, sticky="nsew")
    joystick_instance = JoystickModule(border_frame)
    joystick_instance.joy_init()

    k_ene = tk.BooleanVar()
    keyboard_input_enable = customtkinter.CTkSwitch(joy_frame, variable=k_ene, text="Enable keyboard", command=lambda: toggle_teleop())
    keyboard_input_enable.grid(row=0, column=0, padx=20, pady=20, sticky=tk.W)

    keymap_frame = customtkinter.CTkFrame(label,fg_color="transparent",corner_radius=10, bg_color="transparent")
    label.grid_propagate(False)
    keymap_frame.grid(row=0, column=0,padx=9, pady=0, sticky="nw")
    keymap_frame.grid_remove()  # hidden by default

    keyboard_help_text = (
    "\n                      ╔══════════════════════════════════════════════════════════════════════╗                    \n"
      "                      ║                          Robot Control Commands                      ║                    \n"
      "                      ╠══════════════════════════════════════════════════════════════════════╣                    \n"
      "                      ║  i: Forward     ,: Backward     j: Turn Left     l: Turn Right       ║                    \n"
      "                      ║            u: Forward + Left     o: Forward + Right                  ║                    \n"
      "                      ║                      k: Stop the robot                               ║                    \n"
      "                      ║       w: Increase linear speed    e: Decrease linear speed           ║                    \n"
      "                      ║       s: Increase angular speed   d: Decrease angular speed          ║                    \n"
      "                      ╚══════════════════════════════════════════════════════════════════════╝                    \n"
)


    help_label = customtkinter.CTkLabel(
        keymap_frame, text=keyboard_help_text, justify="left", font=("Courier", 14)
    )
    help_label.pack(padx=5, pady=5)

    def toggle_teleop():
        k_enable = k_ene.get()
        global teleop_thread

        if k_enable:
            start_teleop_thread()
            keymap_frame.grid()  # always show keymap
            label.configure(state=tk.NORMAL)
            label.insert(tk.END, "\nKeyboard enabled")
            label.configure(state=tk.DISABLED)
        else:
            stop_teleop_thread()
            keymap_frame.grid_remove()
            label.configure(state=tk.NORMAL)
            label.insert(tk.END, "\nKeyboard disabled")
            label.configure(state=tk.DISABLED)


# ---------- STATUS POLLING THREAD ----------
def update_robot_data_http(robot_ip):
    global battery_logo, battery_info, connection_qty, status_info, stop_flag
    Link = check_connection(robot_ip)
    while Link and not stop_flag:
        try:
            robot_state = get_data(robot_ip)
        except Exception as e:
            print(f"Error in get_data: {e}")
            stop_flag = True
            break

        battery_status = robot_state[1]
        wifi_data = robot_state[0]
        status_data = robot_state[2]

        if battery_info is not None:
            if battery_status:
                update_battery_status(battery_logo, battery_info, battery_status)
            else:
                battery_info.configure(text="battery info n.a.")

        if connection_qty is not None:
            if wifi_data is not None:
                connection_qty.configure(text=f"{wifi_data} dBm")
            else:
                connection_qty.configure(text="n.a")

            if status_data == "success":
                status_info.configure(text="Receiving data...")
            else:
                status_info.configure(text="Robot not connected")

        time.sleep(5)

def start_status_thread(robot_ip):
    global stop_flag
    stop_flag = False
    update_thread = threading.Thread(target=update_robot_data_http, args=(robot_ip,), daemon=True)
    update_thread.start()

# ---------- UPPER BAR ----------
def create_upper_frame(window, battery, rssi,ip):
    global status_info, battery_logo, battery_info, connection_qty
    status=check_connection(ip)
    status_info, battery_logo, battery_info, connection_qty = create_status_bar(window, battery, rssi,status)
    create_connect_button(window, status_info)
    auto_connect_robot(status_info,ip)

# ---------- SERIAL CONNECTION ----------
def create_lora_connect_window(window, stat_label):

    def close_connect_window():
        connect_window.destroy()

    def connect_to_lora(porta, baud):
        if check_lora_connection(porta, baud) is True:
            stat_label.configure(text="Robot connected")
            lora_connection()
            lora_receiver_thread()
            close_connect_window()
        else:
            connection_error_label.configure(text="Connection error")

    connect_window = tk.Toplevel()
    connect_window.title("Connect a robot")
    connect_window.geometry("550x400")

    connection_error_uplabel = customtkinter.CTkLabel(connect_window, text="Porta")
    connection_error_uplabel.grid(row=0, column=0, padx=10, pady=5)

    porte = find_serial_ports()

    connection_error_label = customtkinter.CTkLabel(connect_window, text="")
    connection_error_label.grid(row=2, column=0, padx=10, pady=5)

    port_entry = customtkinter.CTkComboBox(connect_window, values=porte, state="readonly")
    port_entry.grid(row=0, column=1, padx=20, pady=10)
    port_entry.set("Porta")

    connection_error_uplabel = customtkinter.CTkLabel(connect_window, text="Baud rate")
    connection_error_uplabel.grid(row=1, column=0, padx=10, pady=5)

    baud_entry = customtkinter.CTkComboBox(
        connect_window,
        values=["110", "150", "300", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"],
        state="readonly"
    )
    baud_entry.grid(row=1, column=1, padx=20, pady=10)
    baud_entry.set("9600")

    def try_lora_connection():
        baud = baud_entry.get()
        porta = port_entry.get()
        connect_to_lora(porta, baud)

    lora_button = customtkinter.CTkButton(connect_window, text="Connect", command=try_lora_connection)
    lora_button.grid(row=3, column=1, padx=10, pady=10)

def create_lora_connect_button(window, status_info):
    connect_button = customtkinter.CTkButton(window, text="Connect", command=lambda: create_lora_connect_window(window, status_info))
    connect_button.grid(row=0, column=2, padx=15, pady=15, sticky="nsew")

# main.py
import sys
import customtkinter
import signal
from gui import *
from config_manager import *
from lora_plugin import *
import os

customtkinter.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green
customtkinter.set_widget_scaling(1.2)# widget dimensions and text size

def create_gui(app,ip,Type,battery,rssi,theme,joy_mod,slider,btn_mode,sw_mode,btn_label,sw_labels):

    create_settings_button(app,theme)

    if Type=="http":
        print(ip)
        create_upper_frame(app,battery,rssi,ip)

        main_frame, main_label=create_main_label(app)
        update_label(main_frame, main_label)
        create_lateral_frame(app,main_label,slider,btn_mode,sw_mode,btn_label,sw_labels)
        create_logo_label(app)
        create_virtual_joy(app,main_label) 

    elif Type=="websocket":
        print(ip)
        WS_connection() 
        create_upper_frame(app,battery,rssi,ip)

        main_frame, main_label=create_main_label(app)
        update_label(main_frame, main_label)
        create_lateral_frame(app,main_label,slider,btn_mode,sw_mode,btn_label,sw_labels)
        create_logo_label(app)
        create_virtual_joy(app,main_label) 

    
    elif Type=="lora":
        main_frame, main_label=create_main_label(app)
        update_label(main_frame, main_label)
        create_lateral_frame(app,main_label,slider,btn_mode,sw_mode,btn_label,sw_labels)
        create_logo_label(app)
        create_virtual_joy(app,main_label)
        status_info, battery_logo, battery_info,connection_qty=create_status_bar(app,battery,rssi)        
        create_lora_connect_button(app,status_info)

        
    
    app.protocol("WM_DELETE_WINDOW", lambda: on_closing(app))
    app.deiconify()
    app.state("normal")

def on_closing(window):
    stop_teleop_thread()
    stop_joypad_thread()
    stop_update_thread()
    window.destroy()

def choose_configuration():
    app = customtkinter.CTk()

    recent_configs = load_recent_configurations()
    theme_setting = load_recent_settings()
    preferences = theme_setting.get('preferences', {})
    dark_mode_value = preferences.get('dark_mode', 2)
    joy_mod = preferences.get('joypad_mod', 1)
    theme = tk.IntVar(value=dark_mode_value)
    if dark_mode_value==0:
        customtkinter.set_appearance_mode("light")  # Modes: system (default), light, dark
    if dark_mode_value==1:
        customtkinter.set_appearance_mode("dark")
    else:
        customtkinter.set_appearance_mode("default")

    def maximize_window():
        if os.name == 'posix':
            app.attributes("-zoomed", True)
        else:
            app.state("zoomed")
  
    app.grid_columnconfigure(0, weight=2)
    app.grid_columnconfigure(1,weight=20)
    app.grid_columnconfigure(2,weight=1)
    app.grid_columnconfigure(3,weight=1)
    app.grid_rowconfigure(1, weight=5)
    app.grid_rowconfigure(2, weight=4)
    app.grid_rowconfigure(3, weight=2)

    app.withdraw()

    config_selection_window = customtkinter.CTkToplevel()
    window_width = 1000
    window_height = 500

    screen_width = config_selection_window.winfo_screenwidth()
    screen_height = config_selection_window.winfo_screenheight()

    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)

    config_selection_window.geometry(f"{window_width}x{window_height}+{x}+{y}")    
    config_selection_window.title("Rover-pilot")

    logo_image = Image.open("imgs/LOGO.png")
    ctk_logo_image = customtkinter.CTkImage(logo_image,size=(400,400))
    logo_label = customtkinter.CTkLabel(config_selection_window, image=ctk_logo_image, text="")
    logo_label.image = ctk_logo_image  # avoid garbage collection
    logo_label.grid(row=0, column=0, padx=0, pady=0,rowspan=6, sticky="nsew")

    config_label = customtkinter.CTkLabel(config_selection_window, text="Welcome to rover pilot            V2.0")
    config_label.grid(row=2, column=1, padx=20, pady=5, sticky="nw")

    config_combobox = customtkinter.CTkComboBox(config_selection_window)
    names_array = [config['name'] for config in recent_configs]
    config_combobox.configure(values=names_array)
    config_combobox.set(names_array[0])  
    config_combobox.grid(row=3, column=1, padx=20, pady=15, sticky="nw")


    def refresh_config_combobox(config_combobox):

        recent_configs = load_recent_configurations()
        names_array = [cfg['name'] for cfg in recent_configs]
        ids_array   = [cfg['id']   for cfg in recent_configs]

        current_values = list(config_combobox.cget("values"))
        current_selection = config_combobox.get()

        config_combobox.configure(values=names_array)

        list_changed = names_array != current_values
        selection_renamed = current_selection and current_selection not in names_array

        if list_changed or selection_renamed:
            if names_array:
                config_combobox.set(names_array[0])
        else:
            if current_selection in names_array:
                config_combobox.set(current_selection)
            elif names_array:
                config_combobox.set(names_array[0])

        return recent_configs, names_array, ids_array

    def apply_configuration():
        recent_configs, names_array, ids_array = refresh_config_combobox(config_combobox)
        selected_name = config_combobox.get()
        selected_id   = ids_array[names_array.index(selected_name)]
        selected_cfg  = next(cfg for cfg in recent_configs if cfg["id"] == selected_id)

        create_gui(
            app,
            selected_cfg['ip'],
            selected_cfg['type'],
            selected_cfg['battery'],
            selected_cfg['rssi'],
            theme,
            joy_mod,
            selected_cfg['slider'],
            selected_cfg.get('btn_count', 0),
            selected_cfg.get('sw_count', 0),
            selected_cfg.get('btn_labels', []),
            selected_cfg.get('sw_labels', [])
        )
        maximize_window()
        config_selection_window.destroy()



    apply_button = customtkinter.CTkButton(config_selection_window, text="Start driving", command=apply_configuration)
    apply_button.grid(row=3, column=2, padx=20, pady=15, sticky="nw")

    new_conf_button = customtkinter.CTkButton(
    config_selection_window,
    text="New Config",
    command=lambda: new_config_window(
        config_selection_window,
        on_close_callback=lambda: refresh_config_combobox(config_combobox)
    )
    )

    def on_edit_config():
        recent_configs, names_array, ids_array = refresh_config_combobox(config_combobox)
        selected_name = config_combobox.get()
        selected_cfg = next((cfg for cfg in recent_configs if cfg["name"] == selected_name), None)
        if selected_cfg:
            edit_config_window(
                config_selection_window,
                config_id=selected_cfg["id"],
                on_close_callback=lambda: refresh_config_combobox(config_combobox)
            )

    edit_conf_button = customtkinter.CTkButton(
        config_selection_window,
        text="Edit configs",
        command=on_edit_config
    )

    new_conf_button.grid(row=4, column=1, padx=20, pady=15, sticky="nw")
    edit_conf_button.grid(row=4, column=2, padx=20, pady=15, sticky="nw")

    config_selection_window.protocol("WM_DELETE_WINDOW", lambda: on_closing(app))
    app.mainloop()

def on_exit(signum, frame):
    print("Exiting...")
    sys.exit(0)


from headless import start_headless_teleop

def main():
    headless_mode = "--headless" in sys.argv
    signal.signal(signal.SIGINT, on_exit)

    if headless_mode:
        print("=== Headless Teleop Mode ===")
        ip = input("Robot IP: ").strip()
        protocol = input("Protocol [http/websocket/lora/espnow]: ").strip().lower() or "http"
        esp_port = input("ESPNow port (if used, e.g., /dev/ttyUSB0): ").strip() or "COM3"
        start_headless_teleop(ip, protocol, esp_port)
    else:
        choose_configuration()


if __name__ == "__main__":
    main()
 
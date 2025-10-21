import serial
import serial.tools.list_ports
import time
from enum import Enum
from Lora_lib import LoRaE220
try:
    from lora_e220_operation_constant import ResponseStatusCode
    LORA_AVAILABLE = True
except ModuleNotFoundError:
    ResponseStatusCode = None
    LORA_AVAILABLE = False
from datetime import datetime
import threading
import json

last_stop_command_time = 0
last_command_time=0
last_linear_speed=0 
last_angular_speed=0
lora=None

confirmation_lock = threading.Lock()
confirmation_received = False


def find_serial_ports():
    porte_seriali = serial.tools.list_ports.comports()
    porte_disponibili = []
    for porta in porte_seriali:
        porte_disponibili.append(porta.device)
    return porte_disponibili

def check_lora_connection(porta_seriale,baud):
    try:
        code=lora_setup(porta_seriale,baud)
        if code == 'Success':
            print("LoRa device connected.")
            return True
        else:
            print("Error in connecting the device")
            return False
    except serial.SerialException:
        print("Error in serial com.")
        return False

def lora_setup(porta_seriale,baud):
    global lora
    loraSerial = serial.Serial(porta_seriale, baudrate=9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS)
    lora = LoRaE220('400T22D', loraSerial)
    code = lora.begin()
    response=ResponseStatusCode.get_description(code)
    #print("Initialization: {}", ResponseStatusCode.get_description(code))
    return response

def send_vel_command_to_lora(velocita_lineare, velocita_angolare):
    global lora
    comando = "V,{},{}".format(velocita_lineare, velocita_angolare)
    lora.send_fixed_message(0x01, 0x02, 26, comando)
    
def lora_vel_command(velocita_lineare,velocita_angolare):
    global last_linear_speed, last_angular_speed, last_stop_command_time,last_command_time

    if velocita_lineare == 0 and velocita_angolare == 0:
        current_time = time.time()
        if current_time - last_stop_command_time < 0.3:
            print("Duty cycle limit")
            return
        else:
            send_vel_command_to_lora(0, 0)
            last_stop_command_time = current_time
            last_linear_speed = 0
            last_angular_speed = 0
            return
    elif abs(velocita_lineare - last_linear_speed) >= 0.19 or abs(velocita_angolare - last_angular_speed) >= 0.19:
        current_time = time.time()
        if current_time - last_command_time < 0.3:
            print("cmd not sended")
            return
        else:             
            send_vel_command_to_lora(velocita_lineare, velocita_angolare)
            last_command_time = current_time
            last_linear_speed = velocita_lineare
            last_angular_speed = velocita_angolare
            return
    else:
        print("no new cmd")
    
def send_cam_command_to_lora(camera):
    global lora,confirmation_received
    comando = "C,{}".format(camera)
    lora.send_fixed_message(0x01, 0x02, 26, comando)

def send_nav_command_to_lora(aut_nav_status):
    global lora, confirmation_received
    comando = "S,{}".format(aut_nav_status)
    lora.send_fixed_message(0x01, 0x02, 26, comando)
    start_time = time.time()
    while time.time() - start_time < 3:  # 3 seconds to  confirm
        with confirmation_lock:
            if confirmation_received:
                print("message received.")
                confirmation_received = False
                return
        time.sleep(0.1)
    
    print("Message NOT received.")

def pose_data(posa):
    timestamp = {
        "sec": int(time.time()),
        "nsec": int(time.time_ns() % 1_000_000_000)
    }
    transform_message = {
        "timestamp": timestamp,
        "parent_frame_id": "map",
        "child_frame_id": "base_link",
        "translation": {
            "x": posa[0],
            "y": posa[1],
            "z": posa[2],
        },
        "rotation": {
            "x": posa[3],
            "y": posa[4],
            "z": posa[5],
            "w": posa[6],
        }
    }
    return transform_message

def write_to_file(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file)

def is_float(val):
    try:
        float(val)
        return True
    except ValueError:
        return False
    
def lora_receiver():
    global lora, confirmation_received
    
    while True:
        if lora.available() > 0:
            code, value, rssi = lora.receive_message(rssi=True)
            print(value)
            print("rssi:",rssi)
            if value == "OK":
                with confirmation_lock:
                    confirmation_received = True
            elif  len(value.split(sep=","))==8:
                values=value.split(sep=",")
                if values[0] == "P" and all(is_float(val) for val in values[1:]):
                    posa=[float(values[1]),float(values[2]),float(values[3]),float(values[4]),float(values[5]),float(values[6]),float(values[7])]
                    print(posa)
                    data = pose_data(posa)

def lora_receiver_thread():
    listener_thread = threading.Thread(target=lora_receiver)
    listener_thread.daemon = True
    listener_thread.start()




"""
class ResponseStatusCode(Enum):
    E220_SUCCESS = 0
    ERR_E220_PACKET_TOO_BIG = 1
    ERR_E220_NO_RESPONSE_FROM_DEVICE = 2
    ERR_E220_DATA_SIZE_NOT_MATCH = 3

MAX_SIZE_TX_PACKET = 100

def _send_message(message, uart_instance, ADDH=0x01, ADDL=0x02, CHAN=23) -> ResponseStatusCode:
    result = ResponseStatusCode.E220_SUCCESS

    size_ = len(message.encode('utf-8'))
    if size_ > MAX_SIZE_TX_PACKET + 2:
        return ResponseStatusCode.ERR_E220_PACKET_TOO_BIG

    if ADDH is not None and ADDL is not None and CHAN is not None:
        if isinstance(message, str):
            message = message.encode('utf-8')
        dataarray = bytes([ADDH, ADDL, CHAN]) + message
        dataarray = _normalize_array(dataarray)
        lenMS = uart_instance.write(bytes(dataarray))
        size_ += 3
        print(dataarray)
        print(uart_instance)
        #print("provo invio")
    elif isinstance(message, str):
        lenMS = uart_instance.write(message.encode('utf-8'))
        #print("invio...")
    else:
        lenMS = uart_instance.write(bytes(message))
        #print("else_invio")

    if lenMS != size_:
        print("Send... len:", lenMS, " size:", size_)
        if lenMS == 0:
            result = ResponseStatusCode.ERR_E220_NO_RESPONSE_FROM_DEVICE
        else:
            result = ResponseStatusCode.ERR_E220_DATA_SIZE_NOT_MATCH
    if result != ResponseStatusCode.E220_SUCCESS:
        return result

    print("Clear buffer...")
    clean_UART_buffer(uart_instance)

    print("ok!")
    return result

def _normalize_array(data):
    normalized_data = bytearray()
    for value in data:
        normalized_data.append(value % 256)
    return normalized_data

def clean_UART_buffer(uart_instance):
    uart_instance.read_all()

"""    

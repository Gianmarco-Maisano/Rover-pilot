import requests
import keyboard
import time

robot_ip=""

def set_robot_ip(ip):
    global robot_ip
    robot_ip = ip
    return robot_ip

def send_control_command(linear, angular):
    global robot_ip
    port = 80
    control_endpoint = "/cmd"
    url = f"http://{robot_ip}:{port}{control_endpoint}"
    payload = {"linear": linear, "angular": angular}
    requests.post(url, data=payload)

def update_speed(target_linear, target_angular):
    acceleration = 0.1
    linear_speed = 0.0
    angular_speed = 0.0

    if linear_speed < target_linear:
        linear_speed = min(linear_speed + acceleration, target_linear)
    elif linear_speed > target_linear:
        linear_speed = max(linear_speed - acceleration, target_linear)

    if angular_speed < target_angular:
        angular_speed = min(angular_speed + acceleration, target_angular)
    elif angular_speed > target_angular:
        angular_speed = max(angular_speed - acceleration, target_angular)

def keyboard_teleop():
    linear_speed = 0.0
    angular_speed = 0.0
    acceleration = 0.1
    try:
        print("Use WASD to control direction, and other keys to adjust velocity.")
        print("Press 'q' to exit.")

        while True:
            key = keyboard.read_event(suppress=True).name

            if key == 'w':
                update_speed(linear_speed + acceleration, angular_speed)
            elif key == 's':
                update_speed(linear_speed - acceleration, angular_speed)
            elif key == 'a':
                update_speed(linear_speed, angular_speed + acceleration)
            elif key == 'd':
                update_speed(linear_speed, angular_speed - acceleration)
            elif key == 'z':
                update_speed(0, 0)
            elif key == 'x':
                linear_speed = max(0, linear_speed - acceleration)
                print(f"Linear speed decreased to {linear_speed}")
            elif key == 'c':
                linear_speed = min(1.0, linear_speed + acceleration)
                print(f"Linear speed increased to {linear_speed}")
            elif key == 'v':
                angular_speed = max(-1.0, angular_speed - acceleration)
                print(f"Angular speed decreased to {angular_speed}")
            elif key == 'b':
                angular_speed = min(1.0, angular_speed + acceleration)
                print(f"Angular speed increased to {angular_speed}")
            elif key == 'q':
                print("Exiting.")
                break

            send_control_command(linear_speed, angular_speed)
            print(f"linear: {linear_speed}")
            time.sleep(0.1)  

    except Exception as e:
        print(e)

    finally:
        send_control_command(0, 0)



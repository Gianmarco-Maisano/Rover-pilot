
import tkinter as tk
from robot_controller import send_robot_commands
from math import atan2, cos, sin

class JoystickModule:
    def __init__(self, JOY):
        self.JOY = JOY
        self.xscale=150
        self.yscale=150
        self.joystick_radius = self.xscale*4/5
        self.joystick_handle_radius = self.xscale*1/5
        self.joystick_center_x = self.xscale
        self.joystick_center_y = self.yscale
        self.last_linear=0
        self.last_angular=0

        self.joystick_canvas = tk.Canvas(JOY, width=self.xscale*2, height=self.yscale*2,highlightthickness=0,bg="grey")
        self.joystick_canvas.grid(row=2, column=0,padx=30, pady=10)

    def start_drag(self, event):
        self.joystick_canvas.bind('<B1-Motion>', lambda e: self.drag(e))

    def stop_drag(self, event):
        self.joystick_canvas.unbind('<B1-Motion>')
        self.draw_joystick(0, 0)
        send_robot_commands(0.0, 0.0)

    def drag(self, event):
        x = event.x - self.joystick_center_x
        y = event.y - self.joystick_center_y
        distance = (x**2 + y**2)**0.5

        if distance > self.joystick_radius:
            angle = atan2(y, x)
            x = self.joystick_radius * cos(angle)
            y = self.joystick_radius * sin(angle)


        linear_speed = -y / self.joystick_radius
        if abs(linear_speed)> 0.2:
            angular_speed = x / (self.joystick_radius)
        else:
            linear_speed=0
            angular_speed = x / (self.joystick_radius)
            
            
        joy_data = [linear_speed, angular_speed]
        if abs(linear_speed - self.last_linear) > 0.1 or abs(angular_speed - self.last_angular) > 0.1:
            send_robot_commands(*joy_data)
            self.last_linear = linear_speed
            self.last_angular = angular_speed

        self.draw_joystick(x, y)


    def draw_joystick(self, x, y):
        self.joystick_canvas.delete("joystick_handle")

        self.joystick_canvas.create_oval(
            self.joystick_center_x - self.joystick_radius,
            self.joystick_center_y - self.joystick_radius,
            self.joystick_center_x + self.joystick_radius,
            self.joystick_center_y + self.joystick_radius,
            fill="white",  # Semi-transparent gray color
            width=1
        )

        self.joystick_canvas.create_oval(
            self.joystick_center_x + x - self.joystick_handle_radius,
            self.joystick_center_y + y - self.joystick_handle_radius,
            self.joystick_center_x + x + self.joystick_handle_radius,
            self.joystick_center_y + y + self.joystick_handle_radius,
            fill="#3B8ED0",
            tags="joystick_handle"
        )

    def joy_init(self):
        self.joystick_canvas.create_oval(
            self.joystick_center_x - self.joystick_radius,
            self.joystick_center_y - self.joystick_radius,
            self.joystick_center_x + self.joystick_radius,
            self.joystick_center_y + self.joystick_radius
        )

        self.draw_joystick(0, 0)

        self.joystick_canvas.bind('<Button-1>', lambda e: self.start_drag(e))
        self.joystick_canvas.bind('<ButtonRelease-1>', lambda e: self.stop_drag(e))



    
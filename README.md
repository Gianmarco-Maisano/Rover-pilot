# Python Robot Interface

A lightweight Python interface designed for rapid prototyping of robots. This library allows you to control your robot using **HTTP**, **WebSocket**, or **LoRa** (basic implementation with **Ebyte E220** modules).  

It provides flexible control options and a configurable interface for testing and development.

---

## Features

- **Multiple Control Methods**  
  - HTTP commands  
  - WebSocket communication  
  - LoRa (Ebyte E220) for wireless control

- **Robot Motion Control**  
  - Send **linear** and **angular velocities** to the robot  
  - Supports **virtual on-screen joystick**, **keyboard**, or **physical joystick**  

- **Configurable Inputs**  
  - Up to **2 buttons** and **4 switches** can be added to the interface  
  - Fully configurable for testing different robot behaviors  

- **Headless Mode**  
  - Runs in **terminal only**  
  - Uses only keyboard input  
  - No graphical interface required  

---

## Installation

```bash
git clone https://github.com/Gianmarco-Maisano/Rover-pilot.git
cd Rover-pilot
pip install -r requirements.txt
```

## Usage

Graphics mode
```bash
  python main.py
```

Headless mode
```bash
  python main.py --headless
```


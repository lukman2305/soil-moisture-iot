# Soil Moisture IoT Project

## Project Overview
This project is part of the SRTA 3353 Machine Learning for IoT course (Academic Session 2025/2026).  
The aim is to design and implement a **hardware-based IoT solution** for **smart agriculture**.  
The system measures **soil moisture** using an ESP32 sensor and communicates the data to a **Raspberry Pi 400** via **serial GPIO (RX/TX)**.  

This project demonstrates integration between sensing, processing, decision-making, and actuator control for automated irrigation.

---

## Team Roles

| Student | Role | Responsibilities |
|---------|------|----------------|
| Student 1 | Project Coordinator / Requirements Analyst | Define problem, scope, objectives, coordinate tasks, maintain contribution log |
| Student 2 | Hardware Assembly / Sensor Integration | Wire sensors and actuators, verify hardware functionality |
| Student 3 | Firmware / Embedded System Programming | Develop Raspberry Pi firmware, implement sensor acquisition and actuator control, integrate communication protocols (MQTT/HTTP/Wi-Fi/Bluetooth) |
| Student 4 | Data Processing & Intelligence | Implement preprocessing, filtering, threshold logic, ML-based decision-making |
| Student 5 | Dashboard & Visualization | Configure Favoriot dashboard, create data visualization, implement alerts and monitoring |
| Student 6 | Testing & Documentation | Test system, prepare demo scenarios, collect evidence, compile report |

---

## Hardware Components
- **ESP32** → Reads soil moisture sensor  
- **Soil Moisture Hygrometer** → Measures soil water content  
- **Raspberry Pi 400** → Central processing unit and serial communication  
- **Relay Module + 5V Pump** → Actuator for irrigation  
- **Display (HDMI)** → Shows live readings  
- **Jumper wires & cables** → Connect all components  

---

## Software Components
- **Python 3** → Main programming language  
- **Libraries**:
  - `pyserial` → Serial communication with ESP32  
  - `RPi.GPIO` → Raspberry Pi GPIO control (for relay/pump)  
  - `Adafruit_DHT` → Temperature & humidity sensor (optional for future expansion)  
  - `requests` → HTTP communication  
  - `paho-mqtt` → MQTT communication for dashboard  
- **Git & GitHub** → Version control and collaboration  
- **Virtual Environment (`venv`)** → Isolate Python dependencies  

---

## Project Workflow

1. **Select Problem & Sensors**
   - Smart Agriculture: monitor soil moisture and automate irrigation
2. **Build Hardware Prototype**
   - ESP32 wired to soil moisture sensor
   - Relay module connected to 5V pump
3. **Develop Firmware**
   - Read ESP32 serial data on Raspberry Pi
   - Implement actuator control logic
   - Integrate communication protocols
4. **Test Sensors**
   - Verify soil moisture readings in simulation or real soil
   - Ensure pump triggers correctly
5. **Implement Dashboard / Alerts**
   - Optional: MQTT / HTTP to monitor readings remotely
6. **Document Contribution**
   - Keep logs for each student’s tasks
   - Include screenshots, diagrams, and test outputs

---

## Installation Instructions

1. **Clone repository**
```bash
git clone https://github.com/<username>/soil-moisture-iot.git
cd soil-moisture-iot
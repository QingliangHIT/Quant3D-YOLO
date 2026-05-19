import serial
import time
from serial.tools import list_ports


def find_port():
    # Get available serial ports
    ports = list_ports.comports()
    for port in ports:
        try:
            # Try opening each port
            ser = serial.Serial(
                port=port.device,  # Adjust port as needed
                baudrate=2400,  # Baud rate
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_ODD,
                stopbits=serial.STOPBITS_ONE,
                timeout=1  # Timeout duration
            )
            for i in range(10):
                send_command(ser, "run 11832\r\n")
                time.sleep(0.5)  # Wait for command processing
                if receive_response(ser, "$ready 11832$"):
                    print('Connected', port.device)
                    return ser
                else:
                    ser.close()
        except (OSError, serial.SerialException):
            # If open fails, try next port
            continue

    # If no available ports found, return None
    return None


def send_command(com, command):
    com.write(command.encode('gbk'))


def receive_response(com, expected_response):
    while com.in_waiting > 0:
        data = com.read(com.in_waiting).decode('gbk')
        if expected_response in data:
            return True
    return False


def receive_data(com):
    if com.in_waiting > 0:
        data = com.read(com.in_waiting).decode('gbk')
        return data
    return None


def receive_data_with_timeout(com, timeout=5, check_interval=0.1):
    start_time = time.time()
    last_bytes_in_waiting = 0
    data = ""

    while time.time() - start_time < timeout:
        if com.in_waiting > 0:
            new_data = com.read(com.in_waiting).decode('gbk')
            data += new_data
            last_bytes_in_waiting = com.in_waiting
        else:
            time.sleep(0.1)

        # Check if bytes change in check_interval
        time.sleep(check_interval)
        if com.in_waiting == last_bytes_in_waiting:
            return data

    return data


# Init serial
ser = find_port()
if ser:
    while True:
        send_command(ser, "\r\n")
        receive_data_with_timeout(ser)
        cmd = input("Enter command: ")
        send_command(ser, cmd + "\r\n")
        response = receive_data_with_timeout(ser)
        if response:
            print(f"Received: {response}")
    # else:
    #     print("No data received")

    # Close serial
    ser.close()
else:
    print("No serial port found.")

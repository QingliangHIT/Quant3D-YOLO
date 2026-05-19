import os
import sys
import serial
import time
from serial.tools import list_ports
import keyboard  # Import keyboard


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

    # If no ports found, return None
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


def handle_key_event(event, ser, variable_value, step_scale, in_console_mode):

    if event.event_type == keyboard.KEY_DOWN:
        if event.name == 'w':
            if not in_console_mode[0]:
                value = variable_value['pulse']
                send_command(ser, f"pulse 1 {value}\r\n")
                print(f"\rSent: pulse 1 {value}", end='', flush=True)
        elif event.name == 's':
            if not in_console_mode[0]:
                value = variable_value['pulse']
                send_command(ser, f"pulse 0 {value}\r\n")
                print(f"\rSent: pulse 0 {value}", end='', flush=True)

        elif event.name == 'd':
            if not in_console_mode[0]:
                variable = iter(variable_value)
                idx = variable_value['idx']
                key = None
                for i in range(variable_value['idx'] + 1):
                    key = next(variable)
                if key:
                    variable_value[key] += step_scale[idx]
                    if key == 'keep':
                        send_command(ser, f"set -k {variable_value[key]}\r\n")
                        print(f"\rSent: set -k {variable_value[key]}", end='')
                    else:
                        print(f"\rset {key}: {variable_value[key]}", end='')

        elif event.name == 'a':
            if not in_console_mode[0]:
                variable = iter(variable_value)
                idx = variable_value['idx']
                key = None
                for i in range(variable_value['idx'] + 1):
                    key = next(variable)
                if key:
                    variable_value[key] -= step_scale[idx]
                    if key == 'keep':
                        send_command(ser, f"set -k {variable_value[key]}\r\n")
                        print(f"\rSent: set -k {variable_value[key]}", end='')
                    else:
                        print(f"\rset {key}: {variable_value[key]}", end='')

        elif event.name == 'right':
            if not in_console_mode[0]:
                key = None
                variable = iter(variable_value)
                for i in range(variable_value['idx'] + 1):
                    key = next(variable)
                if key:
                    idx = variable_value['idx']
                    step_scale[idx] += 10**step_scale[2]
                    print(f"\rStep size({key}) increased to {step_scale[idx]}", end='')
        elif event.name == 'left':
            if not in_console_mode[0]:
                key = None
                variable = iter(variable_value)
                for i in range(variable_value['idx'] + 1):
                    key = next(variable)
                if key:
                    idx = variable_value['idx']
                    step_scale[idx] -= 10**step_scale[2]
                    if step_scale[idx] < 0:
                        step_scale[idx] = 0
                    print(f"\rStep size({key}) decreased to {step_scale[idx]}", end='')
        elif event.name == 'up':
            if not in_console_mode[0]:
                step_scale[2] += 1
                print(f"\rStep rate increased to {step_scale[2]}", end='')
        elif event.name == 'down':
            if not in_console_mode[0]:
                step_scale[2] -= 1
                print(f"\rStep rate increased to {step_scale[2]}", end='')
        elif event.name == 'k':
            if not in_console_mode[0]:
                receive_data(ser)
                send_command(ser, "get k\r\n")
                response = receive_data_with_timeout(ser)
                if response:
                    keep_value = int(response.split(': ')[1])
                    print(f"\rCurrent keep value: {keep_value}", end='')
        elif event.name == 'e':
            if not in_console_mode[0]:
                receive_data(ser)
                send_command(ser, "get e\r\n")
                response = receive_data_with_timeout(ser)
                if response:
                    ENA_status = response.split(': ')[1].startswith('true')
                    if ENA_status is True:
                        send_command(ser, "set -e 0\r\n")
                    else:
                        send_command(ser, "set -e 1\r\n")
                    print(f"\rCurrent ENA status: {ENA_status}", end='')
        elif event.name == 'c':
            if not in_console_mode[0]:
                key = None
                variable_value['idx'] += 1
                if variable_value['idx'] >= len(variable_value)-1:
                    variable_value['idx'] = 0
                variable = iter(variable_value)
                for i in range(variable_value['idx']+1):
                    key = next(variable)
                if key:
                    value = variable_value[key]
                    print(f"\rSwitched to {key}: {value}.", end='', flush=True)

        elif event.name == 'ctrl':
            if not in_console_mode[0]:
                print("\rEntering command mode. Type 'exit' to return to key control.\nEnter command: ", end='')
                in_console_mode[0] = True
            else:
                print("\rExiting command mode.", end='')
                in_console_mode[0] = False
                return variable_value, step_scale
        elif event.name == 'q':  # Handle 'q' key
            if not in_console_mode[0]:
                print("\rExiting...", end='', flush=True)
                keyboard.unhook_all()  # Remove all keyboard hooks
                ser.close()  # Close serial
                sys.exit(0)  # Exit program
        if in_console_mode[0]:

            if event.name == 'enter':
                cmd = input()

                if cmd.lower() == 'exit':
                    print("\rExiting command mode.", end='')
                    in_console_mode[0] = False
                elif len(cmd.lower()) == 1:
                    receive_data(ser)
                    send_command(ser, "get "+cmd.lower()+"\r\n")
                    response = receive_data_with_timeout(ser)
                    if response:
                        ret = response.split(': ')[1]
                        print(f"\rReceived: {ret}", end='')
                elif cmd.startswith('k '):
                    try:
                        value = int(cmd.split(' ')[1])
                        send_command(ser, f"set -k {value}\r\n")
                        print(f"\rSent: set -k {value}", end='')
                    except (ValueError, IndexError):
                        print("\rInvalid command format. Use 'k <value>'.", end='')
                elif cmd.startswith('w '):
                    try:
                        value = int(cmd.split(' ')[1])
                        send_command(ser, f"pulse 1 {value}\r\n")
                        print(f"\rSent: pulse 1 {value}", end='')
                    except (ValueError, IndexError):
                        print("\rInvalid command format. Use 'w <value>'.", end='')
                elif cmd.startswith('s '):
                    try:
                        value = int(cmd.split(' ')[1])
                        send_command(ser, f"pulse 0 {value}\r\n")
                        print(f"\rSent: pulse 0 {value}", end='')
                    except (ValueError, IndexError):
                        print("\rInvalid command format. Use 's <value>'.", end='')
                # else:
                else:
                    receive_data(ser)
                    send_command(ser, cmd + "\r\n")
                    response = receive_data_with_timeout(ser)
                    if response:
                        print(f"\rReceived: {response}", end='')

                    # print("\rUnknown command. Use 'k <value>', 'w <value>', or 's <value>'.", end='')
    return variable_value, step_scale


if __name__ == '__main__':
    # Init serial
    ser = find_port()
    if ser:
        receive_data(ser)
        send_command(ser, "get k\r\n")
        response = receive_data_with_timeout(ser)
        if response:
            keep_value = int(response.split(': ')[1])
            keep_value = [keep_value]  # Init keep value
        else:
            keep_value = [1000]
        send_command(ser, "get e\r\n")
        response = receive_data_with_timeout(ser)
        if response:
            ENA_status = response.split(': ')[1].startswith('true')

        step_scale = [100, 100, 2]  # Init step size
        in_console_mode = [False]  # Init console mode flag

        receive_data(ser)
        send_command(ser, "get k\r\n")
        response = receive_data_with_timeout(ser)
        if response:
            keep_value = int(response.split(': ')[1])

        variable_value = {'keep': keep_value, 'pulse': 400, 'idx': 0}  # Init pulse value
        # Register key listener
        # keyboard.hook(lambda event: handle_key_event(event, ser, keep_value, step_scale, in_console_mode))
        # print("Listening for keyboard input.", end='')
        keyboard.hook(
            lambda event: handle_key_event(event, ser, variable_value, step_scale, in_console_mode))
        print("Listening for keyboard input.", end='', flush=True)

        try:
            keyboard.wait()  # Keep program running
        except KeyboardInterrupt:
            print("\rExiting...")
        finally:
            ser.close()
    else:
        print("No serial port found.")

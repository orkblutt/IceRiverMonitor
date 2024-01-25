'''
IceRiver Kaspa Miners Monitor
by
Orkblutt
'''
import sys
import socket
import json
import curses
import textwrap
import time

def send_tcp_request(ip, port, request, timeout=2.0):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, port))
        s.sendall(request)
        s.settimeout(timeout)
        response = b""
        try:
            while True:
                part = s.recv(1024)
                if not part:
                    break
                response += part
        except socket.timeout:
            pass
        return response

def get_chip_data(server_ip, server_port):
    request_data = b'{"id":"getchipinfo"}\r\n'
    response_data = send_tcp_request(server_ip, server_port, request_data)
    response_str = response_data.decode('utf-8')
    response_json = json.loads(response_str)
    chips = response_json.get('ret', {}).get('chips', [])
    return [chip for chip in chips if chip['temp'] != 0 or chip['voltage'] != 0.0 or chip['pll'] != 0]

def get_board_power_data(server_ip, server_port):
    request_data = b'{"id":"boardpow"}\r\n'
    response_data = send_tcp_request(server_ip, server_port, request_data)
    response_str = response_data.decode('utf-8')
    return json.loads(response_str).get('ret', {})

def get_fan_data(server_ip, server_port):
    request_data = b'{"id":"fan"}\r\n'
    response_data = send_tcp_request(server_ip, server_port, request_data)
    response_str = response_data.decode('utf-8')
    return json.loads(response_str).get('ret', {}).get('fans', [])

def get_state_data(server_ip, server_port):
    request_data = b'{"id":"state"}\r\n'
    response_data = send_tcp_request(server_ip, server_port, request_data)
    response_str = response_data.decode('utf-8')
    return json.loads(response_str).get('ret', {})

def get_color_for_temp(temp):
    if temp > 95:
        return 3  # Red
    elif temp > 90:
        return 4  # Orange
    else:
        return 2  # Green

def get_color_for_voltage(voltage):
    if 0.46 <= voltage <= 0.5:
        return 2  # Green
    else:
        return 3  # Red
    
def get_color_for_state(state):
    if state == True:
        return 2  # Green
    else:
        return 3  # Red
    
def get_color_for_rejected(reject):
    if reject > 10.0:
        return 3  # Red
    elif reject > 3:
        return 4  # Orange
    else:
        return 2  # Green
    
def draw_box(stdscr, start_y, start_x, height, width, title=""):
    # Box Drawing Characters
    horizontal = '═'
    vertical = '║'
    top_left = '╔'
    top_right = '╗'
    bottom_left = '╚'
    bottom_right = '╝'

    # Ensure the title is not longer than the box width
    max_title_length = width - 4  # Adjust 4 for padding and box lines
    if len(title) > max_title_length:
        title = title[:max_title_length-1] + '…'  # Truncate and add ellipsis

    # Draw Top Border
    stdscr.addstr(start_y, start_x, top_left + (horizontal * (width - 2)) + top_right)

    # Draw Middle Section
    for y in range(start_y + 1, start_y + height - 1):
        stdscr.addstr(y, start_x, vertical)
        stdscr.addstr(y, start_x + width - 1, vertical)

    # Draw Bottom Border
    stdscr.addstr(start_y + height - 1, start_x, bottom_left + (horizontal * (width - 2)) + bottom_right)

    # Draw Title
    if title:
        # Title padding for aesthetics
        title_start = start_x + (width // 2 - len(title) // 2)
        stdscr.addstr(start_y, title_start, f"{title}")
        
        
def display_info(stdscr, server_ip, server_port):
    # Initialize color pairs
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)  # General information
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Green
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Red
    curses.init_pair(4, 209, curses.COLOR_BLACK)   # Orange
    curses.init_pair(5, curses.COLOR_BLUE, curses.COLOR_BLACK) # Blue

    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Make getch() non-blocking
    
    first_iter = True
    
    while True:
        if first_iter:
            stdscr.clear()
            stdscr.addstr(0, 1, f"Fetching informations from {server_ip}...", curses.color_pair(5))
            stdscr.refresh()
            first_iter = False
        
        # Fetching datas. Since the miner doesn't close the connexion after the request we use 2s timeout for each request
        # This is blocking for 4x2s
        chips = get_chip_data(server_ip, server_port)
        board_pow = get_board_power_data(server_ip, server_port)
        fans = get_fan_data(server_ip, server_port)
        state = get_state_data(server_ip, server_port)
        
        stdscr.clear()
        
        # Calculate dimensions and positions
        max_y, max_x = stdscr.getmaxyx()
        box_width = max_x - 2

         # Display board power data
        stdscr.addstr(1, 2, "HR: ", curses.color_pair(1))
        status = "OK" if state.get('pow', False) else "Not OK"
        stdscr.addstr(status, curses.color_pair(get_color_for_state(state.get('pow', False))))
        stdscr.addstr(" Network: ", curses.color_pair(1))
        status = "OK" if state.get('net', False) else "Not OK"
        stdscr.addstr(status, curses.color_pair(get_color_for_state(state.get('net', False))))
        stdscr.addstr(" Fans: ", curses.color_pair(1))
        status = "OK" if state.get('fan', False) else "Not OK"
        stdscr.addstr(status, curses.color_pair(get_color_for_state(state.get('fan', False))))
        stdscr.addstr(" Temperature: ", curses.color_pair(1))
        status = "OK" if state.get('temp', False) else "Not OK"
        stdscr.addstr(status, curses.color_pair(get_color_for_state(state.get('temp', False))))
                
        stdscr.addstr(2, 2, "Real-Time Hashrate: ", curses.color_pair(1))
        stdscr.addstr(f"{board_pow.get('rtpow', 'N/A')}\n", curses.color_pair(1))
        stdscr.addstr(3, 2, "Average Hashrate: ", curses.color_pair(1))
        stdscr.addstr(f"{board_pow.get('avgpow', 'N/A')}\n", curses.color_pair(1))
        stdscr.addstr(4, 2, "Rejected Shares: ", curses.color_pair(1))
        stdscr.addstr(f"{board_pow.get('reject', 'N/A')}\n", curses.color_pair(get_color_for_rejected(board_pow.get('reject'))))
        stdscr.addstr(5, 2, "Runtime: ", curses.color_pair(1))
        stdscr.addstr(f"{board_pow.get('runtime', 'N/A')}\n", curses.color_pair(1))

        chip_count = len(chips)
        if chip_count > 0:
            min_temp = min(chips, key=lambda x: x['temp'])
            max_temp = max(chips, key=lambda x: x['temp'])
            min_volt = min(chips, key=lambda x: x['voltage'])
            max_volt = max(chips, key=lambda x: x['voltage'])

            stdscr.addstr(8, 2, "Number of Chips: ", curses.color_pair(1))
            stdscr.addstr(str(chip_count), curses.color_pair(1))
            stdscr.addstr(9, 2, "Min Temp: ", curses.color_pair(1))
            stdscr.addstr(str(min_temp['temp']), curses.color_pair(get_color_for_temp(min_temp['temp'])))
            stdscr.addstr(f"°C (Chip No: {min_temp['no']})\n", curses.color_pair(1))
            stdscr.addstr(10, 2, "Max Temp: ", curses.color_pair(1))
            stdscr.addstr(str(max_temp['temp']), curses.color_pair(get_color_for_temp(max_temp['temp'])))
            stdscr.addstr(f"°C (Chip No: {max_temp['no']})\n", curses.color_pair(1))
            stdscr.addstr(11, 2, "Min Voltage: ", curses.color_pair(1))
            stdscr.addstr(f"{min_volt['voltage']}", curses.color_pair(get_color_for_voltage(min_volt['voltage'])))
            stdscr.addstr(f"V (Chip No: {min_volt['no']})\n", curses.color_pair(1))
            stdscr.addstr(12, 2, "Max Voltage: ", curses.color_pair(1))
            stdscr.addstr(f"{max_volt['voltage']}", curses.color_pair(get_color_for_voltage(max_volt['voltage'])))
            stdscr.addstr(f"V (Chip No: {max_volt['no']})\n", curses.color_pair(1))
        else:
            stdscr.addstr(8, 2, "No chips data available", curses.color_pair(3))
            
         # Display fan speeds
        for i, fan_speed in enumerate(fans):
            stdscr.addstr(15 + i, 2, f"Fan {i+1} Speed: {fan_speed} RPM", curses.color_pair(1))

        # Draw boxes
        draw_box(stdscr, 0, 0, 7, box_width, f" Miner {server_ip} General Info ")
        draw_box(stdscr, 7, 0, 7, box_width, " Chips Info ")
        draw_box(stdscr, 14, 0, 6, box_width, " Fans Speed ")

        stdscr.refresh()
        time.sleep(30)  # Refresh every 30 seconds

        # Exit loop if 'q' is pressed
        if stdscr.getch() == ord('q'):
            break

def main():
    if len(sys.argv) < 3:
        print("Usage: python script.py <server_ip> <server_port>")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    curses.wrapper(display_info, server_ip, server_port)

if __name__ == "__main__":
    main()

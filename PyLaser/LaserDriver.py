# -*- coding: utf-8 -*-
"""
Laser Plotter Driver
"""

import serial
import numpy as np
import argparse
import time

####################### settings ###########################################
arduino_serial_port = '/dev/ttyACM0'
arduino_serial_baudrate = 115200
y_steps_per_mm = 11.71
x_steps_per_mm = 333.33
resolution = 150 #dpi
motor_ids = {
             'x': 'A',
             'y': 'B'
             }
############################################################################

resolution_mm = resolution/25.4
ser = None

def execute_move(steps):
    global ser
    ser.write(b'R')
    res = ser.readline().strip()
    if res != b'R':
        raise RuntimeError('Engraver not ready.')
    counter = 0
    while counter < len(steps):
        motor, position = steps[counter]
        cmd = bytes('X{:s}{:d}\n'.format(motor_ids[motor], position), 'ASCII')
        print(cmd)
        ser.write(cmd)
        time.sleep(0.025)
        res = ser.read()
        
        if res == b'D':
            counter += 1
        elif res == b'E':
            print('Error executing move. Repeating')
            #raise RuntimeError('Error executing move')
        else:
            raise RuntimeError('Unknown return code from engraver: {:s}'.format(res.decode('ASCII')))

def move_linear(target_position, engrave=False):
    """
    target_position : (y, x) coordinates to move to in mm
    engrave : whether to move as fast as possible or to engrave (move slowly)
    """
    y, x = target_position
    current_steps_x = 0
    current_steps_y = 0
    current_x = 0 # in mm
    current_y = 0 # in mm
    
    if engrave:
        #x_num_steps = x*x_steps_per_mm
        #y_num_steps = y*y_steps_per_mm
        x_num_pixels = x*resolution_mm
        y_num_pixels = y*resolution_mm
        print(x_num_pixels, y_num_pixels)
        x_steps_per_pixel = x_steps_per_mm/resolution_mm
        y_steps_per_pixel = y_steps_per_mm/resolution_mm
        print(x_steps_per_pixel, y_steps_per_pixel)
        pixel_ratio = x_num_pixels / y_num_pixels
        print(pixel_ratio)
        x_pixels_moved = 0
        y_pixels_moved = 0
        steps = []
        for i in range(int(np.ceil(x_num_pixels + y_num_pixels))):
            if np.rint(i*pixel_ratio) > x_pixels_moved and x_pixels_moved < x_num_pixels:
                x_pixels_moved += 1
                steps.append(('x', int(np.rint((x_pixels_moved)*x_steps_per_pixel))))
            if np.rint(i/pixel_ratio) > y_pixels_moved and y_pixels_moved < y_num_pixels:
                y_pixels_moved += 1
                steps.append(('y', int(np.rint((y_pixels_moved)*y_steps_per_pixel))))
    else:
        steps = [('x', int(np.rint(x*x_steps_per_mm))), ('y', int(np.rint(y*y_steps_per_mm)))]
    
    #print(steps)
    execute_move(steps)

def parse_line(line):
    start_x = line.find('X')
    end_x = line.find(' ', start_x)
    if end_x == -1:
        end_x = None
    x = float(line[start_x+1:end_x])
    start_y = line.find('Y')
    end_y = line.find(' ', start_y)
    if end_y == -1:
        end_y = None
    y = float(line[start_y+1:end_y])
    return (y, x)

def process_line(line: str):
    line = line.upper()
    line = line.strip()
    if line.startswith('G00'):
        position = parse_line(line)
        move_linear(position, engrave=False)
    elif line.startswith('G01'):
        position = parse_line(line)
        move_linear(position, engrave=True)
    else:
        print('unrecognized command')
        
def process_file(path: str):
    raise NotImplementedError

def main():
    global ser
    parser = argparse.ArgumentParser(description='GCode interpreter')
    parser.add_argument('-l', '--line', help='interprets a single line of GCode')
    parser.add_argument('-f', '--file', help='interprets a GCode File')
    args = parser.parse_args()
    ser = serial.Serial(arduino_serial_port, arduino_serial_baudrate, timeout=1)
    res = b''
    while not res == b'R':
        ser.write(b'R')
        res = ser.readline().strip()
        
    ser.write(b'V0\n')
    res = ser.readline().strip()
    if res != b'D':
        print(res)
        raise RuntimeError('Could not set verbosity')
    ser.timeout = 10
    if args.line is not None:
        process_line(args.line)
    elif args.file is not None:
        process_file(args.file)
    if ser is not None:
        ser.close()
    
if __name__ == '__main__':
    main()

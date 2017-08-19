# -*- coding: utf-8 -*-
"""
Laser Plotter Driver
"""

import serial
import numpy as np
import argparse
import time
import os

####################### settings ###########################################
arduino_serial_port = '/dev/ttyACM0'
arduino_serial_baudrate = 115200
y_steps_per_mm = 11.77
x_steps_per_mm = 378.21
resolution = 150 #dpi
motor_ids = {
             'x': 'A',
             'y': 'B'
             }
############################################################################

resolution_mm = resolution/25.4
ser = None
current_steps_x = 0
current_steps_y = 0

def execute_move(steps):
    global ser
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.write(b'R')
    res = ser.read()
    if res != b'R':
        print(res)
        raise RuntimeError('Engraver not ready.')
    counter = 0
    while counter < len(steps):
        #ser.reset_input_buffer()
        #ser.reset_output_buffer()
        motor, position = steps[counter]
        cmd = bytes('X{:s}{:d}\n'.format(motor_ids[motor], position), 'ASCII')
        print(cmd)
        ser.write(cmd)
        #res = ser.readline()
        #print(res)
        res = ser.read()
        print(res)
        
        if res == b'X':
            counter += 1
        elif res == b'E':
            print('Error executing move. Repeating')
            #raise RuntimeError('Error executing move')
        else:
            raise RuntimeError('Unknown return code from engraver: {:s}'.format(res.decode('ASCII')))

def get_current_steps(motor):
    global ser
    ser.reset_input_buffer()
    line = bytearray()
    ser.write(b'P' + bytearray(motor_ids[motor], 'ASCII'))
    while True:
        b = ser.read()
        if not b:
            raise RuntimeError('No data received')
        if b == b'E':
            raise RuntimeError('Error reading current steps')
        if b == b'P':
            break
        line += b
    return int(bytes(line).decode())

def move_linear(target_position, engrave=False):
    """
    target_position : (y, x) coordinates to move to in mm
    engrave : whether to move as fast as possible or to engrave (move slowly)
    """
    global current_steps_x, current_steps_y
    
    y, x = target_position
    current_x = current_steps_x / x_steps_per_mm
    current_y = current_steps_y / y_steps_per_mm
    if y is None:
        y = current_y
    if x is None:
        x = current_x
    x_direction = np.sign(x - current_x)
    y_direction = np.sign(y - current_y)
        
    if engrave:
        x_num_pixels = abs((x - current_x)*resolution_mm)
        y_num_pixels = abs((y - current_y)*resolution_mm)
        x_steps_per_pixel = x_steps_per_mm/resolution_mm
        y_steps_per_pixel = y_steps_per_mm/resolution_mm
        if y_num_pixels == 0:
            pixel_ratio = np.inf
        else:            
            pixel_ratio = x_num_pixels / y_num_pixels
        x_pixels_moved = 0
        y_pixels_moved = 0
        steps = []
        for i in range(int(np.ceil(x_num_pixels + y_num_pixels))):
            if np.rint(i*pixel_ratio) > x_pixels_moved and x_pixels_moved < x_num_pixels:
                x_pixels_moved += 1
                step = int(np.rint(current_steps_x + x_direction*x_pixels_moved*x_steps_per_pixel))
                if step == 0: # Make sure we don't send 0 to the arduino because that will be interpreted as no data received
                    step = 1
                steps.append(('x', step))
            if np.rint(np.divide(i, pixel_ratio)) > y_pixels_moved and y_pixels_moved < y_num_pixels:
                y_pixels_moved += 1
                step = int(np.rint(current_steps_y + y_direction*y_pixels_moved*y_steps_per_pixel))
                if step == 0:
                    step = 1
                steps.append(('y', step))
        current_steps_x = int(np.rint(current_steps_x + x_direction*x_pixels_moved*x_steps_per_pixel))
        current_steps_y = int(np.rint(current_steps_y + y_direction*y_pixels_moved*y_steps_per_pixel))
    else:
        x_step = int(np.rint(x*x_steps_per_mm))
        y_step = int(np.rint(y*y_steps_per_mm))
        if x_step == 0: # Make sure we don't send 0 to the arduino because that will be interpreted as no data received
            x_step = 1
        if y_step == 0:
            y_step = 1
        steps = [('x', x_step), ('y', y_step)]
        current_steps_x = x_step
        current_steps_y = y_step
    print(current_steps_x, current_steps_y)
    return steps
    
def move_circular(target_position, center, direction: str):
    """
    direction must be a string, either 'cw' or 'ccw' for clockwise or counter-clockwise movement
    """
    global current_steps_x, current_steps_y
    direction = direction.lower()
    assert direction in ['cw', 'ccw']
    y, x = target_position
    c_y, c_x = center
    current_x = current_steps_x / x_steps_per_mm
    current_y = current_steps_y / y_steps_per_mm
    c_x += current_x
    c_y += current_y
    if y is None:
        y = current_y
    if x is None:
        x = current_x
    #x_steps_per_pixel = x_steps_per_mm/resolution_mm
    #y_steps_per_pixel = y_steps_per_mm/resolution_mm
    radius = np.sqrt((current_x - c_x)**2 + (current_y - c_y)**2)
    current_angle = np.arctan2(current_y - c_y, current_x - c_x)
    target_angle = np.arctan2(y - c_y, x - c_x)
    angle_delta = target_angle - current_angle
    if angle_delta < 0 and direction == 'ccw':
        angle_delta += 2*np.pi
    if angle_delta > 0 and direction == 'cw':
        angle_delta -= 2*np.pi
    arc_length = abs(angle_delta*radius)
    total_number_pixels = int(np.rint(arc_length * resolution_mm))
    angle_step = angle_delta/total_number_pixels
#    x_pixels_moved = 0
#    y_pixels_moved = 0
    steps = []
    last_x = current_x
    last_y = current_y
    for i in np.arange(angle_step, angle_delta+angle_step, angle_step):
        if np.abs(last_x - (c_x + radius*np.cos(current_angle+i))) > 1/resolution_mm:
            step = int(np.rint((c_x + radius*np.cos(current_angle+i)) * x_steps_per_mm))            
            if step == 0:
                step = 1
            steps.append(('x', step))
            last_x = step/x_steps_per_mm
        if np.abs(last_y - (c_y + radius*np.sin(current_angle+i))) > 1/resolution_mm:
            step = int(np.rint((c_y + radius*np.sin(current_angle+i)) * y_steps_per_mm))
            if step == 0:
                step = 1
            steps.append(('y', step))
            last_y = step/y_steps_per_mm
#        if abs(x - last_x) <= 1/resolution_mm and abs(y - last_y) <= 1/resolution_mm:
        #if x_pixels_moved + y_pixels_moved >= total_number_pixels and (abs(x - last_x) <= 1/resolution_mm and
        #                                                               abs(y - last_y) <= 1/resolution_mm):
 #           break
    steps.append(('x', int(np.rint(x*x_steps_per_mm))))
    steps.append(('y', int(np.rint(y*y_steps_per_mm))))
    current_steps_x = x*x_steps_per_mm
    current_steps_y = y*y_steps_per_mm
    
    return steps

def parse_line(line):
    x = y = z = i = j = None
    comment_start = line.find('(')
    if comment_start != -1:
        line = line[:comment_start]
    
    splitline = line.strip().split()
    for piece in splitline:
        if piece.startswith('X'):
            x = float(piece[1:])
        elif piece.startswith('Y'):
            y = float(piece[1:])
        elif piece.startswith('Z'):
            z = float(piece[1:])
        elif piece.startswith('I'):
            i = float(piece[1:])
        elif piece.startswith('J'):
            j = float(piece[1:])
        else:
            pass
    if i is not None or j is not None:
        return ((y, x), (j, i))
    else:
        return (y, x)

def process_line(line: str):
    global current_steps_x, current_steps_y
    line = line.upper()
    line = line.strip()
    if line.startswith('G'):
        current_steps_x = get_current_steps('x')
        current_steps_y = get_current_steps('y')
        
    if line.startswith('G00'):
        position = parse_line(line)
        steps = move_linear(position, engrave=False)
        execute_move(steps)
    elif line.startswith('G01'):
        position = parse_line(line)
        steps = move_linear(position, engrave=True)
        execute_move(steps)
    elif line.startswith('G02'):
        position, center = parse_line(line)
        steps = move_circular(position, center, 'cw')
        execute_move(steps)
    elif line.startswith('G03'):
        position, center = parse_line(line)
        steps = move_circular(position, center, 'ccw')
        execute_move(steps)
    elif line.startswith('('):
        # Comments from inkscape Gcodetools are in paranthesis
        pass
    else:
        print('unrecognized command')
        
def process_file(path: str):
    with open(path) as gcodefile:
        for line in gcodefile:
            process_line(line)

def main():
    global ser
    parser = argparse.ArgumentParser(description='GCode interpreter')
    parser.add_argument('-l', '--line', help='interprets a single line of GCode')
    parser.add_argument('-f', '--file', help='interprets a GCode File')
    args = parser.parse_args()
    os.system('stty -F {:s} -hupcl'.format(arduino_serial_port))
    ser = serial.Serial(arduino_serial_port, arduino_serial_baudrate, timeout=0.1)
    res = b''
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    while not res == b'R':
        ser.write(b'R')
        res = ser.read()
    ser.write(b'V0\n')
    res = ser.read()
    if res != b'V':
        print(res)
        raise RuntimeError('Could not set verbosity')
    ser.timeout = 10
    if args.line is not None:
        process_line(args.line)
    elif args.file is not None:
        process_file(args.file)
    if ser is not None:
        ser.close()

def calc_arc(steps):
    x_l = []
    y_l = []
    last_x = 0
    last_y = np.inf
    for step in steps:
        if step[0] == 'x' and step[1] > last_x:
            last_x = step[1]
        if step[1] == 'y' and step[1] < last_y:
            last_y = step[1]
            
    for step in steps:
        if step[0] == 'x':
            x_l.append(step[1])
            last_x = step[1]
        elif step[0] == 'y':
            y_l.append(step[1])
            last_y = step[1]
        if len(x_l) < len(y_l)-1:
            x_l.append(last_x)
        if len(y_l) < len(x_l)-1:
            y_l.append(last_y)
    return x_l, y_l
    
if __name__ == '__main__':
    main()

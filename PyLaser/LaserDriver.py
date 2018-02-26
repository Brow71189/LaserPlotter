# -*- coding: utf-8 -*-
"""
Laser Plotter Driver
"""

import serial
import numpy as np
import argparse
import configparser
import os

####################### settings ###########################################
arduino_serial_port = '/dev/ttyACM0'
arduino_serial_baudrate = 115200
y_steps_per_mm = 11.77
x_steps_per_mm = 378.21
y_speed = 5 # in mm/s
x_speed = 5 # in mm/s
resolution = 150 #dpi
use_gcode_speeds = False
fast_movement_speed = 20 # mm/s
engraving_movement_speed = 2 # mm/s
motor_ids = {
             'x': 'XA',
             'y': 'XB',
             'z': 'L'
             }
############################################################################

resolution_mm = resolution/25.4
ser = None
standalone_mode = False
current_steps_x = 0
current_steps_y = 0

class LaserDriver(object):
    motor_ids = {
                     'x': 'XA',
                     'y': 'XB',
                     'z': 'L'
                     }
    
    states = {
              'active': {},
              'pause': {}, 
              'error': {},
              'ready': {},
              'idle': {}
              }
    
    def __init__(self):
        
        self._state = 'idle'
        self.state = 'idle'
        self._current_line = None
        self._abort_move = False
        self._pause_move = False
        self._current_steps_x = 0
        self._current_steps_y = 0
        self._ser = None
        self._resolution_mm = None
        self._move_to = {}
        
        self.serial_port = '/dev/ttyACM0'
        self.serial_baudrate = 115200
        self.y_steps_per_mm = 11.77
        self.x_steps_per_mm = 378.21
        self.y_speed = 5 # in mm/s
        self.x_speed = 5 # in mm/s
        self.resolution = 150 #dpi
        self.use_gcode_speeds = False
        self.fast_movement_speed = 20 # mm/s
        self.engraving_movement_speed = 2 # mm/s
        self.gcode_file = None
        self.gcode_line = None
        self.raw_command = None     
        
        self.callback_function = None
        
        self.load_config()
        
    @property
    def resolution(self):
        return self.resolution * 25.4
    
    @resolution.setter
    def resolution(self, resolution):
        self._resolution_mm = resolution/25.4
        
    def parse_line(self, line):
        x = y = z = i = j = f = None
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
            elif piece.startswith('F'):
                f = float(piece[1:])
            else:
                pass
            
        if f is not None and use_gcode_speeds:
            self.x_speed = f
            self.y_speed = f
        else:
            if line.startswith('G00'):
                self.x_speed = self.fast_movement_speed
                self.y_speed = self.fast_movement_speed
            else:
                self.x_speed = self.engraving_movement_speed
                self.y_speed = self.engraving_movement_speed
                
        if i is not None or j is not None:
            if z is not None:
                return ((z, y, x), (j, i))
            else:        
                return ((y, x), (j, i))
        else:
            if z is not None:
                return (z, y, x)
            else:
                return (y, x)
    
    def calculate_steps(self):
        pass
        
    def process_line(self):
        if self.gcode_line is None:
            return
        import time
        starttime = time.time()
        line = self.gcode_line.upper()
        line = line.strip()
        
        if line.startswith('G') and self.state in ('ready', 'active'):
            self._current_steps_x = self.get_current_steps('x')
            self._current_steps_y = self.get_current_steps('y')
        
        self.parse_line(line)
        self.calculate_steps()
        
        if line.startswith('G00'):
            position = self.parse_line(line)
            self.steps = self.move_linear(position, engrave=False)
        elif line.startswith('G01'):
            position = self.parse_line(line)
            self.steps = self.move_linear(position, engrave=True)
        elif line.startswith('G02'):
            position, center = self.parse_line(line)
            self.steps = self.move_circular(position, center, 'cw')
        elif line.startswith('G03'):
            position, center = self.parse_line(line)
            self.steps = self.move_circular(position, center, 'ccw')
        elif line.startswith('(') or line.startswith('%') or not line:
            # Comments from inkscape Gcodetools are in paranthesis
            pass
        else:
            print('unrecognized command: {}'.format(line))

        try:
            if self.do_simulation:
                self.execute_simulation_move()
            else:
                self.execute_move()
        except RuntimeError:
            raise
        finally:
            if self.mode.get() == 'line':
                self.finish()
                print('Elapsed time: {:.2f} s'.format(time.time() - starttime))
        
    def process_file(self):
        if self._current_line is not None:
            try:
                self.gcode_line = self._current_line
                self.process_line()
            except RuntimeError:
                self.state = 'error'
                raise

        for line in self.gcode_file:
            if self._abort_move:
                self.state = 'ready'
                return
            
            self._current_line = line
            self.gcode_line = line
            
            if self._pause_move:
                self.state = 'pause'
                return
            
            try:
                self.process_line()
            except RuntimeError:
                self.state = 'error'
                raise

    def load_config(self):
        parser = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        if os.path.isfile(config_path):
            parser.read(config_path)
            self.settings_from_parser(parser)
    
    def save_config(self):
        parser = self.settings_to_parser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        with open(config_path, 'w+') as config_file:
            parser.write(config_file)
        
    def settings_to_parser(self):
        parser = configparser.ConfigParser()
        parser.add_section('connection')
        parser.add_section('calibrations')
        parser.add_section('options')
        parser.add_section('motor ids')
        parser.set('connection', 'serial port', self.arduino_serial_port)
        parser.set('connection', 'baudrate', str(self.arduino_serial_baudrate))
        parser.set('calibrations', 'x steps per mm', str(self.x_steps_per_mm))
        parser.set('calibrations', 'y steps per mm', str(self.y_steps_per_mm))
        parser.set('calibrations', 'x speed', str(self.x_speed))
        parser.set('calibrations', 'y speed', str(self.y_speed))
        parser.set('options', 'resolution', str(self.resolution))
        parser.set('options', 'use gcode speeds', str(self.use_gcode_speeds))
        parser.set('options', 'fast movement speed', str(self.fast_movement_speed))
        parser.set('options', 'engraving movement speed', str(self.engraving_movement_speed))
        for key, value in self.motor_ids.items():
            parser.set('motor ids', key, value)
        return parser
    
    def settings_from_parser(self, parser):    
        self.arduino_serial_port = parser.get('connection', 'serial port', fallback=self.arduino_serial_port)
        self.arduino_serial_baudrate = parser.getint('connection', 'baudrate', fallback=self.arduino_serial_baudrate)
        self.x_steps_per_mm = parser.getfloat('calibrations', 'x steps per mm', fallback=self.x_steps_per_mm)
        self.y_steps_per_mm = parser.getfloat('calibrations', 'y steps per mm', fallback=self.y_steps_per_mm)
        self.x_speed = parser.getfloat('calibrations', 'x speed', fallback=self.x_speed)
        self.y_speed = parser.getfloat('calibrations', 'y speed', fallback=self.y_speed)
        self.resolution = parser.getfloat('options','resolution', fallback=self.resolution)
        self.use_gcode_speeds = parser.getboolean('options', 'use gcode speeds', fallback=self.use_gcode_speeds)
        self.fast_movement_speed = parser.getfloat('options', 'fast movement speed', fallback=self.fast_movement_speed)
        self.engraving_movement_speed = parser.getfloat('options', 'engraving movement speed',
                                                        fallback=self.engraving_movement_speed)    
        for key, value in parser.items(section='motor ids'):
            self.motor_ids[key] = value

def execute_move(steps):
    global ser
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.write(b'R')
    res = ser.read()
    if res != b'R':
        print(res)
        raise RuntimeError('Engraver not ready.')
        
    set_speed('x', x_speed)
    set_speed('y', y_speed)
    counter = 0
    while counter < len(steps):
        #ser.reset_input_buffer()
        #ser.reset_output_buffer()
        motor, position = steps[counter]
        cmd = bytes('{:s}{:d}\n'.format(motor_ids[motor], position), 'ASCII')
        #print(cmd)
        ser.write(cmd)
        #res = ser.readline()
        #print(res)
        res = ser.read()
        #print(res)
        
        if res == b'X':
            counter += 1
        elif res == b'L':
            counter += 1
        elif res == b'E':
            print('Error executing move. Repeating')
            #raise RuntimeError('Error executing move')
        elif res == b'B':
            raise RuntimeError('{:s}-Motor might be blocked'.format(motor), counter)
        else:
            print(res)
            raise RuntimeError('Unknown return code from engraver: {:s}'.format(res.decode('ASCII')), counter)

def get_current_steps(motor):
    global ser
    ser.reset_input_buffer()
    line = bytearray()
    ser.write(b'P' + bytearray(motor_ids[motor][1], 'ASCII'))
    while True:
        b = ser.read()
        if not b:
            raise RuntimeError('No data received')
        if b == b'E':
            raise RuntimeError('Error reading current steps')
        if b == b'P':
            break
        #if b in [b'0', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9']:
        line += b
    return int(bytes(line).decode())

def move_linear(target_position, engrave=False):
    """
    target_position : (y, x) coordinates to move to in mm
    engrave : whether to move as fast as possible or to engrave (move slowly)
    """
    global current_steps_x, current_steps_y
    
    x = y = z = None
    
    if len(target_position) == 3:
        z, y, x = target_position
    else:
        y, x = target_position
    current_x = current_steps_x / x_steps_per_mm
    current_y = current_steps_y / y_steps_per_mm
    if y is None:
        y = current_y
    if x is None:
        x = current_x
    #x_direction = np.sign(x - current_x)
    #y_direction = np.sign(y - current_y)
    steps = []
    if z is not None:
        steps.append(('z', 1 if z < 0 else 0))    
    if engrave:
        delta_x = x - current_x
        delta_y = y - current_y
        line_length = np.sqrt(delta_x**2 + delta_y**2)
        angle = np.arctan2(delta_y, delta_x)
        last_x = 0
        last_y = 0
        for i in np.arange(0, line_length+1/resolution_mm, 1/resolution_mm):
            if np.abs(last_x - i*np.cos(angle)) > 1/resolution_mm:
                step = int(np.rint(i*np.cos(angle) * x_steps_per_mm)) + current_steps_x
                if step == 0:
                    step = 1
                if len(steps) > 0 and steps[-1][0] == 'x':
                    steps[-1] = ('x', step)
                else:
                    steps.append(('x', step))
                last_x = i*np.cos(angle)
            if np.abs(last_y - i*np.sin(angle)) > 1/resolution_mm:
                step = int(np.rint(i*np.sin(angle) * y_steps_per_mm)) + current_steps_y
                if step == 0:
                    step = 1
                if len(steps) > 0 and steps[-1][0] == 'y':
                    steps[-1] = ('y', step)
                else:
                    steps.append(('y', step))
                last_y = i*np.sin(angle)
                
    x_step = int(np.rint(x*x_steps_per_mm))
    y_step = int(np.rint(y*y_steps_per_mm))
    if x_step == 0: # Make sure we don't send 0 to the arduino because that will be interpreted as no data received
        x_step = 1
    if y_step == 0:
        y_step = 1
    steps.extend([('x', x_step), ('y', y_step)])
    current_steps_x = x_step
    current_steps_y = y_step
    #print(current_steps_x, current_steps_y)
    return steps
    
def move_circular(target_position, center, direction: str):
    """
    direction must be a string, either 'cw' or 'ccw' for clockwise or counter-clockwise movement
    """
    global current_steps_x, current_steps_y
    
    x = y = z = None
    
    direction = direction.lower()
    assert direction in ['cw', 'ccw']
    
    if len(target_position) == 3:
        z, y, x = target_position
    else:
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
    if z is not None:
        steps.append(('z', 1 if z < 0 else 0))
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
    x_step = int(np.rint(x*x_steps_per_mm))
    y_step = int(np.rint(y*y_steps_per_mm))
    if x_step == 0: # Make sure we don't send 0 to the arduino because that will be interpreted as no data received
        x_step = 1
    if y_step == 0:
        y_step = 1
    steps.extend([('x', x_step), ('y', y_step)])
    current_steps_x = x_step
    current_steps_y = y_step
    
    return steps

def parse_line(line):
    global x_speed, y_speed
    x = y = z = i = j = f = None
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
        elif piece.startswith('F'):
            f = float(piece[1:])
        else:
            pass
        
    if f is not None and use_gcode_speeds:
        x_speed = f
        y_speed = f
    else:
        if line.startswith('G00'):
            x_speed = fast_movement_speed
            y_speed = fast_movement_speed
        else:
            x_speed = engraving_movement_speed
            y_speed = engraving_movement_speed
            
    if i is not None or j is not None:
        if z is not None:
            return ((z, y, x), (j, i))
        else:        
            return ((y, x), (j, i))
    else:
        if z is not None:
            return (z, y, x)
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
    elif line.startswith('(') or line.startswith('%') or not line:
        # Comments from inkscape Gcodetools are in paranthesis
        pass
    else:
         print('unrecognized command: {}'.format(line))
        
def set_speed(motor, speed):
    motor = motor.lower()
    if motor == 'x':
        speed_steps = speed*x_steps_per_mm
    elif motor == 'y':
        speed_steps = speed*y_steps_per_mm
    else:
        print('Unknown motor id. Must be either "x" or "y"')
        return
        
    cmd = bytes('S{:s}{:.1f}\n'.format(motor_ids[motor][1], speed_steps), 'ASCII')
    ser.write(cmd)
    res = ser.read()
    
    if res != b'S':
        raise RuntimeError('Unable to set speed for motor {}.'.format(motor))
    
        
def process_file(path: str):
    with open(path) as gcodefile:
        for line in gcodefile:
            process_line(line)

def send_raw(raw_command: str):
    command = bytes(raw_command, 'ASCII')
    ser.write(command)
    res = (ser.read()).decode()
    num_bytes = ser.in_waiting
    if num_bytes > 0:
        res += (ser.read(num_bytes)).decode()
    return res

def main():
    global ser
    parser = argparse.ArgumentParser(description='GCode interpreter')
    parser.add_argument('-l', '--line', help='interprets a single line of GCode')
    parser.add_argument('-f', '--file', help='interprets a GCode File')
    args = parser.parse_args()
    load_config()
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
    ser.timeout = 300
    if args.line is not None:
        process_line(args.line)
    elif args.file is not None:
        process_file(args.file)
    if standalone_mode:
        close()

def close():
    global ser
    if ser is not None:
        ser.close()
        ser = None
    save_config()

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
    standalone_mode = True
    main()

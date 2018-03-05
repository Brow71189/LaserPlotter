# -*- coding: utf-8 -*-
"""
Laser Plotter Driver
"""

import serial
from serial import SerialException
import numpy as np
import argparse
import configparser
import os
import logging
from io import StringIO
import threading

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


class LaserDriver(object):
    __motor_ids = {
                     'x': 'XA',
                     'y': 'XB',
                     'z': 'L'
                     }
    
    __states = {
                'active': {'_pause_move': False,
                           '_abort_move': False},
                'pause': {'_pause_move': True,
                          '_abort_move': False,
                          '_thread': None}, 
                'error': {'_pause_move': False,
                          '_abort_move': False,
                          '_thread': None},
                'ready': {'_current_line': None,
                         '_target_position': {},
                         '_steps': [],
                         '_current_counter': 0,
                         'gcode_file': None,
                         'gcode_line': None,
                         'raw_command': None,
                         '_thread': None},
                'idle': {'_current_line': None,
                         '_ser': None,
                         '_target_position': {},
                         '_steps': [],
                         '_current_counter': 0,
                         'gcode_file': None,
                         'gcode_line': None,
                         'raw_command': None,
                         '_thread': None},
                }
              
    __done = {
              'raw': {'raw_command': None,
                      '_thread': None},
              'line': {'raw_command': None,
                       'gcode_line': None,
                       '_steps': [],
                       '_current_counter': 0,
                       '_current_line': None,
                       '_target_position': {},
                       '_thread': None},
              'file': {'state': 'ready'}
              }
    
    def __init__(self):
        
        self._state = 'idle'
        self._current_line = None
        self._abort_move = False
        self._pause_move = False
        self._current_steps_x = 0
        self._current_steps_y = 0
        self._ser = None
        self._resolution_mm = None
        self._target_position = {}
        self._y_speed = 5 # in mm/s
        self._x_speed = 5 # in mm/s
        self._steps = []
        self._current_counter = 0
        self._thread = None
        
        self.serial_port = '/dev/ttyACM0'
        self.serial_baudrate = 115200
        self.y_steps_per_mm = 11.77
        self.x_steps_per_mm = 378.21
        self.resolution = 150 #dpi
        self.use_gcode_speeds = False
        self.fast_movement_speed = 20 # mm/s
        self.engraving_movement_speed = 2 # mm/s
        self.gcode_file = None
        self.gcode_line = None
        self.raw_command = None     
        
        self.callback_function = None
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        self.load_config()
        
    @property
    def resolution(self):
        return self._resolution_mm * 25.4
    
    @resolution.setter
    def resolution(self, resolution):
        self._resolution_mm = resolution/25.4
        
    @property
    def state(self):
        return self._state
    
    @state.setter
    def state(self, state):
        if state == self._state:
            return
        
        state_parameters = self.__states.get(state, dict())
        for key, value in state_parameters.items():
            setattr(self, key, value)
        self._state = state
        if callable(self.callback_function):
            self.callback_function({'action': 'set', 'parameter': 'state', 'value': state})
            
    def abort(self):
        self._abort_move = True
        
    def pause(self):
        self._pause_move = True
            
    def _done(self, command):
        done_parameters = self.__done.get(command, dict())
        for key, value in done_parameters.items():
            setattr(self, key, value)
        if command == 'raw' and self.gcode_line is None:
            self.state = 'ready'
        elif command == 'line' and self.gcode_file is None:
            self.state = 'ready'
        if callable(self.callback_function):
            self.callback_function({'action': 'done', 'value': command})
            
    def execute_command(self, command, content=None):
        run_func = None
        try:
            self.save_config()
        except Exception as e:
            self.logger.error(str(e))
        if command == 'raw':
            if content is not None:
                self.raw_command = content
            def run():
                try:
                    self.send_raw()
                except Exception as e:
                    message = ''
                    for p in e.args:
                        message += str(p) + ' '
                    message = message[:-1]
                    self.logger.error(message)
                    raise
            run_func = run
        elif command == 'line':
            if content is not None:
                self.gcode_line = content
            def run():
                try:
                    self.process_line()
                except Exception as e:
                    message = ''
                    for p in e.args:
                        message += str(p) + ' '
                    message = message[:-1]
                    self.logger.error(message)
                    raise
            run_func = run
        elif command == 'file':
            if content is not None:
                if type(content) == str:
                    self.gcode_file = StringIO(initial_value=content)
                else:
                    self.gcode_file = content
            
            def run():
                try:
                    self.process_file()
                except Exception as e:
                    message = ''
                    for p in e.args:
                        message += str(p) + ' '
                    message = message[:-1]
                    self.logger.error(message)
                    raise
            run_func = run
        elif command == 'start connection':
            try:
                self.start_connection()
            except Exception as e:
                message = ''
                for p in e.args:
                    message += str(p) + ' '
                message = message[:-1]
                self.logger.error(message)
                raise
        elif command == 'close connection':
            try:
                self.start_connection()
            except Exception as e:
                message = ''
                for p in e.args:
                    message += str(p) + ' '
                message = message[:-1]
                self.logger.error(message)
                raise
                
        if run_func is not None:
            self._thread = threading.Thread(run_func)
            self._thread.start()
        
    def send_raw(self, raw_command=None):
        if raw_command is not None:
            self.raw_command = raw_command
        if self.raw_command is None:
            return
        self.state = 'active'
        command = self.raw_command.encode()
        try:
            self._ser.write(command)
        except SerialException:
            self.state = 'error'
            raise
        else:
            self._done('raw')
        res = b''
        while self._ser.in_waiting > 0:
            res += self._ser.read()
        return res.decode()
    
    def check_ready(self):
        reply = self.send_raw('R')
        if reply != 'R':
            raise RuntimeError('Ready check failed! Reply was "{}" instead of "R"!'.format(reply))
            
    def get_current_steps(self, motor):
        res = self.send_raw('P' + self.__motor_ids[motor][1])
        
        if res.endswith('P'):
            return int(res[:-1])
        elif not res:
            raise RuntimeError('No data received')
        else:
            raise RuntimeError('Error reading current steps')
            
    def set_speed(self, motor, speed):
        motor = motor.lower()
        if motor == 'x':
            speed_steps = speed*self.x_steps_per_mm
        elif motor == 'y':
            speed_steps = speed*self.y_steps_per_mm
        else:
            raise RuntimeError('Unknown motor id "{}". Must be either "x" or "y"'.format(motor))
            
        cmd = 'S{:s}{:.1f}\n'.format(self.__motor_ids[motor][1], speed_steps)
        
        res = self.send_raw(cmd)
        
        if res != 'S':
            raise RuntimeError('Unable to set speed for motor {}.'.format(motor))
    
    def execute_move(self):
        if self._ser is not None:
            try:
                self._ser.reset_input_buffer()
                self._ser.reset_output_buffer()
            except SerialException:
                self.state = 'error'
                raise
                
        try:
            self.check_ready()
        except RuntimeError:
            self.state = 'error'
            raise
        
        try:
            self.set_speed('x', self._x_speed)
            self.set_speed('y', self._y_speed)
        except RuntimeError:
            self.state = 'error'
            raise
            
        counter = self._current_counter
        while counter < len(self._steps):
            self._current_counter = counter
            if self._pause_move:
                self.state = 'pause'
                return
            motor, position = self._steps[counter]
            cmd = '{:s}{:d}\n'.format(self.__motor_ids[motor], position)
            res = self.send_raw(cmd)
            if res == 'X':
                counter += 1
            elif res == 'L':
                counter += 1
            elif res == 'E':
                self.logger.warning('Error executing move. Repeating')
            elif res == 'B':
                raise RuntimeError('{:s}-Motor might be blocked'.format(motor), counter)
            else:
                raise RuntimeError('Unknown return code from engraver: {:s}'.format(res), counter)
        
    def parse_line(self, line):
        if not line.startswith('G'):
            self._target_position = {}
            return
        
        comment_start = line.find('(')
        if comment_start != -1:
            line = line[:comment_start]
        target_position = {}
        splitline = line.strip().split()
        for piece in splitline:
            if piece.startswith('X'):
                target_position['x'] = float(piece[1:])
            elif piece.startswith('Y'):
                target_position['y'] = float(piece[1:])
            elif piece.startswith('Z'):
                target_position['z'] = float(piece[1:])
            elif piece.startswith('I'):
                target_position['i'] = float(piece[1:])
            elif piece.startswith('J'):
                target_position['i'] = float(piece[1:])
            elif piece.startswith('F'):
                target_position['f'] = float(piece[1:])
            else:
                pass
            
        if target_position.get('f') is not None and self.use_gcode_speeds:
            self._x_speed = target_position['f']
            self._y_speed = target_position['f']
        else:
            if line.startswith('G00'):
                self._x_speed = self.fast_movement_speed
                self._y_speed = self.fast_movement_speed
            else:
                self._x_speed = self.engraving_movement_speed
                self._y_speed = self.engraving_movement_speed
        
        target_position['command'] = line[:3]
        
        self._target_position = target_position
    
    def calculate_steps(self):
        if self._target_position.get('command') is None:
            return
        elif self._target_position.get('command') == 'G00':
            self.move_linear(engrave=False)
        elif self._target_position.get('command') == 'G01':
            self.move_linear(engrave=True)
        elif self._target_position.get('command') == 'G02':
            self.move_circular('cw')
        elif self._target_position.get('command') == 'G03':
            self.move_circular('ccw')    
        
    def process_line(self, gcode_line=None):
        if gcode_line is not None:
            self.gcode_line = gcode_line
        if self.gcode_line is None:
            return
        self.state = 'active'
        import time
        starttime = time.time()
        line = self.gcode_line.upper()
        line = line.strip()
        
        if line.startswith('G') and self.state in {'ready', 'active'}:
            self._current_steps_x = self.get_current_steps('x')
            self._current_steps_y = self.get_current_steps('y')
        
        self.parse_line(line)
        self.calculate_steps()

        try:
            self.execute_move()
        except RuntimeError:
            self.state = 'error'
            raise
        else:
            if not self.state in {'pause', 'error'}:
                self._done('line')
        finally:
            self.logger.info('Elapsed time: {:.2f} s'.format(time.time() - starttime))
        
    def process_file(self):
        self.state = 'active'
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
                
        if self.state not in ('error', 'pause'):
            self.done('file')

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
        parser.set('connection', 'serial port', self.serial_port)
        parser.set('connection', 'baudrate', str(self.serial_baudrate))
        parser.set('calibrations', 'x steps per mm', str(self.x_steps_per_mm))
        parser.set('calibrations', 'y steps per mm', str(self.y_steps_per_mm))
        parser.set('calibrations', 'x speed', str(self._x_speed))
        parser.set('calibrations', 'y speed', str(self._y_speed))
        parser.set('options', 'resolution', str(self.resolution))
        parser.set('options', 'use gcode speeds', str(self.use_gcode_speeds))
        parser.set('options', 'fast movement speed', str(self.fast_movement_speed))
        parser.set('options', 'engraving movement speed', str(self.engraving_movement_speed))
        for key, value in self.__motor_ids.items():
            parser.set('motor ids', key, value)
        return parser
    
    def settings_from_parser(self, parser):    
        self.serial_port = parser.get('connection', 'serial port', fallback=self.serial_port)
        self.serial_baudrate = parser.getint('connection', 'baudrate', fallback=self.serial_baudrate)
        self.x_steps_per_mm = parser.getfloat('calibrations', 'x steps per mm', fallback=self.x_steps_per_mm)
        self.y_steps_per_mm = parser.getfloat('calibrations', 'y steps per mm', fallback=self.y_steps_per_mm)
        self._x_speed = parser.getfloat('calibrations', 'x speed', fallback=self._x_speed)
        self._y_speed = parser.getfloat('calibrations', 'y speed', fallback=self._y_speed)
        self.resolution = parser.getfloat('options','resolution', fallback=self.resolution)
        self.use_gcode_speeds = parser.getboolean('options', 'use gcode speeds', fallback=self.use_gcode_speeds)
        self.fast_movement_speed = parser.getfloat('options', 'fast movement speed', fallback=self.fast_movement_speed)
        self.engraving_movement_speed = parser.getfloat('options', 'engraving movement speed',
                                                        fallback=self.engraving_movement_speed)    
        for key, value in parser.items(section='motor ids'):
            self.__motor_ids[key] = value

    def move_linear(self, target_position, engrave=False):
        """
        engrave : whether to move as fast as possible or to engrave (move slowly)
        """
        
        x = self._target_position.get('x')
        y = self._target_position.get('y')
        z = self._target_position.get('z')
        
        current_x = self._current_steps_x / self.x_steps_per_mm
        current_y = self._current_steps_y / self.y_steps_per_mm
        
        if y is None:
            y = current_y
        if x is None:
            x = current_x
            
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
            for i in np.arange(0, line_length+1/self._resolution_mm, 1/self._resolution_mm):
                if np.abs(last_x - i*np.cos(angle)) > 1/self._resolution_mm:
                    step = int(np.rint(i*np.cos(angle) * x_steps_per_mm)) + self._current_steps_x
                    if step == 0:
                        step = 1
                    if len(steps) > 0 and steps[-1][0] == 'x':
                        steps[-1] = ('x', step)
                    else:
                        steps.append(('x', step))
                    last_x = i*np.cos(angle)
                if np.abs(last_y - i*np.sin(angle)) > 1/self._resolution_mm:
                    step = int(np.rint(i*np.sin(angle) * y_steps_per_mm)) + self._current_steps_y
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
        self._current_steps_x = x_step
        self._current_steps_y = y_step
        
        self._steps = steps
        
    def move_circular(self, direction: str):
        """
        direction must be a string, either 'cw' or 'ccw' for clockwise or counter-clockwise movement
        """        
        direction = direction.lower()
        assert direction in ['cw', 'ccw'], 'Direction must be either "cw" or "ccw", not "{}"!'.format(direction)
        
        x = self._target_position.get('x')
        y = self._target_position.get('y')
        z = self._target_position.get('z')
        c_x = self._target_position.get('i')
        c_y = self._target_position.get('j')
        
        assert not None in (c_x, c_y), 'Center must be given for a cirular move!'
        
        current_x = self._current_steps_x / self.x_steps_per_mm
        current_y = self._current_steps_y / self.y_steps_per_mm
        
        c_x += current_x
        c_y += current_y
        
        if y is None:
            y = current_y
        if x is None:
            x = current_x

        radius = np.sqrt((current_x - c_x)**2 + (current_y - c_y)**2)
        current_angle = np.arctan2(current_y - c_y, current_x - c_x)
        target_angle = np.arctan2(y - c_y, x - c_x)
        angle_delta = target_angle - current_angle
        if angle_delta < 0 and direction == 'ccw':
            angle_delta += 2*np.pi
        if angle_delta > 0 and direction == 'cw':
            angle_delta -= 2*np.pi
        arc_length = abs(angle_delta*radius)
        total_number_pixels = int(np.rint(arc_length * self._resolution_mm))
        angle_step = angle_delta/total_number_pixels

        steps = []
        last_x = current_x
        last_y = current_y
        if z is not None:
            steps.append(('z', 1 if z < 0 else 0))
        for i in np.arange(angle_step, angle_delta+angle_step, angle_step):
            if np.abs(last_x - (c_x + radius*np.cos(current_angle+i))) > 1/self._resolution_mm:
                step = int(np.rint((c_x + radius*np.cos(current_angle+i)) * x_steps_per_mm))            
                if step == 0:
                    step = 1
                steps.append(('x', step))
                last_x = step/x_steps_per_mm
            if np.abs(last_y - (c_y + radius*np.sin(current_angle+i))) > 1/self._resolution_mm:
                step = int(np.rint((c_y + radius*np.sin(current_angle+i)) * y_steps_per_mm))
                if step == 0:
                    step = 1
                steps.append(('y', step))
                last_y = step/y_steps_per_mm
                
        x_step = int(np.rint(x*x_steps_per_mm))
        y_step = int(np.rint(y*y_steps_per_mm))
        if x_step == 0: # Make sure we don't send 0 to the arduino because that will be interpreted as no data received
            x_step = 1
        if y_step == 0:
            y_step = 1
        steps.extend([('x', x_step), ('y', y_step)])
        self._current_steps_x = x_step
        self._current_steps_y = y_step
        
        self._steps = steps
        
    def start_connection(self):
        os.system('stty -F {:s} -hupcl'.format(arduino_serial_port))
        try:
            self._ser = serial.Serial(self.serial_port, self.serial_baudrate, timeout=0.1)
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
        except SerialException:
            self.close()
            raise

        counter = 0
        while counter < 100:
            try:
                self.check_ready()
            except RuntimeError:
                pass
            else:
                self.state = 'ready'
                break
            finally:
                counter += 1
        else:
            self.close()
            raise RuntimeError('Plotter did not pass ready check. Check the connection and try to reconnect.')
            
        res = self.send_raw('V0')

        if res != 'V':
            raise RuntimeError('Could not set verbosity. Returned "{}" instead of "V"!'.format(res))
        self._ser.timeout = 300
        
    def close(self):
        if self._ser is not None:
            self._ser.close()
            self._ser = None
        self.state = 'idle'
        self.save_config()
        
#def main():
#    global ser
#    parser = argparse.ArgumentParser(description='GCode interpreter')
#    parser.add_argument('-l', '--line', help='interprets a single line of GCode')
#    parser.add_argument('-f', '--file', help='interprets a GCode File')
#    args = parser.parse_args()
#    load_config()
#    os.system('stty -F {:s} -hupcl'.format(arduino_serial_port))
#    ser = serial.Serial(arduino_serial_port, arduino_serial_baudrate, timeout=0.1)
#    res = b''
#    ser.reset_input_buffer()
#    ser.reset_output_buffer()
#    while not res == b'R':
#        ser.write(b'R')
#        res = ser.read()
#    ser.write(b'V0\n')
#    res = ser.read()
#    if res != b'V':
#        print(res)
#        raise RuntimeError('Could not set verbosity')
#    ser.timeout = 300
#    if args.line is not None:
#        process_line(args.line)
#    elif args.file is not None:
#        process_file(args.file)
#    if standalone_mode:
#        close()

#def close():
#    global ser
#    if ser is not None:
#        ser.close()
#        ser = None
#    save_config()
#    
#if __name__ == '__main__':
#    standalone_mode = True
#    main()

# -*- coding: utf-8 -*-
"""
Created on Sun Aug 27 16:48:31 2017

@author: andi
"""

import tkinter as tk
from tkinter import font
from tkinter import filedialog
import LaserDriver
import os
import threading
import numpy as np

class LaserGUI(object):
    def __init__(self):
        self.root = None
        self.gcodefile = None
        self._current_line = None
        self.mode = None
        self._file = None
        self.info_label = None
        self.start_button = None
        self.abort_button = None
        self.connect_button = None
        self.simulator_canvas = None
        self.steps = None
        self._abort_move = False
        self._current_counter = 0
        self._thread = None
        self.do_simulation = False

    def create_gui(self):
        self.root = tk.Tk()
        # Fonts definitions
        default_font = font.Font()
        file_name_font = font.Font(slant='italic')
        # Spacing definitions
        default_padx = 5
        default_pady = 3
        
        def connect_button_clicked():
            info_label['text'] = ''
            if self.connect_button['text'] == 'Connect to plotter':
                try:
                    LaserDriver.main()
                except Exception as e:
                    self.info_label['text'] = str(e)
                    return
                else:
                    self.connect_button['text'] = 'Disconnect'
            elif self.connect_button['text'] == 'Disconnect':
                LaserDriver.close()
                self.info_label['text'] = 'Connect to plotter'
                
        def settings_button_clicked():
            def resolution_changed(*args):
                if len(resolution.get()) > 0 and resolution.get() != str(LaserDriver.resolution):
                    try:
                        res = int(resolution.get())
                    except ValueError as e:
                        self.info_label['text'] = str(e)
                        resolution.set(str(LaserDriver.resolution))
                    else:
                        LaserDriver.resolution = res
                        
            def serial_port_changed(*args):
                if len(serial_port.get()) > 0 and serial_port.get() != LaserDriver.arduino_serial_port:
                    LaserDriver.arduino_serial_port = serial_port.get()
                        
            settings_window = tk.Toplevel(self.root)
            resolution_label = tk.Label(settings_window, font=default_font, text='Resolution (dpi):', anchor=tk.W)
            resolution_label.grid(column=0, row=0, padx=default_padx, pady=default_pady, sticky=tk.W)
            resolution = tk.StringVar()
            resolution.set(LaserDriver.resolution)
            resolution.trace('w', resolution_changed)
            resolution_field = tk.Entry(settings_window, font=default_font, textvariable=resolution, width=4)
            resolution_field.grid(column=1, row=0, padx=default_padx, pady=default_pady, sticky=tk.W)
            serial_port_label = tk.Label(settings_window, font=default_font, text='Serial port:', anchor=tk.W)
            serial_port_label.grid(column=0, row=1, padx=default_padx, pady=default_pady, sticky=tk.W)
            serial_port = tk.StringVar()
            serial_port.set(LaserDriver.arduino_serial_port)
            serial_port.trace('w', serial_port_changed)
            serial_port_field = tk.Entry(settings_window, font=default_font, textvariable=serial_port, width=12)
            serial_port_field.grid(column=1, row=1, padx=default_padx, pady=default_pady)

        def open_button_clicked():
            filename = ''
            info_label['text'] = ''
            while not os.path.isfile(filename):
                filename = filedialog.askopenfilename()
                if len(filename) == 0:
                    break
            if len(filename) > 0:
                if not os.path.isfile(filename):
                    info_label['text'] = '{:s} is not a valid file'.format(filename)
                    return
                self.gcodefile = filename
                current_file_name['text'] = self.gcodefile
        
        def start_button_clicked():
            info_label['text'] = ''
            if self.mode.get() == 'file':
                try:
                    self._file = open(self.gcodefile)
                except Exception as e:
                   info_label['text'] = str(e)
                   return
                else:
                    self._thread = threading.Thread(target=self.process_file)
                    self._thread.start()
            elif self.mode.get() == 'line':
                self._thread = threading.Thread(target=self.process_line, args=(line_entry.get(),))
                self._thread.start()
            elif self.mode.get() == 'raw':
                self._thread = threading.Thread(target=self.process_raw, args=(raw_entry.get(),))
                self._thread.start()
                
            self.abort_button.config(state=tk.NORMAL)
            self.start_button.config(state=tk.DISABLED)
            self.connect_button.config(state=tk.DISABLED)
                
        def abort_button_clicked():
            self._abort_move = True
            self.start_button['text'] = 'Start plot'
            self.steps = None
            self._current_counter = 0
            self._current_line = None
            self.abort_button.config(state=tk.DISABLED)
            if self._thread is None or not self._thread.is_alive():
                self._abort_move = False
        
        def mode_changed(*args):
            current_file_text.grid_remove()
            current_file_name.grid_remove()
            open_button.grid_remove()
            line_descriptor.grid_remove()
            line_entry.grid_remove()
            raw_descriptor.grid_remove()
            raw_entry.grid_remove()
            if self.mode.get() == 'file':
                current_file_text.grid()
                current_file_name.grid()
                open_button.grid()
            elif self.mode.get() == 'line':
                line_descriptor.grid()
                line_entry.grid()
            elif self.mode.get() == 'raw':
                raw_descriptor.grid()
                raw_entry.grid()
        
        def simulate_button_clicked():
            self.do_simulation = True
            start_button_clicked()
        
        def clear_button_clicked():
            self.simulator_canvas.delete(tk.ALL)
            LaserDriver.current_steps_x = 0
            LaserDriver.current_steps_y = 0
            
        # Elements for "file" mode
        current_file_text = tk.Label(self.root, text='Current file:', font=default_font, anchor=tk.W)
        current_file_text.grid(column=0, row=1, padx=default_padx, pady=default_pady, sticky=tk.W)
        current_file_name = tk.Label(self.root, text='/home/Andi/test.ngc', font=file_name_font, anchor=tk.W)
        current_file_name.grid(column=1, row=1, columnspan=2, padx=default_padx, pady=default_pady, sticky=tk.W)
        open_button = tk.Button(self.root, text='Open Gcode file', command=open_button_clicked, font=default_font)
        open_button.grid(column=3, row=1, padx=default_padx, pady=default_pady)
        # Elements for "line" mode
        line_descriptor = tk.Label(self.root, text='Gcode line:', font=default_font)
        line_descriptor.grid(column=0, row=1, padx=default_padx, pady=default_pady)
        line_entry = tk.Entry(self.root, font=default_font)
        line_entry.grid(column=1, row=1, padx=default_padx, pady=default_pady, sticky=tk.W)
        # Elements for "raw" mode
        raw_descriptor = tk.Label(self.root, text='Raw movement command:', font=default_font)
        raw_descriptor.grid(column=0, row=1, padx=default_padx, pady=default_pady)
        raw_entry = tk.Entry(self.root, font=default_font)
        raw_entry.grid(column=1, row=1, padx=default_padx, pady=default_pady)
        # Other elements
        self.connect_button = tk.Button(self.root, text='Connect to plotter', command=connect_button_clicked, font=default_font)
        self.connect_button.grid(column=0, row=0, columnspan=2, padx=default_padx, pady=default_pady, sticky=tk.W)
        settings_button = tk.Button(self.root, text='Settings...', command=settings_button_clicked, font=default_font)
        settings_button.grid(column=2, row=0, padx=default_padx, pady=default_pady)
        self.start_button = tk.Button(self.root, text='Start plot', command=start_button_clicked, font=default_font)
        self.start_button.grid(column=3, row=2, padx=default_padx, pady=default_pady)
        self.abort_button = tk.Button(self.root, text='Abort plot', command=abort_button_clicked, font=default_font)
        self.abort_button.grid(column=2, row=2, padx=default_padx, pady=default_pady)
        self.abort_button.config(state=tk.DISABLED)
        mode_options = ('file', 'line', 'raw')
        self.mode = tk.StringVar()
        self.mode.trace('w', mode_changed)
        self.mode.set(mode_options[0])
        mode_combo_box = tk.OptionMenu(self.root, self.mode, *mode_options)
        mode_combo_box.config(font=default_font)
        mode_combo_box.grid(column=0, row=2, padx=default_padx, pady=default_pady)
        #info label
        info_label = tk.Label(self.root, font=default_font, anchor=tk.W)
        info_label.grid(column=0, row=3, columnspan=3, padx=default_padx, pady=default_pady, sticky=tk.W)
        self.info_label = info_label
        #simulator canvas
        self.simulator_canvas = tk.Canvas(self.root, height=200, width=200, bg='white')
        self.simulator_canvas.grid(column=4, row=1, rowspan=3, columnspan=2)
        simulate_button = tk.Button(self.root, text='Simulate', command=simulate_button_clicked, font=default_font)
        simulate_button.grid(column=4, row=0, padx=default_padx, pady=default_pady)
        clear_button = tk.Button(self.root, text='Clear', command=clear_button_clicked, font=default_font)
        clear_button.grid(column=5, row=0, padx=default_padx, pady=default_pady)
        #oval = self.simulator_canvas.create_oval(10, 30, 40, 50)
        
        
        self.root.mainloop()
        
    def process_file(self):
        if self._current_line is not None:
            self.process_line(self._current_line)
            
        for line in self._file:
            if self._abort_move:
                self.steps = None
                self._current_counter = 0
                self.start_button['text'] = 'Start plot'
                self.start_button.config(state=tk.NORMAL)
                break
            self._current_line = line
            try:
                self.process_line(line)
            except RuntimeError:
                self.finish()                
                return
        self._current_line = None
        self.finish()
    
    def process_line(self, line):
        self.info_label['text'] = ''
        line = line.upper()
        line = line.strip()
        if line.startswith('G') and not self.do_simulation:
            LaserDriver.current_steps_x = LaserDriver.get_current_steps('x')
            LaserDriver.current_steps_y = LaserDriver.get_current_steps('y')
        
        if line.startswith('G00'):
            position = LaserDriver.parse_line(line)
            self.steps = LaserDriver.move_linear(position, engrave=False)
        elif line.startswith('G01'):
            position = LaserDriver.parse_line(line)
            self.steps = LaserDriver.move_linear(position, engrave=True)
        elif line.startswith('G02'):
            position, center = LaserDriver.parse_line(line)
            self.steps = LaserDriver.move_circular(position, center, 'cw')
        elif line.startswith('G03'):
            position, center = LaserDriver.parse_line(line)
            self.steps = LaserDriver.move_circular(position, center, 'ccw')
        elif line.startswith('('):
            # Comments from inkscape Gcodetools are in paranthesis
            pass
        else:
            print('unrecognized command')
        
        try:
            if self.do_simulation:
                self.execute_simulation_move()
            else:
                self.execute_move()
        except RuntimeError:
            pass
        finally:
            if self.mode.get() == 'line':
                self.finish()
    
    def process_raw(self, raw):
        res = LaserDriver.send_raw(raw)
        self.info_label['text'] = res
        self.finish()
    
    def execute_move(self):
        if self.steps is not None:
            try:
                LaserDriver.execute_move(self.steps[self._current_counter:])
            except RuntimeError as e:
                message, counter = e.args
                self._current_counter += counter
                self.info_label['text'] = message
                self.start_button['text'] = 'Resume plot'
                self.start_button.config(state=tk.NORMAL)
                raise
            else:
                self.steps = None
                self._current_counter = 0
                self.start_button['text'] = 'Start plot'
                self.start_button.config(state=tk.NORMAL)
    
    def execute_simulation_move(self):
        min_x = min_y = np.inf
        max_x = max_y = -np.inf
        if self.steps is not None:
            for step in self.steps:
                if step[0] == 'x':
                    step_mm = step[1]/LaserDriver.x_steps_per_mm
                    if step_mm > max_x:
                        max_x = step_mm
                    if step_mm < min_x:
                        min_x = step_mm
                if step[0] == 'y':
                    step_mm = step[1]/LaserDriver.y_steps_per_mm
                    if step_mm > max_y:
                        max_y = step_mm
                    if step_mm < min_y:
                        min_y = step_mm
                        
            last_x = LaserDriver.current_steps_x
            last_y = LaserDriver.current_steps_y
            counter = 0
            while True:
                if counter >= len(self.steps):
                    break
                else:
                    step = self.steps[counter]
                    x = y = 0
                    if step[0] == 'x':
                        step_mm = step[1]/LaserDriver.x_steps_per_mm
                        x = step_mm
                        y = last_y
                        last_x = x
                    if step[0] == 'y':
                        step_mm = step[1]/LaserDriver.y_steps_per_mm
                        x = last_x
                        y = step_mm
                        last_y = y
                    self.simulator_canvas.create_oval(x-1, 200-y+1, x+1, 200-y-1, fill='black')
                counter += 1

    def finish(self):
        self.start_button.config(state=tk.NORMAL)
        self.abort_button.config(state=tk.DISABLED)
        self.connect_button.config(state=tk.NORMAL)
        self.do_simulation = False
        self._abort_move = False
                
if __name__ == '__main__':
    GUI = LaserGUI()    
    GUI.create_gui()

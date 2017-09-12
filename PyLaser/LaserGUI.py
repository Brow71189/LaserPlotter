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

class LaserGUI(object):
    def __init__(self):
        self.root = None
        self.gcodefile = None
        self._current_line = None
        self.mode = None
        self._file = None
        self.info_label = None
        self.steps = None
        self._abort_move = False
        self._current_counter = 0
        self._thread = None

    def create_gui(self):
        self.root = tk.Tk()
        # Fonts definitions
        default_font = font.Font()
        file_name_font = font.Font(slant='italic')
        # Spacing definitions
        default_padx = 5
        default_pady = 2
        
        def connect_button_clicked():
            info_label['text'] = ''
            if connect_button['text'] == 'Connect to plotter':
                try:
                    LaserDriver.main()
                except Exception as e:
                    self.info_label['text'] = str(e)
                    return
                else:
                    connect_button['text'] = 'Disconnect'
            elif connect_button['text'] == 'Disconnect':
                LaserDriver.close()
                self.info_label['text'] = 'Connect to plotter'

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
            
        # Elements for "file" mode
        current_file_text = tk.Label(self.root, text='Current file:', font=default_font)
        current_file_text.grid(column=0, row=1, padx=default_padx, pady=default_pady)
        current_file_name = tk.Label(self.root, text='/home/Andi/test.ngc', font=file_name_font)
        current_file_name.grid(column=1, row=1, padx=default_padx, pady=default_pady)
        open_button = tk.Button(self.root, text='Open Gcode file', command=open_button_clicked, font=default_font)
        open_button.grid(column=3, row=1, padx=default_padx, pady=default_pady)
        # Elements for "line" mode
        line_descriptor = tk.Label(self.root, text='Gcode line:', font=default_font)
        line_descriptor.grid(column=0, row=1, padx=default_padx, pady=default_pady)
        line_entry = tk.Entry(self.root, font=default_font)
        line_entry.grid(column=1, row=1, padx=default_padx, pady=default_pady)
        # Elements for "raw" mode
        raw_descriptor = tk.Label(self.root, text='Raw movement command:', font=default_font)
        raw_descriptor.grid(column=0, row=1, padx=default_padx, pady=default_pady)
        raw_entry = tk.Entry(self.root, font=default_font)
        raw_entry.grid(column=1, row=1, padx=default_padx, pady=default_pady)
        # Other elements
        connect_button = tk.Button(self.root, text='Connect to plotter', command=connect_button_clicked, font=default_font)
        connect_button.grid(column=0, row=0, padx=default_padx, pady=default_pady)
        self.start_button = tk.Button(self.root, text='Start plot', command=start_button_clicked, font=default_font)
        self.start_button.grid(column=3, row=2, padx=default_padx, pady=default_pady)
        self.abort_button = tk.Button(self.root, text='Abort plot', command=abort_button_clicked, font=default_font)
        self.abort_button.grid(column=2, row=2, padx=default_padx, pady=default_pady)
        mode_options = ('file', 'line', 'raw')
        self.mode = tk.StringVar()
        self.mode.trace('w', mode_changed)
        self.mode.set(mode_options[0])
        mode_combo_box = tk.OptionMenu(self.root, self.mode, *mode_options)
        mode_combo_box.config(font=default_font)
        mode_combo_box.grid(column=0, row=2, padx=default_padx, pady=default_pady)
        #info label
        info_label = tk.Label(self.root, font=default_font, anchor=tk.W)
        info_label.grid(column=0, row=3, columnspan=3, padx=default_padx, pady=default_pady)
        self.info_label = info_label
        
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
                return
        self._current_line = None
    
    def process_line(self, line):
        global current_steps_x, current_steps_y
        self.info_label['text'] = ''
        line = line.upper()
        line = line.strip()
        if line.startswith('G'):
            current_steps_x = LaserDriver.get_current_steps('x')
            current_steps_y = LaserDriver.get_current_steps('y')
        
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
            self.execute_move()
        except RuntimeError:
            pass
    
    def process_raw(self, raw):
        res = LaserDriver.send_raw(raw)
        self.info_label['text'] = res
    
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
                
if __name__ == '__main__':
    GUI = LaserGUI()    
    GUI.create_gui()

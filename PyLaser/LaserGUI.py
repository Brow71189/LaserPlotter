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

class LaserGUI(object):
    def __init__(self):
        self.root = None
        self.gcodefile = None
        self.current_line = None
        self.mode = None
        self._file = None

    def create_gui(self):
        self.root = tk.Tk()
        # Fonts definitions
        default_font = font.Font()
        file_name_font = font.Font(slant='italic')
        # Spacing definitions
        default_padx = 5
        default_pady = 2
        
        description_label = tk.Label(self.root, text="Hello, world!", font=default_font)
        description_label.grid(column=0, row=0)

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
                else:
                    self.process_file()
            elif self.mode.get() == 'line':
                self.process_line(line_entry.get())
            elif self.mode.get() == 'raw':
                self.process_raw(raw_entry.get())
        
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
        open_button.grid(column=2, row=1, padx=default_padx, pady=default_pady)
        # Elements for "line" mode
        line_descriptor = tk.Label(self.root, text='Gcode line:', font=default_font)
        line_descriptor.grid(column=0, row=1, padx=default_padx, pady=default_pady)
        line_entry = tk.Entry(self.root, font=default_font)
        line_entry.grid(column=1, row=1, padx=default_padx, pady=default_pady)
        # Elements ofr "raw" mode
        raw_descriptor = tk.Label(self.root, text='Raw movement command:', font=default_font)
        raw_descriptor.grid(column=0, row=1, padx=default_padx, pady=default_pady)
        raw_entry = tk.Entry(self.root, font=default_font)
        raw_entry.grid(column=1, row=1, padx=default_padx, pady=default_pady)
        # Other elements
        start_button = tk.Button(self.root, text='Start plot', command=start_button_clicked, font=default_font)
        start_button.grid(column=3, row=2, padx=default_padx, pady=default_pady)
        mode_options = ('file', 'line', 'raw')
        self.mode = tk.StringVar()
        self.mode.trace('w', mode_changed)
        self.mode.set(mode_options[0])
        mode_combo_box = tk.OptionMenu(self.root, self.mode, *mode_options)
        mode_combo_box.config(font=default_font)
        mode_combo_box.grid(column=0, row=2, padx=default_padx, pady=default_pady)
        #info label
        info_label = tk.Label(self.root, font=default_font)
        info_label.grid(column=0, row=3, columnspan=3, padx=default_padx, pady=default_pady)
        
        self.root.mainloop()
        
    def process_file(self):
        pass
    
    def process_line(self, line):
        pass
    
    def process_raw(self, raw):
        pass

if __name__ == '__main__':
    GUI = LaserGUI()    
    GUI.create_gui()

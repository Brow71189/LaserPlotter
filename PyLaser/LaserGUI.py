# -*- coding: utf-8 -*-
"""
Created on Sun Aug 27 16:48:31 2017

@author: andi
"""

import tkinter as tk
from tkinter import filedialog
import LaserDriver
import os

class LaserGUI(object):
    def __init__(self):
        self.root = None
        self.gcodefile = None
        self.current_line = None

    def show_gui(self):
        self.root = tk.Tk()
        description_label = tk.Label(self.root, text="Hello, world!")
        description_label.pack()
        def open_button_clicked():
            filename = ''
            while not os.path.isfile(filename):
                filename = filedialog.askopenfilename()
                if len(filename) == 0:
                    break
            if len(filename) > 0:
                self.gcodefile = filename
            
        open_button = tk.Button(self.root, text="Open Gcode file", command=open_button_clicked)
        open_button.pack()        
        
        self.root.mainloop()

if __name__ == '__main__':
    GUI = LaserGUI()    
    GUI.show_gui()

# -*- coding: utf-8 -*-
"""
Created on Sat Feb 17 10:50:14 2018

@author: Andi
"""

from flexx import app, event, ui
import time

class AppRoot(app.PyComponent):
    """
    Root widget
    This class talks to the Laser Driver module and handles the connection to the ui
    It also saves the state of all variables
    """
    gcode_file = event.StringProp()
    gcode_line = event.StringProp()
    raw_command = event.StringProp()
    current_mode = event.StringProp('File Mode')
    plot_running = event.BoolProp()
    simulate = event.BoolProp()
    settings = event.DictProp()
    
    def init(self):
        self.view = View()
        
    @event.action
    def set_current_mode(self, mode):
        self._mutate_current_mode(mode)
        self.update_info_label(self.current_mode)
        
    @event.action
    def handle_connect_clicked(self):
        self.update_info_label('connect')
    
    @event.action
    def handle_abort_clicked(self):
        self.update_info_label('abort')
    
    @event.action
    def handle_start_clicked(self):
        self.update_info_label('start')
        
    @event.action
    def update_info_label(self, text):
        self.view.update_info_label(text)
        
class View(ui.Widget):
    """
    Contains all the ui elements and creates the Layout of the app
    """
    def init(self):
        with ui.HSplit():
            with ui.VBox(flex=2):
                self.tab_panel = TabPanel(flex=3)
                self.control_panel = ControlPanel(flex=1)
                    
            self.plot_panel = PlotPanel(flex=1)
    
    @event.action
    def update_info_label(self, text):
        self.control_panel.update_info_label(text)

class TabPanel(ui.Widget):
    """
    Contains the tabs for the different modes
    """
    def init(self):
        with ui.TabLayout() as self.tabs:
            self.file_tab = FileTab()
            self.line_tab = LineTab()
            self.raw_tab = RawTab()
            self.settings_tab = SettingsTab()
    
    @event.reaction('tabs.current')
    def _current_tab_changed(self, *events):
        old_v = events[0].old_value
        new_v = events[-1].new_value
        if old_v is None or new_v is None:
            return
        
        if (self.root.plot_running and old_v.title != new_v.title and new_v.title != 'Settings' and
            new_v.title != self.root.current_mode):
            
            self.tabs.set_current(old_v)
        elif new_v.title != 'Settings':
            self.root.set_current_mode(new_v.title)        

class ControlPanel(ui.Widget):
    """
    This class contains all the ui elements to control the laser plotter
    """
    def init(self):
        with ui.VBox():
            with ui.HBox(flex=1):
                self.connect_button = ui.Button(flex=1, text='Connect to plotter', title='connect')
                ui.Label(flex=1)
                self.abort_button = ui.Button(flex=1, text='Abort plot', title='abort')
                self.start_button = ui.Button(flex=1, text='Start plot', title='start')
            
            self.info_label = ui.Label(flex=1, wrap=True, text='Status Label')
    
    @event.action
    def update_info_label(self, text):
        self.info_label.set_text(text)
    
    @event.action
    def clear_info_label(self):
        self.update_info_label('')
        
    @event.reaction('connect_button.mouse_click', 'abort_button.mouse_click', 'start_button.mouse_click')
    def _button_clicked(self, *events):
        ev = events[-1]
        if ev.source.title == 'connect':
            self.root.handle_connect_clicked()
        elif ev.source.title == 'abort':
            self.root.handle_abort_clicked()
        elif ev.source.title == 'start':
            self.root.handle_start_clicked()
            

class PlotPanel(ui.Widget):
    """
    This class contains the panel where the simulated plot is drawn
    """

class FileTab(ui.Widget):
    """
    Tab for file plotting mode
    """
    title = event.StringProp('File mode')
    
    def init(self):
        with ui.VBox():
            ui.HBox(flex=1)
            with ui.HBox(flex=0):
                self.path_label = ui.LineEdit(flex=3, text='C:/Path/to/Gcode/File.gcode', disabled=True)
                self.open_button = ui.Button(flex=1, text='Open...')
            ui.HBox(flex=4)
            
    @event.reaction('open_button.mouse_click')
    def _button_clicked(self, *events):
        self.root.update_info_label('open clicked')
    
    
class LineTab(ui.Widget):
    """
    Tab for line plotting mode
    """
    title = event.StringProp('Line mode')
    
    def init(self):
        with ui.VBox():
            ui.HBox(flex=1)
            with ui.HBox(flex=0):
                self.gcode_line = ui.LineEdit(flex=3, placeholder_text='e.g. G01 Y10 Y2 Z-1')
            ui.HBox(flex=4)
    
class RawTab(ui.Widget):
    """
    Tab for raw plotting mode
    """
    title = event.StringProp('Raw mode')
    
    def init(self):
        with ui.VBox():
            ui.HBox(flex=1)
            with ui.HBox(flex=0):
                self.gcode_line = ui.LineEdit(flex=3, placeholder_text='e.g. XA1000')
            ui.HBox(flex=4)
    
class SettingsTab(ui.Widget):
    """
    Tab for settings
    """
    title = event.StringProp('Settings')

class Example(ui.Widget):

    def init(self):
        with ui.HSplit():
            ui.Button(text='foo')
            with ui.VBox():
                ui.Button(flex=1, text='bar')
                ui.Button(flex=1, text='spam')

#example = app.serve(Example)
#app.export(Example, 'example.html')
#example = app.serve(Example)
a = app.App(AppRoot)
#a.serve()
#app.start()
a.launch()
app.run()
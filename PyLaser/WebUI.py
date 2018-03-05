# -*- coding: utf-8 -*-
"""
Created on Sat Feb 17 10:50:14 2018

@author: Andi
"""

from flexx import app, event, ui

import sys, os
sys.path.append(os.path.dirname(__file__))

from logging import StreamHandler

from _file import OpenFileWidget
from flexx.pyscript import window

import LaserDriver


class AppRoot(app.PyComponent):
    """
    Root widget
    This class talks to the Laser Driver module and handles the connection to the ui
    It also saves the state of all variables
    """    
    gcode_file = event.StringProp()
    gcode_line = event.StringProp()
    raw_command = event.StringProp()
    current_mode = event.StringProp('file')
    state = event.StringProp('idle')
    #plot_running = event.BoolProp()
    simulate = event.BoolProp()
    settings = event.DictProp()#{'resolution': 150, 'serial_port': 1, 'serial_baudrate': 19200, 'x_steps_per_mm': 378,
                               #'y_steps_per_mm': 12, 'fast_movement_speed': 10, 'engraving_movement_speed': 2,
                               #'use_gcode_speeds': False}
    states = event.DictProp()
    
    settings_types = {'resolution': float, 'serial_port': str, 'serial_baudrate': int, 'x_steps_per_mm': float,
                      'y_steps_per_mm': float, 'fast_movement_speed': float, 'engraving_movement_speed': float,
                      'use_gcode_speeds': bool}
    
    def init(self):
        self.laser_driver = LaserDriver.LaserDriver()
        self.laser_driver.callback_function = self.low_level_parameter_changed
        self.view = View()
        self.initialize_UI()
        
    @property
    def plot_running(self):
        return event.BoolProp(self.state == 'active')
        
    @event.action
    def initialize_UI(self):
        try:
            self.laser_driver.logger.addHandler(StreamHandler(stream=StreamToInfoLabel(self.update_info_label)))
        except Exception as e:
            print(str(e))
            
        settings = {'resolution': self.laser_driver.resolution,
                    'serial_port': self.laser_driver.serial_port,
                    'serial_baudrate': self.laser_driver.serial_baudrate,
                    'x_steps_per_mm': self.laser_driver.x_steps_per_mm,
                    'y_steps_per_mm': self.laser_driver.y_steps_per_mm,
                    'fast_movement_speed': self.laser_driver.fast_movement_speed,
                    'engraving_movement_speed': self.laser_driver.engraving_movement_speed,
                    'use_gcode_speeds': self.laser_driver.use_gcode_speeds}
        states = { 'idle': [('start_button.text', 'Start plot'),
                            ('start_button.disabled', True),
                            ('abort_button.text', 'Abort plot'),
                            ('abort_button.disabled', True),
                            ('connect_button.text', 'Connect to plotter'),
                            ('connect_button.disabled', False)],
                   'ready': [('start_button.text', 'Start plot'),
                             ('start_button.disabled', False),
                             ('abort_button.text', 'Abort plot'),
                             ('abort_button.disabled', True),
                             ('connect_button.text', 'Disconnect from plotter'),
                             ('connect_button.disabled', False)],
                   'active': [('start_button.text', 'Pause plot'),
                              ('start_button.disabled', False),
                              ('abort_button.text', 'Abort plot'),
                              ('abort_button.disabled', False),
                              ('connect_button.text', 'Disconnect from plotter'),
                              ('connect_button.disabled', True)],
                   'error': [('start_button.text', 'Resume plot'),
                             ('start_button.disabled', False),
                             ('abort_button.text', 'Abort plot'),
                             ('abort_button.disabled', False),
                             ('connect_button.text', 'Disconnect from plotter'),
                             ('connect_button.disabled', True)],
                   'pause': [('start_button.text', 'Resume plot'),
                             ('start_button.disabled', False),
                             ('abort_button.text', 'Abort plot'),
                             ('abort_button.disabled', False),
                             ('connect_button.text', 'Disconnect from plotter'),
                             ('connect_button.disabled', True)]
                   }
        
        self._mutate_settings(settings,'set')
        self._mutate_states(states, 'set')
        
    @event.action
    def set_current_mode(self, mode):
        self._mutate_current_mode(mode)
        self.update_info_label(self.current_mode)
        
    @event.action
    def handle_connect_clicked(self):
        if self.state == 'idle':
            self.laser_driver.execute_command('start connection')
            self.update_info_label('connected')
        elif self.state == 'ready':
            self.laser_driver.execute_command('close connection')
            self.update_info_label('disconnected')
    
    @event.action
    def handle_abort_clicked(self):
        self.laser_driver.abort()
        self.update_info_label('abort')
    
    @event.action
    def handle_start_clicked(self):
        if self.state == 'ready':
            contents = {'file': self.gcode_file, 'line': self.gcode_line, 'raw': self.raw_command}
            self.laser_driver.execute_command(self.current_mode, content=contents[self.current_mode])
            self.update_info_label('start')
        elif self.state in {'pause', 'error'}:
            self.laser_driver.execute_command(self.current_mode)
            self.update_info_label('resume')
        elif self.state == 'active':
            self.laser_driver.pause()
            self.update_info_label('pause')
        
    @event.action
    def handle_use_gcode_speeds_clicked(self, checked):
        self._mutate_settings({'use_gcode_speeds': checked}, 'replace')
        self.update_info_label('use gcode speeds {}'.format('ON' if checked else 'OFF'))

    @event.action
    def handle_new_gcode_file(self, file_content):
        self._mutate_gcode_file(file_content)
        self.update_info_label('new gcode file arrived')
    
    @event.action
    def handle_setting_changed(self, setting_name, new_value):
        old_value = self.settings.get(setting_name)
        try:
            new_value = self.settings_types[setting_name](new_value)
        except ValueError:
            self.propagate_change('settings')
        except KeyError as e:
            print(e)
        else:
            if old_value is not None and new_value != old_value:
                self._mutate_settings({setting_name: new_value}, 'replace')
    
    @event.action
    def update_info_label(self, text):
        self.view.update_info_label(text)
        
    @event.action
    def propagate_change(self, name_changed):
        self.view.propagate_change(name_changed)
    
    @event.action
    def low_level_parameter_changed(self, description_dict):
        if description_dict.get('action') == 'set':
            if description_dict.get('parameter') == 'state':
                self._mutate_state(description_dict.get('value'))
        elif description_dict.get('action') == 'done':
            pass
        
    @event.reaction('gcode_file', 'gcode_line', 'raw_command', 'current_mode', 'simulate', 'settings', 'state')
    def property_changed(self, *events):
        for ev in events:
            if ev.type == 'settings':
                if ev.mutation == 'replace':
                    for key, value in ev.objects.items():
                        setattr(self.laser_driver, key, value)
                elif ev.mutation == 'set':
                    for key, value in ev.new_value.items():
                        setattr(self.laser_driver, key, value)
                self.propagate_change('settings')
            elif ev.type == 'state':
                self.propagate_change('state')
                self.update_info_label(ev.new_value)
                        
    
class View(ui.Widget):
    """
    Contains all the ui elements and creates the Layout of the app
    """
    CSS = """
    .flx-Button[disabled] {
            color: gray;
    }
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
        
    @event.action
    def propagate_change(self, name_changed):
        self.tab_panel.propagate_change(name_changed)
        self.control_panel.propagate_change(name_changed)
        self.plot_panel.propagate_change(name_changed)

class TabPanel(ui.Widget):
    """
    Contains the tabs for the different modes
    """
    modes = event.Dict({'File mode': 'file', 'Line mode': 'line', 'Raw mode': 'raw'})
    
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
            self.root.set_current_mode(self.modes[new_v.title])
            
    @event.action
    def propagate_change(self, name_changed):
        self.file_tab.propagate_change(name_changed)
        self.line_tab.propagate_change(name_changed)
        self.raw_tab.propagate_change(name_changed)
        self.settings_tab.propagate_change(name_changed)

class ControlPanel(ui.Widget):
    """
    This class contains all the ui elements to control the laser plotter
    """
    
    def init(self):
        with ui.VBox():
            with ui.HBox(flex=0):
                self.connect_button = ui.Button(flex=1, text='Connect to plotter', title='connect')
                ui.Widget(flex=1)
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
            
    @event.action
    def propagate_change(self, name_changed):
        if name_changed == 'state':
            new_properties = self.root.states.get(self.root.state)
            if new_properties is not None:
                for key, value in new_properties:
                    element, prop = key.split('.')
                    getattr(getattr(self, element), 'set_' + prop)(value)
            

class PlotPanel(ui.Widget):
    """
    This class contains the panel where the simulated plot is drawn
    """                
    def init(self):
        with ui.VFix():
            self.drawing = Drawing()
            

    @event.action
    def propagate_change(self, name_changed):
        pass

class FileTab(ui.Widget):
    """
    Tab for file plotting mode
    """
    title = event.StringProp('File mode')
    
    def init(self):
        with ui.VBox():
            ui.Widget(flex=1)
            ui.Label(flex=0, text='Select a gcode file here:')
            #with ui.HBox(flex=0):
                #self.path_label = ui.LineEdit(flex=3, text='C:/Path/to/Gcode/File.gcode', disabled=True)
                #self.open_button = ui.Button(flex=1, text='Open...', title='open')
            self.open_gcode_widget = OpenFileWidget()
            ui.Widget(flex=1)
            with ui.HBox(flex=0):
                self.use_gcode_speeds_button = ui.ToggleButton(flex=0, text='Use gcode speeds', title='use_gcode_speed')
                ui.Widget(flex=1)
            ui.Widget(flex=8)
            
#    @event.reaction('open_button.mouse_click')
#    def _button_clicked(self, *events):
#        ev = events[-1]
#        if ev.source.title == 'open':
#            self.root.update_info_label('open clicked')

    @event.reaction('use_gcode_speeds_button.checked')  
    def _button_toggled(self, *events):
        self.root.handle_use_gcode_speeds_clicked(self.use_gcode_speeds_button.checked)
        
    @event.reaction('open_gcode_widget.file')
    def _new_gcode_file_loaded(self):
        self._convert_gcode_file_to_string()
        
    @event.action
    def _convert_gcode_file_to_string(self):
        def _get_string(event):
            self.root.handle_new_gcode_file(event.target.result)
            print(event.target.result)
        
        if self.open_gcode_widget.file is not None:
            reader = window.FileReader()
            reader.onload = _get_string
            reader.readAsText(self.open_gcode_widget.file)

    @event.action
    def propagate_change(self, name_changed):
        if name_changed == 'settings':
            self.use_gcode_speeds_button.set_checked(self.root.settings.get('use_gcode_speeds', self.use_gcode_speeds_button.checked))
    
    
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
            
    @event.action
    def propagate_change(self, name_changed):
        pass
    
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
            
    @event.action
    def propagate_change(self, name_changed):
        pass
    
class SettingsTab(ui.Widget):
    """
    Tab for settings
    """
    title = event.StringProp('Settings')
    
    def init(self):
        with ui.VBox():
            with ui.HFix(flex=1):
                with ui.VBox(flex=2):
                    ui.Label(text='Resolution (dpi): ')
                    ui.Label(text='Serial port: ')
                    ui.Label(text='Serial baudrate: ')
                    ui.Label(text='Steps per mm (x, y): ')
                    ui.Label(text='Speed in mm/s (fast, engrave): ')
                with ui.VBox(flex=1):
                    self.resolution_widget = ui.LineEdit(title='resolution')
                    self.serial_port_widget = ui.LineEdit(title='serial_port')
                    self.serial_baudrate_widget = ui.LineEdit(title='serial_baudrate')
                    with ui.HBox():
                        self.x_steps_widget = ui.LineEdit(title='x_steps_per_mm')
                        self.y_steps_widget = ui.LineEdit(title='y_steps_per_mm')
                    with ui.HBox():
                        self.fast_speed_widget = ui.LineEdit(title='fast_movement_speed')
                        self.engrave_speed_widget = ui.LineEdit(title='engraving_movement_speed')
                        
            
            ui.Widget(flex=1)
    
    @event.reaction('resolution_widget.submit', 'serial_port_widget.submit', 'serial_baudrate_widget.submit',
                    'x_steps_widget.submit', 'y_steps_widget.submit', 'fast_speed_widget.submit',
                    'engrave_speed_widget.submit')
    def _settings_changed(self, *events):
        ev = events[-1]
        self.root.handle_setting_changed(ev.source.title, ev.source.text)
        
    @event.action
    def propagate_change(self, name_changed):
        if name_changed == 'settings':
            self.resolution_widget.set_text(str(self.root.settings.get('resolution', self.resolution_widget.text)))
            self.serial_port_widget.set_text(str(self.root.settings.get('serial_port', self.serial_port_widget.text)))
            self.serial_baudrate_widget.set_text(str(self.root.settings.get('serial_baudrate', self.serial_baudrate_widget.text)))
            self.x_steps_widget.set_text(str(self.root.settings.get('x_steps_per_mm', self.x_steps_widget.text)))
            self.y_steps_widget.set_text(str(self.root.settings.get('y_steps_per_mm', self.y_steps_widget.text)))
            self.fast_speed_widget.set_text(str(self.root.settings.get('fast_movement_speed', self.fast_speed_widget.text)))
            self.engrave_speed_widget.set_text(str(self.root.settings.get('engraving_movement_speed', self.engrave_speed_widget.text)))

class StreamToInfoLabel(object):
    def __init__(self, write_to_info_label_method):
        self.write_to_info_label_method = write_to_info_label_method
    
    def write(self, s):
        if callable(self.write_to_info_label_method) and s.strip():
            self.write_to_info_label_method(s)
    
    def flush(self):
        pass

class Drawing(ui.CanvasWidget):
    def init(self):
        super().init()
        self.ctx = self.node.getContext('2d')
        self.set_capture_mouse(1)
        self._last_pos = (0, 0)

    @event.reaction('mouse_move')
    def on_move(self, *events):
        for ev in events:
            self.ctx.beginPath()
            self.ctx.strokeStyle = '#080'
            self.ctx.lineWidth = 3
            self.ctx.lineCap = 'round'
            self.ctx.moveTo(*self._last_pos)
            self.ctx.lineTo(*ev.pos)
            self.ctx.stroke()
            self._last_pos = ev.pos

    @event.reaction('mouse_down')
    def on_down(self, *events):
        self._last_pos = events[-1].pos
 
#class Example(ui.Widget):
#
#    def init(self):
#        with ui.HSplit():
#            ui.Button(text='foo')
#            with ui.VBox():
#                ui.Button(flex=1, text='bar')
#                ui.Button(flex=1, text='spam')

#example = app.serve(Example)
#app.export(Example, 'example.html')
#example = app.serve(Example)
a = app.App(AppRoot)
#a.serve()
#app.start()
a.launch()
app.run()
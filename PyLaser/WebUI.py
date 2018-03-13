# -*- coding: utf-8 -*-
"""
Created on Sat Feb 17 10:50:14 2018

@author: Andi
"""

from flexx import app, event, ui, config

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
    settings = event.DictProp()#{'resolution': 150, 'serial_port': 1, 'serial_baudrate': 19200, 'x_steps_per_mm': 378,
                               #'y_steps_per_mm': 12, 'fast_movement_speed': 10, 'engraving_movement_speed': 2,
                               #'use_gcode_speeds': False}
    states = event.DictProp()
    simulation_states = event.DictProp()

    settings_types = {'resolution': float, 'serial_port': str, 'serial_baudrate': int, 'x_steps_per_mm': float,
                      'y_steps_per_mm': float, 'fast_movement_speed': float, 'engraving_movement_speed': float,
                      'use_gcode_speeds': bool, 'simulation_mode': int, 'burnin_time': float}

    state_ = event.StringProp('idle', settable=True)

    def init(self):
        self._state = 'idle'
        self._simulation_state = 'idle'
        self.laser_driver = LaserDriver.LaserDriver()
        self.laser_driver.callback_function = self.low_level_parameter_changed
        self.view = View()
        self.initialize_UI()

    @property
    def state(self):
        if self.settings.get('simulation_mode') < 2:
            return self._state
        else:
            if self._simulation_state == 'idle':
                self.state = 'ready'
            return self._simulation_state

    @state.setter
    def state(self, new_state):
        if self.settings.get('simulation_mode') < 2:
            self._state = new_state
        else:
            self._simulation_state = new_state
        self.__state_changed(new_state)

    @event.action
    def __state_changed(self, new_state):
        self._mutate_state_(new_state)
        self.emit('state_', {'new_value': new_state})

    @event.action
    def initialize_UI(self):
        try:
            self.laser_driver.logger.addHandler(StreamHandler(stream=StreamToInfoLabel(lambda text: event.loop.call_soon(self.update_info_label, text))))
        except Exception as e:
            print(str(e))

        settings = {'resolution': self.laser_driver.resolution,
                    'serial_port': self.laser_driver.serial_port,
                    'serial_baudrate': self.laser_driver.serial_baudrate,
                    'x_steps_per_mm': self.laser_driver.x_steps_per_mm,
                    'y_steps_per_mm': self.laser_driver.y_steps_per_mm,
                    'fast_movement_speed': self.laser_driver.fast_movement_speed,
                    'engraving_movement_speed': self.laser_driver.engraving_movement_speed,
                    'use_gcode_speeds': self.laser_driver.use_gcode_speeds,
                    'simulation_mode': self.laser_driver.simulation_mode,
                    'burnin_time': self.laser_driver.burnin_time}
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

        simulation_states = { 'idle': [('start_button.text', 'Start plot'),
                            ('start_button.disabled', False),
                            ('abort_button.text', 'Abort plot'),
                            ('abort_button.disabled', True),
                            ('connect_button.disabled', True)],
                   'ready': [('start_button.text', 'Start plot'),
                             ('start_button.disabled', False),
                             ('abort_button.text', 'Abort plot'),
                             ('abort_button.disabled', True),
                             ('connect_button.disabled', True)],
                   'active': [('start_button.text', 'Pause plot'),
                              ('start_button.disabled', False),
                              ('abort_button.text', 'Abort plot'),
                              ('abort_button.disabled', False),
                              ('connect_button.disabled', True)],
                   'error': [('start_button.text', 'Resume plot'),
                             ('start_button.disabled', False),
                             ('abort_button.text', 'Abort plot'),
                             ('abort_button.disabled', False),
                             ('connect_button.disabled', True)],
                   'pause': [('start_button.text', 'Resume plot'),
                             ('start_button.disabled', False),
                             ('abort_button.text', 'Abort plot'),
                             ('abort_button.disabled', False),
                             ('connect_button.disabled', True)]
                   }

        self._mutate_settings(settings,'set')
        self._mutate_states(states, 'set')
        self._mutate_simulation_states(simulation_states, 'set')

    @event.action
    def on_raw_text_changed(self, text):
        self._mutate_raw_command(text)

    @event.action
    def on_gcode_line_text_changed(self, text):
        self._mutate_gcode_line(text)

    @event.action
    def set_current_mode(self, mode):
        self._mutate_current_mode(mode)
        #self.update_info_label(self.current_mode)

    @event.action
    def handle_connect_clicked(self):
        self.update_info_label('')
        if self.state == 'idle':
            self.laser_driver.execute_command('start connection')
            #self.update_info_label('connected')
        elif self.state == 'ready':
            self.laser_driver.execute_command('close connection')
            #self.update_info_label('disconnected')

    @event.action
    def handle_abort_clicked(self):
        self.update_info_label('')
        self.laser_driver.abort()
        #self.update_info_label('abort')

    @event.action
    def handle_start_clicked(self):
        self.update_info_label('')
#        if self.current_mode == 'raw':
#            self.propagate_change(self.raw_command)
        if self.state == 'ready':
            contents = {'file': self.gcode_file, 'line': self.gcode_line, 'raw': self.raw_command}
            self.laser_driver.execute_command(self.current_mode, content=contents[self.current_mode])
            #self.update_info_label('start')
        elif self.state in {'pause', 'error'}:
            self.laser_driver.execute_command(self.current_mode)
            #self.update_info_label('resume')
        elif self.state == 'active':
            self.laser_driver.pause()
            #self.update_info_label('pause')

    @event.action
    def handle_use_gcode_speeds_clicked(self, checked):
        self._mutate_settings({'use_gcode_speeds': checked}, 'replace')
        #self.update_info_label('use gcode speeds {}'.format('ON' if checked else 'OFF'))

    @event.action
    def handle_new_gcode_file(self, file_content):
        self._mutate_gcode_file(file_content)
        #self.update_info_label('new gcode file arrived')

    @event.action
    def handle_setting_changed(self, setting_name, new_value):
        old_value = self.settings.get(setting_name)
        try:
            new_value = self.settings_types[setting_name](new_value)
        except ValueError as e:
            self.propagate_change('settings')
            self.update_info_label(str(e))
        except KeyError as e:
            self.update_info_label(str(e))
        else:
            if old_value is not None and new_value != old_value:
                self._mutate_settings({setting_name: new_value}, 'replace')

    @event.action
    def handle_state_changed(self, new_state):
        self.state = new_state

    @event.action
    def update_info_label(self, text):
        if hasattr(self, 'view'):
            self.view.update_info_label(text)

    @event.action
    def propagate_change(self, name_changed):
        if hasattr(self, 'view'):
            self.view.propagate_change(name_changed)

    def low_level_parameter_changed(self, description_dict):
        event.loop.call_soon(self.main_thread_callback, description_dict)

    @event.action
    def main_thread_callback(self, description_dict):
        if description_dict.get('action') == 'set':
            if description_dict.get('parameter') == 'state':
                self.state = description_dict.get('value')
        elif description_dict.get('action') == 'done':
            if description_dict.get('value') == 'raw' and description_dict.get('position') is not None:
                position = description_dict['position']
                movement = 'move cursor:'
                if position.get('z', 0) > 0:
                    movement = 'line to:'
                command = '{:s}{:g} {:g}'.format(movement, position.get('x', 0), position.get('y', 0))
                self.propagate_change(command)
                if description_dict.get('done_event'):
                    description_dict['done_event'].set()

    @event.reaction('gcode_file', 'gcode_line', 'raw_command', 'current_mode', 'settings', 'state_')
    def property_changed(self, *events):
        for ev in events:
            if ev.type == 'settings':
                if ev.mutation == 'replace':
                    for key, value in ev.objects.items():
                        setattr(self.laser_driver, key, value)
                elif ev.mutation == 'set':
                    for key, value in ev.new_value.items():
                        setattr(self.laser_driver, key, value)
                self.state = self.state
                self.propagate_change('settings')
            elif ev.type == 'state_':
                self.propagate_change('state_')
                #self.update_info_label(ev.new_value)

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
        with ui.VBox():
            with ui.HSplit(flex=3) as self.hsplit:
                self.tab_panel = TabPanel(flex=2)
                self.plot_panel = PlotPanel(flex=1)
            self.control_panel = ControlPanel(flex=1)

    @event.reaction('hsplit.splitter_positions')
    def _splitter_changed(self, *events):
        self.propagate_change('splitter_positions')

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
        if (self.root.state_ == 'active' and old_v.title != new_v.title and new_v.title != 'Settings' and
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
                ui.Widget(flex=1)
                self.only_simulate_checkbox = ui.ToggleButton(flex=0, text='Simulate', title='simulate')
                self.live_view_checkbox = ui.ToggleButton(flex=0, text='Live view', title='live')

            self.info_label = ui.Label(flex=1, wrap=True, text='')

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

    @event.reaction('only_simulate_checkbox.checked', 'live_view_checkbox.checked')
    def _button_toggled(self, *events):
        if self.only_simulate_checkbox.checked:
            self.root.handle_setting_changed('simulation_mode', 2)
        elif self.live_view_checkbox.checked:
            self.root.handle_setting_changed('simulation_mode', 1)
        else:
            self.root.handle_setting_changed('simulation_mode', 0)

    @event.action
    def propagate_change(self, name_changed):
        if name_changed == 'state_':
            if self.root.settings.get('simulation_mode') < 2:
                new_properties = self.root.states.get(self.root.state_)
                if new_properties is not None:
                    for key, value in new_properties:
                        element, prop = key.split('.')
                        getattr(getattr(self, element), 'set_' + prop)(value)
            else:
                new_properties = self.root.simulation_states.get(self.root.state_)
                if new_properties is not None:
                    for key, value in new_properties:
                        element, prop = key.split('.')
                        getattr(getattr(self, element), 'set_' + prop)(value)
        elif name_changed == 'settings':
            if self.root.settings.get('simulation_mode') == 2:
                self.only_simulate_checkbox.set_checked(True)
            elif self.root.settings.get('simulation_mode') == 1:
                self.only_simulate_checkbox.set_checked(False)
                self.live_view_checkbox.set_checked(True)
            elif self.root.settings.get('simulation_mode') == 0:
                self.only_simulate_checkbox.set_checked(False)
                self.live_view_checkbox.set_checked(False)


class PlotPanel(ui.Widget):
    """
    This class contains the panel where the simulated plot is drawn
    """
    def init(self):
        with ui.VBox():
            with ui.HBox(flex=0):
                self.zoom_in_button = ui.Button(flex=0, text='+', title='zoom_in')
                self.zoom_label = ui.Label(flex=0, text='1x', title='zoom_label', style='min-width:40px;text-align:center;')
                self.zoom_out_button = ui.Button(flex=0, text='-', title='zoom_out')
                self.clear_button = ui.Button(flex=0, text='clear', title='clear')
                ui.Widget(flex=1)
            with ui.VSplit(flex=1) as self.vsplit:
                self.drawing = Drawing(flex=3)
                ui.Widget(flex=1)

        self.drawing.set_transform()

    @event.reaction('vsplit.splitter_positions')
    def _splitter_changed(self, *events):
        self.drawing.force_redraw()

    @event.action
    def propagate_change(self, name_changed):
        if name_changed.startswith('move cursor:'):
            pos_str = name_changed[12:]
            pos = pos_str.split()
            self.drawing.move_cursor((float(pos[0]), float(pos[1])))
        elif name_changed.startswith('line to:'):
            pos_str = name_changed[8:]
            pos = pos_str.split()
            self.drawing.draw_line((float(pos[0]), float(pos[1])))
        elif name_changed == 'state_':
            if self.root.state_ == 'active':
                self.drawing.start_drawing()
            else:
                self.drawing.stop_drawing()
        elif name_changed == 'splitter_positions':
            self.drawing.force_redraw()

    @event.reaction('zoom_in_button.mouse_click', 'zoom_out_button.mouse_click', 'clear_button.mouse_click')
    def _button_clicked(self, *events):
        for ev in events:
            if ev.source.title == 'zoom_in':
                self.drawing.zoom_in()
                text = str(self.drawing._zoom)
                if len(text) > 3:
                    text = text[:4]
                self.zoom_label.set_text(text+'x')
            elif ev.source.title == 'zoom_out':
                self.drawing.zoom_out()
                text = str(self.drawing._zoom)
                if len(text) > 3:
                    text = text[:4]
                self.zoom_label.set_text(text+'x')
            elif ev.source.title == 'clear':
                self.drawing.clear()

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

    @event.reaction('gcode_line.user_text')
    def _text_changed(self, *events):
        self.root.on_gcode_line_text_changed(self.gcode_line.user_text)

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
                self.raw_command = ui.LineEdit(flex=3, placeholder_text='e.g. XA1000')
            ui.HBox(flex=4)

    @event.reaction('raw_command.user_text')
    def _text_changed(self, *events):
        self.root.on_raw_text_changed(self.raw_command.user_text)

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
                    ui.Label(text='Burnin time in ms: ')
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
                    self.burnin_time_widget = ui.LineEdit(title='burnin_time')


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
            self.burnin_time_widget.set_text(str(self.root.settings.get('burnin_time', self.burnin_time_widget.text)))

class StreamToInfoLabel(object):
    def __init__(self, write_to_info_label_method):
        self.write_to_info_label_method = write_to_info_label_method

    def write(self, s):
        if callable(self.write_to_info_label_method) and s.strip():
            self.write_to_info_label_method(s)

    def flush(self):
        pass

class Drawing(ui.CanvasWidget):
    CSS = """
    .flx-Drawing {border: 3px solid gray;}
    .flx-Drawing:hover {cursor: all-scroll;}
    """
    def init(self):
        super().init()
        self.ctx = self.node.getContext('2d')
        self.canvas = self.ctx.canvas
        self._last_pos = (0, 0)
        self._last_cursor_pos = (0, 0)
        self._last_image_data = None
        self.strokeColor = 'black'
        self.cursorColor = 'red'
        self.strokeWidth = 1
        self.cursorSize = 2
        self.lineCap = 'round'
        self._zoom = 1
        self._position = (0, 0)
        self._mouse_down_position = None
        self._mouse_down_mouse_position = None
        self._line_paths = None
        self._cursor_paths = None
        self._do_drawing = False
        window.addEventListener('resize', self._on_resize)

    def _on_resize(self, *events):
        self.force_redraw()

    @event.reaction('mouse_move')
    def _on_mouse_move(self, *events):
        for ev in events:
            if 1 in ev.buttons:
                self.move(ev.pos[0] - self._mouse_down_mouse_position[0], ev.pos[1] - self._mouse_down_mouse_position[1])

    @event.reaction('mouse_down')
    def  _on_mouse_down(self, *events):
        ev = events[-1]
        self._mouse_down_position = self._position
        self._mouse_down_mouse_position = ev.pos

    @event.action
    def force_redraw(self):
        if not self._do_drawing:
            window.requestAnimationFrame(self.draw)

    def set_transform(self):
        self.ctx.setTransform(self._zoom, 0, 0, -self._zoom, self._position[0], self._position[1]+self.canvas.height)

    def draw_line(self, pos):
        last_pos = self._last_pos
        if self._line_paths is None:
            path = window.Path2D()
        else:
            path = window.Path2D(self._line_paths)
        path.moveTo(*pos)
        path.lineTo(*last_pos)
        self._line_paths = path
        self.move_cursor(pos)

    def move_cursor(self, pos):
        self._last_pos = pos
        self._last_cursor_pos = pos
        path = window.Path2D()
        path.rect(self._last_pos[0]-self.cursorSize, self._last_pos[1]-self.cursorSize,
                  2*self.cursorSize, 2*self.cursorSize)
        self._cursor_paths = path

    def draw(self):
        if self._do_drawing:
            window.requestAnimationFrame(self.draw)
        self.ctx.setTransform(1, 0, 0, 1, 0, 0)
        self.ctx.clearRect(0, 0, self.ctx.canvas.width, self.ctx.canvas.height)
        self.set_transform()
        self.ctx.lineWidth = self.strokeWidth
        self.ctx.lineCap = self.lineCap
        self.ctx.strokeStyle = self.strokeColor
        if self._line_paths:
            self.ctx.stroke(self._line_paths)
        self.ctx.fillStyle = self.cursorColor
        if self._cursor_paths:
            self.ctx.fill(self._cursor_paths)

    def stop_drawing(self):
        self._do_drawing = False

    def start_drawing(self):
        if not self._do_drawing:
            self._do_drawing = True
            window.requestAnimationFrame(self.draw)

    def zoom_in(self):
        if self._zoom <= 0.33:
            self._zoom += 0.33
        elif self._zoom <= 0.5:
            self._zoom += 0.5
        else:
            self._zoom += 1
        self.set_transform()
        self.strokeWidth = 1/self._zoom
        self.cursorSize = 2/self._zoom
        self.move_cursor(self._last_cursor_pos)
        if not self._do_drawing:
            window.requestAnimationFrame(self.draw)

    def zoom_out(self):
        if self._zoom > 1:
            self._zoom -= 1
        elif self._zoom > 0.5:
            self._zoom -= 0.5
        elif self._zoom > 0.33:
            self._zoom -= 0.33
        self.set_transform()
        #self.strokeWidth = 0.25 if self._zoom > 1 else 1
        self.strokeWidth = 1/self._zoom
        self.cursorSize = 2/self._zoom
        self.move_cursor(self._last_cursor_pos)
        if not self._do_drawing:
            window.requestAnimationFrame(self.draw)

    def clear(self):
        self._line_paths = []
        self._cursor_paths = []
        if not self._do_drawing:
            window.requestAnimationFrame(self.draw)

    def move(self, x, y):
        self._position = (self._mouse_down_position[0] + x, self._mouse_down_position[1] + y)
        self.set_transform()
        if not self._do_drawing:
            window.requestAnimationFrame(self.draw)

#config.hostname = 'localhost'
#config.port = 80

a = app.App(AppRoot)
#a.serve()
#app.start()
#a.export(filename='C:/Users/Andi/Downloads/AppRoot.html')
a.launch()
app.run()
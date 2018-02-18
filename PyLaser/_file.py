# -*- coding: utf-8 -*-
"""
Created on Sun Feb 18 13:13:19 2018

@author: Andi
"""

from flexx import event
from flexx.ui import Widget
from flexx.pyscript import window


class OpenFileWidget(Widget):
    """ A widget used to select file.
    """
    
    file = event.AnyProp(settable=True, doc="""
                         The currently selected file.
                         """)
    
    def _create_dom(self):
        node = window.document.createElement('input')
        node.type = 'file'
        self._addEventListener(node, 'change', self._selected_file_changed, 0)
        return node
    
    def _selected_file_changed(self, e):
        if len(self.node.files) > 0:
            self.set_file(self.node.files[0])
            
#    @event.reaction('file')
#    def _file_changed(self):
#        self._print_content_to_console()
#            
#    @event.action
#    def _print_content_to_console(self):
#        def _print(event):
#            print(event.target.result)
#        
#        if self.file is not None:
#            reader = window.FileReader()
#            reader.onload = _print
#            reader.readAsText(self.file)
#            print(self.file)
        
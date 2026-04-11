"""
Aurexis Core — Import Diagnostic v2
Tests ScreenManager and all M11 imports one by one.
"""

import os
os.environ['KIVY_LOG_LEVEL'] = 'info'

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window

results = []

def try_import(desc, fn):
    try:
        fn()
        results.append(f'[color=00ff00]PASS[/color]  {desc}')
    except Exception as e:
        results.append(f'[color=ff0000]FAIL[/color]  {desc}: {e}')

# Kivy core
try_import('kivy.uix.button', lambda: __import__('kivy.uix.button'))
try_import('kivy.uix.image', lambda: __import__('kivy.uix.image'))
try_import('kivy.uix.scrollview', lambda: __import__('kivy.uix.scrollview'))
try_import('kivy.clock', lambda: __import__('kivy.clock'))

# ScreenManager (the new addition)
try_import('kivy.uix.screenmanager (import)', lambda: __import__('kivy.uix.screenmanager'))

def test_sm_classes():
    from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
    sm = ScreenManager(transition=NoTransition())
    s = Screen(name='test')
    sm.add_widget(s)
try_import('ScreenManager + Screen + NoTransition (create)', test_sm_classes)

# numpy
try_import('numpy', lambda: __import__('numpy'))

# Path setup for aurexis_lang
import sys
from pathlib import Path
_HERE = Path(__file__).resolve().parent
_SRC = _HERE / 'aurexis_lang' / 'src'
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
    results.append(f'[color=00ff00]PATH[/color]  Added {_SRC}')
else:
    results.append(f'[color=ffff00]PATH[/color]  aurexis_lang/src: exists={_SRC.is_dir()}')

# mobile_pipeline
try_import('mobile_pipeline', lambda: __import__('mobile_pipeline'))

# visual_gui
try_import('visual_gui', lambda: __import__('visual_gui'))

# debugger
try_import('debugger', lambda: __import__('debugger'))

# Widget creation tests
def test_visual_widgets():
    from visual_gui import IRTreeWidget, EvidenceInspector, PromotionTracker
    w1 = IRTreeWidget()
    w2 = EvidenceInspector()
    w3 = PromotionTracker()
try_import('visual_gui widgets (create)', test_visual_widgets)

def test_debugger_widget():
    from debugger import DebuggerWidget
    w = DebuggerWidget()
try_import('DebuggerWidget (create)', test_debugger_widget)


class DiagApp(App):
    title = 'Aurexis Diag v2'

    def build(self):
        root = BoxLayout(orientation='vertical')
        scroll = ScrollView()
        lbl = Label(
            text='\n'.join(results),
            font_size='14sp',
            markup=True,
            size_hint_y=None,
            text_size=(Window.width - 20, None),
            halign='left', valign='top',
        )
        lbl.bind(texture_size=lbl.setter('size'))
        scroll.add_widget(lbl)
        root.add_widget(scroll)
        return root


if __name__ == '__main__':
    DiagApp().run()

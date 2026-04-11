"""
Aurexis Core — UI Build Diagnostic v3
Builds the full M11 UI step by step, reports which step crashes.
"""

import os
import traceback
os.environ['KIVY_LOG_LEVEL'] = 'info'

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image as KivyImage
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform

import numpy as np
from mobile_pipeline import MobilePipeline, MobileFrameProcessor, kivy_texture_to_bgr
from visual_gui import PhoxelOverlay, IRTreeWidget, EvidenceInspector, PromotionTracker
from debugger import DebuggerWidget

results = []

def step(desc, fn):
    try:
        fn()
        results.append(f'[color=00ff00]OK[/color]    {desc}')
        return True
    except Exception as e:
        results.append(f'[color=ff0000]FAIL[/color]  {desc}')
        results.append(f'        {e}')
        tb = traceback.format_exc().split('\n')
        for line in tb[-4:]:
            if line.strip():
                results.append(f'        {line.strip()}')
        return False


class DiagApp(App):
    title = 'Aurexis Diag v3'

    def build(self):
        # We'll try building the full UI piece by piece
        self._pieces = {}

        step('BoxLayout root', lambda: self._pieces.update(
            root=BoxLayout(orientation='vertical', spacing=0)))

        step('ScreenManager', lambda: self._pieces.update(
            sm=ScreenManager(transition=NoTransition(), size_hint=(1, 0.82))))

        # Screen 1: Live
        def make_live():
            s = Screen(name='live')
            box = BoxLayout(orientation='vertical', spacing=4, padding=4)
            img = KivyImage(size_hint=(1, 0.5), allow_stretch=True, keep_ratio=True)
            box.add_widget(img)
            scroll = ScrollView(size_hint=(1, 0.5))
            lbl = Label(
                text='Test log',
                font_size='12sp',
                size_hint_y=None,
                text_size=(Window.width - 20, None),
                halign='left', valign='top',
                markup=True,
                color=(0.9, 0.95, 1.0, 1),
            )
            lbl.bind(texture_size=lbl.setter('size'))
            scroll.add_widget(lbl)
            box.add_widget(scroll)
            s.add_widget(box)
            self._pieces['s_live'] = s
        step('Screen: Live Feed', make_live)

        # Screen 2: IR Tree
        def make_ir():
            s = Screen(name='ir')
            w = IRTreeWidget(size_hint=(1, 1))
            s.add_widget(w)
            self._pieces['s_ir'] = s
        step('Screen: IR Tree', make_ir)

        # Screen 3: Evidence
        def make_ev():
            s = Screen(name='evidence')
            w = EvidenceInspector(size_hint=(1, 1))
            s.add_widget(w)
            self._pieces['s_ev'] = s
        step('Screen: Evidence', make_ev)

        # Screen 4: Promotions
        def make_promo():
            s = Screen(name='promos')
            w = PromotionTracker(size_hint=(1, 1))
            s.add_widget(w)
            self._pieces['s_promo'] = s
        step('Screen: Promotions', make_promo)

        # Screen 5: Debugger
        def make_debug():
            s = Screen(name='debug')
            w = DebuggerWidget(size_hint=(1, 1))
            s.add_widget(w)
            self._pieces['s_debug'] = s
        step('Screen: Debugger', make_debug)

        # Add screens to SM
        def add_screens():
            sm = self._pieces['sm']
            for key in ['s_live', 's_ir', 's_ev', 's_promo', 's_debug']:
                if key in self._pieces:
                    sm.add_widget(self._pieces[key])
        step('Add all screens to SM', add_screens)

        # Add SM to root
        def attach_sm():
            self._pieces['root'].add_widget(self._pieces['sm'])
        step('Attach SM to root', attach_sm)

        # Control bar
        def make_ctrl():
            bar = BoxLayout(size_hint=(1, 0.06), spacing=6, padding=(6, 2))
            bar.add_widget(Button(text='START', font_size='15sp'))
            bar.add_widget(Button(text='STOP', font_size='15sp'))
            bar.add_widget(Label(text='Ready', font_size='14sp', size_hint_x=0.4))
            self._pieces['root'].add_widget(bar)
        step('Control bar (START/STOP)', make_ctrl)

        # Bottom nav
        def make_nav():
            nav = BoxLayout(size_hint=(1, 0.07), spacing=2, padding=(2, 2))
            for label in ['Live', 'IR Tree', 'Evidence', 'Promos', 'Debug']:
                btn = Button(text=label, font_size='13sp',
                             background_color=(0.25, 0.25, 0.35, 1))
                nav.add_widget(btn)
            self._pieces['root'].add_widget(nav)
        step('Bottom navigation bar', make_nav)

        # Footer
        def make_footer():
            f = Label(text='M11 Diag', font_size='12sp', markup=True,
                      size_hint=(1, 0.05), color=(0.4, 0.4, 0.4, 1))
            self._pieces['root'].add_widget(f)
        step('Footer label', make_footer)

        # Permission request
        def make_perms():
            if platform == 'android':
                def req(dt):
                    try:
                        from android.permissions import request_permissions, Permission
                        request_permissions(
                            [Permission.CAMERA, Permission.WRITE_EXTERNAL_STORAGE,
                             Permission.READ_EXTERNAL_STORAGE],
                            lambda p, g: None,
                        )
                    except Exception:
                        pass
                Clock.schedule_once(req, 0.5)
        step('Deferred permission request', make_perms)

        # Show results
        results.append('')
        passed = sum(1 for r in results if '[color=00ff00]' in r)
        total_steps = sum(1 for r in results if 'OK' in r or 'FAIL' in r)
        results.append(f'{passed}/{total_steps} steps passed')

        # If all passed, return the actual built root
        if all('[color=ff0000]' not in r for r in results):
            results.append('[color=00ff00]ALL PASSED — returning full UI[/color]')
            # Overlay results on the live screen for 5 seconds
            return self._pieces.get('root', self._fallback())
        else:
            return self._fallback()

    def _fallback(self):
        root = BoxLayout(orientation='vertical')
        scroll = ScrollView()
        lbl = Label(
            text='\n'.join(results),
            font_size='13sp',
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

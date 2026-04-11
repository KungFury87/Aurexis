"""
Aurexis Core — M11 Visual Programming GUI + Debugger

5-screen mobile app with bottom navigation:
  1. Live Feed:    Camera with phoxel overlay
  2. IR Tree:      Program structure with execution status colors
  3. Evidence:     Tap frames to inspect evidence chains
  4. Promotions:   Status ladder dashboard
  5. Debugger:     Step-through IR debugger with breakpoints

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import os
import sys
import time
from pathlib import Path

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


# ────────────────────────────────────────────────────────────
TARGET_FPS = 1.0
DEFAULT_DURATION = 30.0
MAX_LOG_LINES = 50


# ────────────────────────────────────────────────────────────
class AurexisApp(App):

    title = 'Aurexis Core'

    def build(self):
        self.pipeline = None
        self._running = False
        self._schedule = None
        self._start_time = 0
        self._log_lines = []
        self._camera = None
        self._permissions_granted = False

        root = BoxLayout(orientation='vertical', spacing=0)

        # ── Screen manager (replaces TabbedPanel) ──
        self.sm = ScreenManager(
            transition=NoTransition(),
            size_hint=(1, 0.82),
        )

        # Screen 1: Live Feed
        s_live = Screen(name='live')
        self.live_box = BoxLayout(orientation='vertical', spacing=4, padding=4)
        self.annotated_image = KivyImage(
            size_hint=(1, 0.5),
            allow_stretch=True,
            keep_ratio=True,
        )
        self.live_box.add_widget(self.annotated_image)
        live_scroll = ScrollView(size_hint=(1, 0.5))
        self.live_log = Label(
            text='Aurexis Core M11\nTap START to begin.\n',
            font_size='12sp',
            size_hint_y=None,
            text_size=(Window.width - 20, None),
            halign='left', valign='top',
            markup=True,
            color=(0.9, 0.95, 1.0, 1),
        )
        self.live_log.bind(texture_size=self.live_log.setter('size'))
        live_scroll.add_widget(self.live_log)
        self.live_box.add_widget(live_scroll)
        s_live.add_widget(self.live_box)
        self.sm.add_widget(s_live)

        # Screen 2: IR Tree
        s_ir = Screen(name='ir')
        self.ir_tree = IRTreeWidget(size_hint=(1, 1))
        s_ir.add_widget(self.ir_tree)
        self.sm.add_widget(s_ir)

        # Screen 3: Evidence
        s_ev = Screen(name='evidence')
        self.evidence = EvidenceInspector(size_hint=(1, 1))
        s_ev.add_widget(self.evidence)
        self.sm.add_widget(s_ev)

        # Screen 4: Promotions
        s_promo = Screen(name='promos')
        self.promotions = PromotionTracker(size_hint=(1, 1))
        s_promo.add_widget(self.promotions)
        self.sm.add_widget(s_promo)

        # Screen 5: Debugger
        s_debug = Screen(name='debug')
        self.debugger_widget = DebuggerWidget(size_hint=(1, 1))
        s_debug.add_widget(self.debugger_widget)
        self.sm.add_widget(s_debug)

        root.add_widget(self.sm)

        # ── START / STOP bar ──
        ctrl_bar = BoxLayout(size_hint=(1, 0.06), spacing=6, padding=(6, 2))

        self.btn_start = Button(
            text='START', font_size='15sp',
            background_color=(0.15, 0.6, 0.15, 1),
            on_press=self._start_pipeline,
        )
        self.btn_stop = Button(
            text='STOP', font_size='15sp',
            background_color=(0.6, 0.15, 0.15, 1),
            disabled=True,
            on_press=self._stop_pipeline,
        )
        self.lbl_status = Label(
            text='Ready', font_size='14sp',
            size_hint_x=0.4,
            color=(0.7, 0.7, 0.7, 1),
        )

        ctrl_bar.add_widget(self.btn_start)
        ctrl_bar.add_widget(self.btn_stop)
        ctrl_bar.add_widget(self.lbl_status)
        root.add_widget(ctrl_bar)

        # ── Bottom navigation (big tappable buttons) ──
        nav = BoxLayout(size_hint=(1, 0.07), spacing=2, padding=(2, 2))
        self._nav_buttons = {}

        tabs = [
            ('Live', 'live'),
            ('IR Tree', 'ir'),
            ('Evidence', 'evidence'),
            ('Promos', 'promos'),
            ('Debug', 'debug'),
        ]
        for label, name in tabs:
            btn = Button(
                text=label,
                font_size='13sp',
                background_color=(0.25, 0.25, 0.35, 1),
            )
            btn.screen_name = name
            btn.bind(on_press=self._switch_screen)
            nav.add_widget(btn)
            self._nav_buttons[name] = btn

        # Highlight initial tab
        self._nav_buttons['live'].background_color = (0.1, 0.4, 0.7, 1)
        root.add_widget(nav)

        # ── Footer ──
        self.footer = Label(
            text='M11 — Debugger & Inspector',
            font_size='12sp', markup=True,
            size_hint=(1, 0.05),
            color=(0.4, 0.4, 0.4, 1),
        )
        root.add_widget(self.footer)

        # ── Request permissions (deferred) ──
        if platform == 'android':
            Clock.schedule_once(self._request_permissions, 0.5)
        else:
            self._permissions_granted = True

        return root

    # ── Permissions (deferred to avoid crash) ─────────────

    def _request_permissions(self, dt):
        """Request Android permissions after the UI is built."""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions(
                [Permission.CAMERA, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE],
                self._on_permissions_result,
            )
        except Exception:
            self._permissions_granted = True

    def _on_permissions_result(self, permissions, grants):
        """Called when permission dialog is answered."""
        self._permissions_granted = True

    # ── Navigation ────────────────────────────────────────

    def _switch_screen(self, btn):
        name = btn.screen_name
        self.sm.current = name
        # Update button colors
        for n, b in self._nav_buttons.items():
            if n == name:
                b.background_color = (0.1, 0.4, 0.7, 1)
            else:
                b.background_color = (0.25, 0.25, 0.35, 1)

    # ── Logging ───────────────────────────────────────────

    def log(self, msg):
        self._log_lines.append(msg)
        if len(self._log_lines) > MAX_LOG_LINES:
            self._log_lines = self._log_lines[-MAX_LOG_LINES:]
        self.live_log.text = '\n'.join(self._log_lines)

    # ── Start / Stop ──────────────────────────────────────

    def _start_pipeline(self, *args):
        if self._running:
            return

        if platform == 'android':
            out_dir = os.path.join(self.user_data_dir, 'm11_run')
        else:
            out_dir = str(Path.home() / 'AurexisCore' / 'm11_run')

        try:
            self.pipeline = MobilePipeline(output_dir=out_dir)
            self.pipeline.start()
        except Exception as e:
            self.log(f'[ERROR] Pipeline init: {e}')
            return

        self._running = True
        self._start_time = time.time()

        # Create camera on demand (avoids permission crash)
        if self._camera is None:
            from kivy.uix.camera import Camera
            self._camera = Camera(
                index=0, resolution=(640, 480),
                play=False, size_hint=(0, 0), opacity=0,
            )
            self.live_box.add_widget(self._camera)

        self._camera.play = True
        self.btn_start.disabled = True
        self.btn_stop.disabled = False
        self.lbl_status.text = 'Running...'
        self.lbl_status.color = (0.2, 1.0, 0.2, 1)

        self.log('Pipeline started.')
        self.log(f'Duration: {DEFAULT_DURATION}s at {TARGET_FPS} FPS')
        self.log('')

        self._schedule = Clock.schedule_interval(
            self._grab_and_process,
            1.0 / TARGET_FPS,
        )

    def _stop_pipeline(self, *args):
        if not self._running:
            return

        self._running = False
        if self._schedule:
            self._schedule.cancel()
            self._schedule = None

        if self._camera:
            self._camera.play = False

        self.btn_start.disabled = False
        self.btn_stop.disabled = True
        self.lbl_status.text = 'Stopped'
        self.lbl_status.color = (1.0, 0.5, 0.2, 1)

        self._show_report()

    # ── Frame processing ──────────────────────────────────

    def _grab_and_process(self, dt):
        if not self._running or self._camera is None:
            return

        elapsed = time.time() - self._start_time
        if elapsed >= DEFAULT_DURATION:
            self._stop_pipeline()
            return

        texture = self._camera.texture
        if texture is None:
            return

        frame = kivy_texture_to_bgr(texture)
        if frame is None:
            return

        try:
            result = self.pipeline.process_frame(frame)

            # Tab 1: Annotated live feed
            extractor = self.pipeline.processor.extractor
            extraction = extractor.extract_robust_primitives(frame)
            annotated = PhoxelOverlay.annotate_frame(
                frame, extraction,
                show_labels=True, show_confidence=True,
            )
            tex = PhoxelOverlay.frame_to_texture(annotated)
            self.annotated_image.texture = tex

            # Tab 2: IR Tree
            ir_root = result.get('_ir_root')
            opt_report = result.get('_opt_report')
            if ir_root is not None:
                self.ir_tree.update_tree(ir_root, opt_report)

            # Tab 3: Evidence
            self.evidence.update_frames(self.pipeline.results)

            # Tab 4: Promotions
            self.promotions.update(self.pipeline.results)

            # Tab 5: Debugger
            if ir_root is not None:
                self.debugger_widget.load_tree(ir_root, opt_report)

            # Live log
            self._display_result(result, elapsed)

        except Exception as e:
            self.log(f'[ERROR] {e}')

    def _display_result(self, result, elapsed):
        status = result['best_status']
        if status == 'EXECUTABLE':
            s = f'[color=00ff00]{status}[/color]'
        elif status == 'VALIDATED':
            s = f'[color=ffff00]{status}[/color]'
        else:
            s = f'[color=888888]{status}[/color]'

        law = '[color=00ff00]OK[/color]' if result['law_passed'] else '[color=ff0000]FAIL[/color]'

        self.log(
            f'[{elapsed:5.1f}s] #{result["frame_index"]:3d}  '
            f'p={result["primitives"]:3d}  c={result["mean_confidence"]:.3f}  '
            f'{law}  {s}  {result["processing_time_seconds"]:.2f}s'
        )
        self.lbl_status.text = f'{len(self.pipeline.results)} frames'

    # ── Report ────────────────────────────────────────────

    def _show_report(self):
        if self.pipeline is None or not self.pipeline.results:
            self.footer.text = 'No frames processed'
            return

        report = self.pipeline.get_report()

        self.log('')
        self.log('=' * 40)
        self.log('  M11 AUDIT REPORT')
        self.log('=' * 40)
        self.log(f'  Frames: {report["frames_processed"]}  FPS: {report["effective_fps"]:.2f}')
        p = report.get('primitives', {})
        c = report.get('confidence', {})
        t = report.get('processing_time', {})
        self.log(f'  Prims: {p.get("mean", 0):.1f}/frame  Conf: {c.get("mean", 0):.4f}')
        self.log(f'  Time: {t.get("mean", 0):.3f}s/frame (max {t.get("max", 0):.3f}s)')
        self.log(f'  Law: {report["law_compliance"]:.0%}  EXEC: {report["executable_frames"]} frames')
        self.log('')

        dbg_loaded = self.debugger_widget.debugger.total_nodes > 0
        m11_checks = {
            'phoxel_overlay': self.annotated_image.texture is not None,
            'ir_tree_rendered': 'PROGRAM' in (self.ir_tree.label.text or ''),
            'evidence_inspector': len(self.pipeline.results) > 0,
            'promotion_tracker': 'EXECUTABLE' in (self.promotions.label.text or ''),
            'debugger_loaded': dbg_loaded,
            'frames_processed': report['frames_processed'] >= 1,
            'executable_reached': report.get('executable_reached', False),
            'within_tech_floor': report.get('all_within_tech_floor', False),
        }

        passed = sum(1 for v in m11_checks.values() if v)
        total = len(m11_checks)

        for name, ok in m11_checks.items():
            icon = '[color=00ff00]PASS[/color]' if ok else '[color=ff0000]FAIL[/color]'
            self.log(f'  {icon}  {name}')

        self.log('')
        if all(m11_checks.values()):
            self.log('[color=00ff00]  M11 COMPLETE — Debugger & Inspector[/color]')
            self.footer.text = f'[color=00ff00]M11 COMPLETE  {passed}/{total}[/color]'
        else:
            failed = [k for k, v in m11_checks.items() if not v]
            self.log(f'  M11 incomplete: {", ".join(failed)}')
            self.footer.text = f'M11: {passed}/{total}'

        try:
            self.pipeline.save_report()
        except Exception:
            pass


# ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    AurexisApp().run()

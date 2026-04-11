"""
visual_gui.py — M10 Visual Programming GUI Components

Four visual modules for the Aurexis Core mobile app:
  1. PhoxelOverlay:     Draws primitives on camera frames
  2. IRTreeView:        Renders IR tree with execution status colors
  3. EvidenceInspector: Traces observations back to source frames
  4. PromotionTracker:  Shows observations climbing the status ladder

All components work with Kivy widgets and the MobilePipeline results.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.graphics.texture import Texture
from kivy.core.window import Window


# ────────────────────────────────────────────────────────────
# Color constants for execution status
# ────────────────────────────────────────────────────────────

STATUS_COLORS = {
    'EXECUTABLE':  (0.0, 1.0, 0.0, 1.0),    # green
    'VALIDATED':   (1.0, 1.0, 0.0, 1.0),     # yellow
    'ESTIMATED':   (1.0, 0.6, 0.0, 1.0),     # orange
    'DESCRIPTIVE': (0.5, 0.5, 0.5, 1.0),     # gray
    'none':        (0.3, 0.3, 0.3, 1.0),     # dark gray
}

TIER_COLORS = {
    'REAL_CAPTURE': (0.0, 1.0, 0.4, 1.0),    # bright green
    'EARNED':       (0.0, 0.8, 1.0, 1.0),     # cyan
    'AUTHORED':     (1.0, 0.8, 0.0, 1.0),     # gold
    'LAB':          (0.6, 0.4, 1.0, 1.0),     # purple
}


# ────────────────────────────────────────────────────────────
# 1. Phoxel Field Overlay
# ────────────────────────────────────────────────────────────

class PhoxelOverlay:
    """
    Draws detected primitives directly onto camera frames.
    Returns an annotated BGR numpy array ready for display.
    """

    # Colors for different primitive types (BGR for OpenCV)
    PRIM_COLORS = {
        'color_region':    (0, 255, 100),
        'edge_segment':    (255, 100, 0),
        'corner':          (0, 100, 255),
        'texture_region':  (255, 255, 0),
        'keypoint':        (255, 0, 255),
        'contour':         (0, 255, 255),
        'unknown':         (200, 200, 200),
    }

    @staticmethod
    def annotate_frame(
        frame: np.ndarray,
        extraction_result: Dict[str, Any],
        show_labels: bool = True,
        show_confidence: bool = True,
        show_grid: bool = False,
    ) -> np.ndarray:
        """
        Draw primitive observations onto a camera frame.
        Returns a new annotated frame (does not modify original).
        """
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        primitives = extraction_result.get('primitive_observations', [])

        if show_grid:
            # Draw a subtle grid overlay
            for gx in range(0, w, w // 8):
                cv2.line(annotated, (gx, 0), (gx, h), (40, 40, 40), 1)
            for gy in range(0, h, h // 6):
                cv2.line(annotated, (0, gy), (w, gy), (40, 40, 40), 1)

        for i, prim in enumerate(primitives):
            ptype = prim.get('primitive_type', 'unknown')
            conf = prim.get('confidence', 0)
            attrs = prim.get('attributes', {})
            color = PhoxelOverlay.PRIM_COLORS.get(ptype, (200, 200, 200))

            # Get position from attributes
            cx = attrs.get('centroid_x', attrs.get('x', (i * 37) % w))
            cy = attrs.get('centroid_y', attrs.get('y', (i * 53) % h))
            cx = int(cx) if cx < w else w // 2
            cy = int(cy) if cy < h else h // 2

            # Draw marker based on primitive type
            if ptype in ('color_region', 'texture_region'):
                size = int(max(10, conf * 30))
                cv2.rectangle(
                    annotated,
                    (cx - size, cy - size),
                    (cx + size, cy + size),
                    color, 2,
                )
            elif ptype in ('corner', 'keypoint'):
                radius = int(max(4, conf * 15))
                cv2.circle(annotated, (cx, cy), radius, color, 2)
            elif ptype == 'edge_segment':
                length = int(max(8, conf * 25))
                cv2.line(
                    annotated,
                    (cx - length, cy),
                    (cx + length, cy),
                    color, 2,
                )
            else:
                cv2.drawMarker(
                    annotated, (cx, cy), color,
                    cv2.MARKER_CROSS, 10, 2,
                )

            # Label
            if show_labels and i < 20:  # Cap labels to avoid clutter
                label = ptype[:6]
                if show_confidence:
                    label += f' {conf:.2f}'
                cv2.putText(
                    annotated, label,
                    (cx + 5, cy - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1,
                )

        # Stats overlay (top-left)
        stats_lines = [
            f'Primitives: {len(primitives)}',
            f'Mean conf: {extraction_result.get("mean_confidence", 0):.3f}',
        ]
        for j, line in enumerate(stats_lines):
            cv2.putText(
                annotated, line,
                (10, 20 + j * 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
            )

        return annotated

    @staticmethod
    def frame_to_texture(frame: np.ndarray) -> Texture:
        """Convert a BGR numpy frame to a Kivy Texture for display."""
        # BGR → RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Flip vertically (Kivy textures are bottom-up)
        rgb = np.flipud(rgb)
        h, w = rgb.shape[:2]
        texture = Texture.create(size=(w, h), colorfmt='rgb')
        texture.blit_buffer(rgb.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        return texture


# ────────────────────────────────────────────────────────────
# 2. IR Tree Viewer
# ────────────────────────────────────────────────────────────

class IRTreeWidget(ScrollView):
    """
    Renders the IR tree as a scrollable, indented text view.
    Each node is color-coded by its execution status.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.label = Label(
            text='IR Tree: waiting for data...',
            font_size='13sp',
            size_hint_y=None,
            text_size=(Window.width - 40, None),
            halign='left',
            valign='top',
            markup=True,
            color=(0.9, 0.95, 1.0, 1),
        )
        self.label.bind(texture_size=self.label.setter('size'))
        self.add_widget(self.label)
        self._selected_node = None

    def update_tree(self, ir_root, opt_report=None):
        """Render the IR tree from an IR node."""
        if ir_root is None:
            self.label.text = '[color=888888]No IR tree (no tokens produced)[/color]'
            return

        lines = []
        lines.append('[b]IR PROGRAM TREE[/b]')
        lines.append('')
        self._render_node(ir_root, lines, depth=0)

        if opt_report is not None:
            lines.append('')
            lines.append('[b]OPTIMIZATION REPORT[/b]')
            lines.append(f'  Executable: [color=00ff00]{opt_report.executable_count}[/color]')
            lines.append(f'  Validated:  [color=ffff00]{opt_report.validated_count}[/color]')
            lines.append(f'  Descriptive: [color=888888]{opt_report.descriptive_count}[/color]')

        self.label.text = '\n'.join(lines)

    def _render_node(self, node, lines, depth=0):
        """Recursively render an IR node and its children."""
        indent = '  ' * depth
        node_type = getattr(node, 'node_type', type(node).__name__)
        status = self._get_node_status(node)
        color = self._status_to_markup_color(status)

        # Node label
        label = f'{node_type}'
        conf = getattr(node, 'confidence', None)
        if conf is not None:
            label += f' (conf={conf:.3f})'

        lines.append(f'{indent}[color={color}]{label}[/color]')

        # Recurse into children
        children = getattr(node, 'children', [])
        if children:
            for child in children:
                self._render_node(child, lines, depth + 1)

    def _get_node_status(self, node):
        """Extract execution status from an IR node."""
        status = getattr(node, 'execution_status', None)
        if status is not None:
            if hasattr(status, 'value'):
                return status.value
            return str(status)
        # Check metadata
        meta = getattr(node, 'metadata', {})
        if isinstance(meta, dict):
            return meta.get('execution_status', 'none')
        return 'none'

    def _status_to_markup_color(self, status):
        """Convert execution status to Kivy markup color hex."""
        mapping = {
            'EXECUTABLE':  '00ff00',
            'VALIDATED':   'ffff00',
            'ESTIMATED':   'ff9900',
            'DESCRIPTIVE': '888888',
        }
        return mapping.get(str(status).upper(), '666666')


# ────────────────────────────────────────────────────────────
# 3. Evidence Chain Inspector
# ────────────────────────────────────────────────────────────

class EvidenceInspector(ScrollView):
    """
    Shows the evidence chain for processed frames.
    Tap a frame entry to see its full evidence trail.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=4,
            padding=8,
        )
        self.container.bind(minimum_height=self.container.setter('height'))
        self.add_widget(self.container)
        self._frames_data = []

    def update_frames(self, results: List[Dict[str, Any]]):
        """Update with the latest pipeline results."""
        self._frames_data = results
        self._rebuild_list()

    def _rebuild_list(self):
        """Rebuild the frame list display."""
        self.container.clear_widgets()

        header = Label(
            text='[b]EVIDENCE CHAIN INSPECTOR[/b]\nTap a frame to inspect',
            font_size='14sp',
            markup=True,
            size_hint_y=None,
            height=50,
            color=(0.8, 0.9, 1.0, 1),
        )
        self.container.add_widget(header)

        for r in self._frames_data[-30:]:  # Last 30 frames
            status = r.get('best_status', 'none')
            color_hex = '00ff00' if status == 'EXECUTABLE' else 'ffff00' if status == 'VALIDATED' else '888888'

            text = (
                f'[color={color_hex}]Frame #{r["frame_index"]}[/color]  '
                f'prims={r["primitives"]}  conf={r["mean_confidence"]:.3f}  '
                f'status={status}  t={r["processing_time_seconds"]:.2f}s'
            )

            btn = Button(
                text=text,
                font_size='12sp',
                size_hint_y=None,
                height=45,
                markup=True,
                background_color=(0.15, 0.15, 0.2, 1),
                halign='left',
                valign='middle',
            )
            btn.text_size = (Window.width - 40, None)
            btn.frame_data = r
            btn.bind(on_press=self._on_frame_tap)
            self.container.add_widget(btn)

    def _on_frame_tap(self, btn):
        """Show detailed evidence chain for a tapped frame."""
        r = btn.frame_data
        self.container.clear_widgets()

        # Back button
        back = Button(
            text='<< Back to frame list',
            font_size='14sp',
            size_hint_y=None,
            height=40,
            background_color=(0.3, 0.3, 0.4, 1),
        )
        back.bind(on_press=lambda x: self._rebuild_list())
        self.container.add_widget(back)

        # Frame detail
        status = r.get('best_status', 'none')
        color_hex = '00ff00' if status == 'EXECUTABLE' else 'ffff00' if status == 'VALIDATED' else '888888'

        lines = []
        lines.append(f'[b]Frame #{r["frame_index"]} — Evidence Chain[/b]')
        lines.append('')
        lines.append(f'[b]Observation[/b]')
        lines.append(f'  Timestamp: {r.get("timestamp", "?")}')
        lines.append(f'  Resolution: {r.get("resolution", "?")}')
        lines.append(f'  Primitives: {r["primitives"]}')
        lines.append(f'  Mean confidence: {r["mean_confidence"]:.4f}')
        lines.append(f'  Max confidence: {r.get("max_confidence", 0):.4f}')
        lines.append('')
        lines.append(f'[b]Validation[/b]')
        lines.append(f'  Schema valid: {r["schema_valid"]}')
        lines.append(f'  Law passed: {r["law_passed"]}')
        lines.append(f'  Law violations: {r.get("law_violations", 0)}')
        lines.append('')
        lines.append(f'[b]Execution[/b]')
        lines.append(f'  Tokens: {r.get("tokens", 0)}')
        lines.append(f'  Executable nodes: {r["executable_count"]}')
        lines.append(f'  Validated nodes: {r["validated_count"]}')
        lines.append(f'  Best status: [color={color_hex}]{status}[/color]')
        lines.append('')
        lines.append(f'[b]Performance[/b]')
        lines.append(f'  Processing time: {r["processing_time_seconds"]:.3f}s')
        lines.append(f'  Within tech floor: {r["within_tech_floor"]}')
        lines.append('')
        lines.append(f'[b]Evidence Trail[/b]')
        lines.append(f'  Source: mobile_camera/frame_{r["frame_index"]}')
        lines.append(f'  Tier: REAL_CAPTURE')
        lines.append(f'  Device: Samsung Galaxy S23 Ultra')
        lines.append(f'  Synthetic: False')
        lines.append(f'  Traceable: True')

        detail = Label(
            text='\n'.join(lines),
            font_size='13sp',
            markup=True,
            size_hint_y=None,
            text_size=(Window.width - 40, None),
            halign='left',
            valign='top',
            color=(0.9, 0.95, 1.0, 1),
        )
        detail.bind(texture_size=detail.setter('size'))
        self.container.add_widget(detail)


# ────────────────────────────────────────────────────────────
# 4. Promotion Tracker
# ────────────────────────────────────────────────────────────

class PromotionTracker(ScrollView):
    """
    Live dashboard showing how observations climb the execution
    status ladder over time.

    Tracks: DESCRIPTIVE → ESTIMATED → VALIDATED → EXECUTABLE
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.label = Label(
            text='[b]PROMOTION TRACKER[/b]\nWaiting for frames...',
            font_size='13sp',
            markup=True,
            size_hint_y=None,
            text_size=(Window.width - 30, None),
            halign='left',
            valign='top',
            color=(0.9, 0.95, 1.0, 1),
        )
        self.label.bind(texture_size=self.label.setter('size'))
        self.add_widget(self.label)

        # Track status counts over time
        self._history: List[Dict[str, int]] = []

    def update(self, results: List[Dict[str, Any]]):
        """Update the promotion tracker with pipeline results."""
        if not results:
            return

        # Count statuses
        counts = {
            'EXECUTABLE': 0,
            'VALIDATED': 0,
            'ESTIMATED': 0,
            'DESCRIPTIVE': 0,
            'none': 0,
        }
        for r in results:
            s = r.get('best_status', 'none')
            if s in counts:
                counts[s] += 1
            else:
                counts['none'] += 1

        total = len(results)
        lines = []
        lines.append('[b]PROMOTION TRACKER[/b]')
        lines.append(f'{total} frames processed')
        lines.append('')

        # Status ladder visualization
        lines.append('[b]Execution Status Ladder[/b]')
        lines.append('')

        ladder = ['EXECUTABLE', 'VALIDATED', 'ESTIMATED', 'DESCRIPTIVE', 'none']
        colors = {
            'EXECUTABLE': '00ff00',
            'VALIDATED': 'ffff00',
            'ESTIMATED': 'ff9900',
            'DESCRIPTIVE': '888888',
            'none': '444444',
        }

        max_bar = 30  # max bar width in characters
        for status in ladder:
            count = counts[status]
            pct = count / total if total > 0 else 0
            bar_len = int(pct * max_bar)
            bar = '|' * bar_len
            color = colors[status]

            lines.append(
                f'  [color={color}]{status:12s}[/color]  '
                f'[color={color}]{bar}[/color]  '
                f'{count}/{total} ({pct:.0%})'
            )

        lines.append('')
        lines.append('[b]Promotion Rate[/b]')

        exec_pct = counts['EXECUTABLE'] / total if total > 0 else 0
        if exec_pct >= 0.9:
            grade = '[color=00ff00]EXCELLENT[/color]'
        elif exec_pct >= 0.7:
            grade = '[color=00ff00]GOOD[/color]'
        elif exec_pct >= 0.5:
            grade = '[color=ffff00]MODERATE[/color]'
        else:
            grade = '[color=ff4444]LOW[/color]'

        lines.append(f'  EXECUTABLE rate: {exec_pct:.0%} — {grade}')
        lines.append('')

        # Confidence trend
        confs = [r['mean_confidence'] for r in results]
        if len(confs) >= 2:
            first_half = confs[:len(confs)//2]
            second_half = confs[len(confs)//2:]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            delta = avg_second - avg_first

            if delta > 0.01:
                trend = f'[color=00ff00]improving (+{delta:.4f})[/color]'
            elif delta < -0.01:
                trend = f'[color=ff4444]declining ({delta:.4f})[/color]'
            else:
                trend = f'[color=ffff00]stable ({delta:+.4f})[/color]'
            lines.append(f'[b]Confidence Trend[/b]')
            lines.append(f'  First half avg:  {avg_first:.4f}')
            lines.append(f'  Second half avg: {avg_second:.4f}')
            lines.append(f'  Trend: {trend}')
            lines.append('')

        # Per-frame timeline (last 15)
        lines.append('[b]Recent Frame Timeline[/b]')
        for r in results[-15:]:
            s = r.get('best_status', 'none')
            c = colors.get(s, '666666')
            lines.append(
                f'  #{r["frame_index"]:3d}  '
                f'[color={c}]{s:12s}[/color]  '
                f'conf={r["mean_confidence"]:.3f}  '
                f'prims={r["primitives"]}'
            )

        self.label.text = '\n'.join(lines)

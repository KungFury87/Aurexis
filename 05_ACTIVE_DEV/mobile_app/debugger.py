"""
debugger.py — M11 Aurexis IR Debugger and Inspector

Provides step-through debugging for Aurexis IR trees:
  - Step into/over/out of IR nodes
  - Breakpoints on tier transitions (e.g., break on EXECUTABLE promotion)
  - Watchpoints on confidence values (break when conf drops below threshold)
  - Core Law violation inspector (show which section violated and why)
  - Session export as reproducible JSON report

Architecture:
  - IRDebugger:       Core debug engine, walks IR tree, manages breakpoints
  - BreakpointManager: Handles tier, confidence, and custom breakpoints
  - LawInspector:     Analyzes Core Law violations in detail
  - DebugSession:     Records all steps for export
  - DebuggerWidget:   Kivy UI for the debugger tab

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window


# ────────────────────────────────────────────────────────────
# Debug step record
# ────────────────────────────────────────────────────────────

@dataclass
class DebugStep:
    """One step in the debug session."""
    step_number: int
    node_op: str
    node_depth: int
    node_index: int          # position among siblings
    confidence: float
    execution_status: str
    evidence_tier: str
    traceable: bool
    synthetic: bool
    pruned: bool
    breakpoint_hit: Optional[str] = None  # which breakpoint triggered
    law_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ────────────────────────────────────────────────────────────
# Breakpoint types
# ────────────────────────────────────────────────────────────

@dataclass
class Breakpoint:
    """A debug breakpoint."""
    bp_id: int
    bp_type: str        # 'tier_transition', 'confidence', 'status', 'op'
    condition: str       # e.g., 'EXECUTABLE', '<0.5', 'assign'
    enabled: bool = True
    hit_count: int = 0

    def check(self, step: DebugStep) -> bool:
        """Return True if this breakpoint should trigger."""
        if not self.enabled:
            return False

        if self.bp_type == 'status':
            return step.execution_status.upper() == self.condition.upper()

        elif self.bp_type == 'tier_transition':
            return step.evidence_tier.upper() == self.condition.upper()

        elif self.bp_type == 'confidence':
            # Condition like '<0.5' or '>0.8'
            try:
                if self.condition.startswith('<'):
                    return step.confidence < float(self.condition[1:])
                elif self.condition.startswith('>'):
                    return step.confidence > float(self.condition[1:])
                else:
                    return abs(step.confidence - float(self.condition)) < 0.001
            except ValueError:
                return False

        elif self.bp_type == 'op':
            return step.node_op == self.condition

        return False


# ────────────────────────────────────────────────────────────
# Core Law Violation Inspector
# ────────────────────────────────────────────────────────────

class LawInspector:
    """
    Analyzes Core Law violations on a per-node basis.
    Maps violations to specific Core Law sections.
    """

    # Core Law section descriptions (frozen)
    SECTIONS = {
        1: 'Evidence Origin — All data must originate from verifiable camera observation',
        2: 'Phoxel Schema — All records must conform to 6-field canonical schema',
        3: 'Illegal Inference — Cannot infer beyond what camera physically captured',
        4: 'Executable Promotion — Requires conf >= 0.7, REAL_CAPTURE, non-synthetic, traceable',
        5: 'Immutability — Core Law sections cannot be modified at runtime',
        6: 'Tech Floor — Max 30s processing, 500MB RAM, 5% battery/min',
        7: 'Evidence Chain — Every claim must have unbroken chain to source frame',
    }

    @staticmethod
    def inspect_node(node, opt_state) -> List[Dict[str, Any]]:
        """
        Check a node's optimization state against Core Law.
        Returns a list of violation dicts (empty = compliant).
        """
        violations = []

        if opt_state is None:
            return violations

        # Section 4: Executable promotion checks
        status = getattr(opt_state, 'execution_status', 'descriptive')
        if status == 'executable':
            conf = getattr(opt_state, 'confidence_mean', 0)
            if conf < 0.7:
                violations.append({
                    'section': 4,
                    'rule': 'Confidence >= 0.7 required for EXECUTABLE',
                    'actual': f'confidence={conf:.4f}',
                    'severity': 'CRITICAL',
                })

            if getattr(opt_state, 'synthetic', True):
                violations.append({
                    'section': 4,
                    'rule': 'synthetic must be False for EXECUTABLE',
                    'actual': 'synthetic=True',
                    'severity': 'CRITICAL',
                })

            if not getattr(opt_state, 'traceable', False):
                violations.append({
                    'section': 4,
                    'rule': 'traceable must be True for EXECUTABLE',
                    'actual': 'traceable=False',
                    'severity': 'CRITICAL',
                })

            tier = getattr(opt_state, 'evidence_tier', 'LAB')
            if tier.upper() not in ('REAL_CAPTURE', 'EARNED'):
                violations.append({
                    'section': 4,
                    'rule': 'Evidence tier must be REAL_CAPTURE or EARNED',
                    'actual': f'tier={tier}',
                    'severity': 'CRITICAL',
                })

        # Section 7: Evidence chain
        if not getattr(opt_state, 'traceable', False) and status != 'descriptive':
            violations.append({
                'section': 7,
                'rule': 'Non-descriptive nodes must be traceable',
                'actual': 'traceable=False',
                'severity': 'WARNING',
            })

        return violations


# ────────────────────────────────────────────────────────────
# IR Debugger Engine
# ────────────────────────────────────────────────────────────

class IRDebugger:
    """
    Step-through debugger for Aurexis IR trees.

    Usage:
        dbg = IRDebugger(ir_root)
        dbg.add_breakpoint('status', 'EXECUTABLE')
        while dbg.has_next():
            step = dbg.step_into()
            if step.breakpoint_hit:
                # inspect state
    """

    def __init__(self, ir_root=None):
        self.ir_root = ir_root
        self.breakpoints: List[Breakpoint] = []
        self._bp_counter = 0

        # Walk state
        self._flat_nodes: List[Tuple[Any, int, int]] = []  # (node, depth, sibling_idx)
        self._cursor = 0
        self._steps: List[DebugStep] = []
        self._step_counter = 0

        if ir_root is not None:
            self._flatten(ir_root, 0, 0)

    def load_tree(self, ir_root):
        """Load a new IR tree for debugging."""
        self.ir_root = ir_root
        self._flat_nodes = []
        self._cursor = 0
        self._steps = []
        self._step_counter = 0
        self._flatten(ir_root, 0, 0)

    def _flatten(self, node, depth, sibling_idx):
        """Flatten the IR tree into a list for sequential stepping."""
        self._flat_nodes.append((node, depth, sibling_idx))
        for i, child in enumerate(getattr(node, 'children', [])):
            self._flatten(child, depth + 1, i)

    def has_next(self) -> bool:
        return self._cursor < len(self._flat_nodes)

    @property
    def total_nodes(self) -> int:
        return len(self._flat_nodes)

    @property
    def current_position(self) -> int:
        return self._cursor

    @property
    def steps(self) -> List[DebugStep]:
        return self._steps

    # ── Breakpoint management ─────────────────────────────

    def add_breakpoint(self, bp_type: str, condition: str) -> int:
        """Add a breakpoint. Returns the breakpoint ID."""
        self._bp_counter += 1
        bp = Breakpoint(
            bp_id=self._bp_counter,
            bp_type=bp_type,
            condition=condition,
        )
        self.breakpoints.append(bp)
        return bp.bp_id

    def remove_breakpoint(self, bp_id: int):
        self.breakpoints = [b for b in self.breakpoints if b.bp_id != bp_id]

    def clear_breakpoints(self):
        self.breakpoints.clear()

    # ── Step commands ─────────────────────────────────────

    def step_into(self) -> Optional[DebugStep]:
        """Step to the next node (depth-first)."""
        if not self.has_next():
            return None

        node, depth, sib_idx = self._flat_nodes[self._cursor]
        self._cursor += 1
        return self._make_step(node, depth, sib_idx)

    def step_over(self) -> Optional[DebugStep]:
        """Step over children — jump to next sibling or parent's next sibling."""
        if not self.has_next():
            return None

        node, depth, sib_idx = self._flat_nodes[self._cursor]
        self._cursor += 1

        # Skip all children (nodes with depth > current depth)
        while self._cursor < len(self._flat_nodes):
            _, next_depth, _ = self._flat_nodes[self._cursor]
            if next_depth <= depth:
                break
            self._cursor += 1

        return self._make_step(node, depth, sib_idx)

    def step_out(self) -> Optional[DebugStep]:
        """Step out — jump to parent's next sibling."""
        if not self.has_next():
            return None

        node, depth, sib_idx = self._flat_nodes[self._cursor]

        # Find next node at depth - 1 or less
        self._cursor += 1
        while self._cursor < len(self._flat_nodes):
            _, next_depth, _ = self._flat_nodes[self._cursor]
            if next_depth < depth:
                break
            self._cursor += 1

        return self._make_step(node, depth, sib_idx)

    def run_to_breakpoint(self) -> Optional[DebugStep]:
        """Run until a breakpoint is hit or end of tree."""
        while self.has_next():
            step = self.step_into()
            if step and step.breakpoint_hit:
                return step
        return None

    def run_all(self) -> List[DebugStep]:
        """Run through entire tree, collecting all steps."""
        results = []
        while self.has_next():
            step = self.step_into()
            if step:
                results.append(step)
        return results

    def reset(self):
        """Reset to beginning of tree."""
        self._cursor = 0
        self._steps = []
        self._step_counter = 0

    # ── Internal ──────────────────────────────────────────

    def _make_step(self, node, depth, sib_idx) -> DebugStep:
        """Create a DebugStep from a node."""
        self._step_counter += 1

        opt = getattr(node, 'metadata', {}).get('opt', None)

        confidence = 0.0
        execution_status = 'descriptive'
        evidence_tier = 'LAB'
        traceable = False
        synthetic = True
        pruned = False

        if opt is not None:
            confidence = getattr(opt, 'confidence_mean', 0.0)
            execution_status = getattr(opt, 'execution_status', 'descriptive')
            evidence_tier = getattr(opt, 'evidence_tier', 'LAB')
            traceable = getattr(opt, 'traceable', False)
            synthetic = getattr(opt, 'synthetic', True)
            pruned = getattr(opt, 'pruned', False)
        else:
            # Fall back to args
            args = getattr(node, 'args', {})
            confidence = float(args.get('confidence', 0.0) or 0.0)

        # Check law violations
        law_violations = LawInspector.inspect_node(node, opt)

        step = DebugStep(
            step_number=self._step_counter,
            node_op=getattr(node, 'op', 'unknown'),
            node_depth=depth,
            node_index=sib_idx,
            confidence=confidence,
            execution_status=execution_status,
            evidence_tier=evidence_tier,
            traceable=traceable,
            synthetic=synthetic,
            pruned=pruned,
            law_violations=[v['rule'] for v in law_violations],
        )

        # Check breakpoints
        for bp in self.breakpoints:
            if bp.check(step):
                bp.hit_count += 1
                step.breakpoint_hit = f'BP#{bp.bp_id}({bp.bp_type}={bp.condition})'
                break  # Only report first hit

        self._steps.append(step)
        return step

    # ── Export ─────────────────────────────────────────────

    def export_session(self) -> Dict[str, Any]:
        """Export the debug session as a reproducible JSON report."""
        return {
            'debugger': 'aurexis_ir_debugger',
            'version': '1.0',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'total_nodes': self.total_nodes,
            'total_steps': len(self._steps),
            'breakpoints': [
                {
                    'id': bp.bp_id,
                    'type': bp.bp_type,
                    'condition': bp.condition,
                    'enabled': bp.enabled,
                    'hits': bp.hit_count,
                }
                for bp in self.breakpoints
            ],
            'steps': [s.to_dict() for s in self._steps],
            'summary': {
                'executable_nodes': sum(1 for s in self._steps if s.execution_status == 'executable'),
                'validated_nodes': sum(1 for s in self._steps if s.execution_status == 'validated'),
                'law_violations': sum(len(s.law_violations) for s in self._steps),
                'breakpoints_hit': sum(1 for s in self._steps if s.breakpoint_hit),
            },
        }


# ────────────────────────────────────────────────────────────
# Kivy Debugger Widget
# ────────────────────────────────────────────────────────────

class DebuggerWidget(BoxLayout):
    """
    Kivy UI for the M11 debugger tab.
    Shows: control buttons, current node info, step history, breakpoints.
    """

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', spacing=4, padding=4, **kwargs)

        self.debugger = IRDebugger()
        self._current_step = None

        # ── Control buttons ──
        btn_bar = BoxLayout(size_hint_y=None, height=45, spacing=4)

        self.btn_into = Button(text='Step Into', font_size='13sp',
                               background_color=(0.2, 0.5, 0.8, 1))
        self.btn_into.bind(on_press=self._on_step_into)

        self.btn_over = Button(text='Step Over', font_size='13sp',
                               background_color=(0.2, 0.6, 0.5, 1))
        self.btn_over.bind(on_press=self._on_step_over)

        self.btn_out = Button(text='Step Out', font_size='13sp',
                              background_color=(0.5, 0.4, 0.2, 1))
        self.btn_out.bind(on_press=self._on_step_out)

        self.btn_run = Button(text='Run to BP', font_size='13sp',
                              background_color=(0.7, 0.2, 0.2, 1))
        self.btn_run.bind(on_press=self._on_run_to_bp)

        btn_bar.add_widget(self.btn_into)
        btn_bar.add_widget(self.btn_over)
        btn_bar.add_widget(self.btn_out)
        btn_bar.add_widget(self.btn_run)
        self.add_widget(btn_bar)

        # ── Breakpoint controls ──
        bp_bar = BoxLayout(size_hint_y=None, height=35, spacing=4)

        bp_exec = Button(text='BP: EXEC', font_size='12sp',
                         background_color=(0.0, 0.4, 0.0, 1))
        bp_exec.bind(on_press=lambda x: self._add_bp('status', 'executable'))

        bp_valid = Button(text='BP: VALID', font_size='12sp',
                          background_color=(0.4, 0.4, 0.0, 1))
        bp_valid.bind(on_press=lambda x: self._add_bp('status', 'validated'))

        bp_lowconf = Button(text='BP: Conf<0.5', font_size='12sp',
                            background_color=(0.4, 0.2, 0.0, 1))
        bp_lowconf.bind(on_press=lambda x: self._add_bp('confidence', '<0.5'))

        bp_clear = Button(text='Clear BPs', font_size='12sp',
                          background_color=(0.3, 0.3, 0.3, 1))
        bp_clear.bind(on_press=self._clear_bps)

        bp_bar.add_widget(bp_exec)
        bp_bar.add_widget(bp_valid)
        bp_bar.add_widget(bp_lowconf)
        bp_bar.add_widget(bp_clear)
        self.add_widget(bp_bar)

        # ── Current node display ──
        self.node_label = Label(
            text='[b]DEBUGGER[/b]\nLoad an IR tree to begin',
            font_size='13sp',
            markup=True,
            size_hint_y=None,
            height=120,
            text_size=(Window.width - 20, None),
            halign='left',
            valign='top',
            color=(0.9, 1.0, 0.9, 1),
        )
        self.add_widget(self.node_label)

        # ── Step history (scrollable) ──
        scroll = ScrollView(size_hint=(1, 1))
        self.history_label = Label(
            text='Step history will appear here...',
            font_size='12sp',
            markup=True,
            size_hint_y=None,
            text_size=(Window.width - 20, None),
            halign='left',
            valign='top',
            color=(0.8, 0.85, 0.9, 1),
        )
        self.history_label.bind(texture_size=self.history_label.setter('size'))
        scroll.add_widget(self.history_label)
        self.add_widget(scroll)

        # ── Status bar ──
        self.status = Label(
            text='No tree loaded',
            font_size='12sp',
            size_hint_y=None,
            height=25,
            color=(0.5, 0.5, 0.5, 1),
        )
        self.add_widget(self.status)

    # ── Public API ────────────────────────────────────────

    def load_tree(self, ir_root, opt_report=None):
        """Load an IR tree from the pipeline."""
        self.debugger.load_tree(ir_root)
        self._opt_report = opt_report
        self._update_status()
        self.node_label.text = (
            f'[b]DEBUGGER[/b] — Tree loaded\n'
            f'Nodes: {self.debugger.total_nodes}\n'
            f'Use Step Into/Over/Out or set breakpoints'
        )
        self.history_label.text = ''

    # ── Button handlers ───────────────────────────────────

    def _on_step_into(self, *args):
        step = self.debugger.step_into()
        self._show_step(step)

    def _on_step_over(self, *args):
        step = self.debugger.step_over()
        self._show_step(step)

    def _on_step_out(self, *args):
        step = self.debugger.step_out()
        self._show_step(step)

    def _on_run_to_bp(self, *args):
        step = self.debugger.run_to_breakpoint()
        if step:
            self._show_step(step)
        else:
            self.node_label.text = (
                '[b]DEBUGGER[/b]\n'
                '[color=ffff00]No breakpoint hit — reached end of tree[/color]'
            )
        self._update_history()
        self._update_status()

    def _add_bp(self, bp_type, condition):
        bp_id = self.debugger.add_breakpoint(bp_type, condition)
        self._update_status()

    def _clear_bps(self, *args):
        self.debugger.clear_breakpoints()
        self._update_status()

    # ── Display helpers ───────────────────────────────────

    def _show_step(self, step: Optional[DebugStep]):
        if step is None:
            self.node_label.text = (
                '[b]DEBUGGER[/b]\n'
                '[color=888888]End of tree reached[/color]'
            )
            self._update_status()
            return

        indent = '  ' * step.node_depth
        status_color = {
            'executable': '00ff00',
            'validated': 'ffff00',
            'estimated': 'ff9900',
            'descriptive': '888888',
        }.get(step.execution_status, '666666')

        lines = ['[b]CURRENT NODE[/b]']
        lines.append(f'{indent}[b]{step.node_op}[/b]  (depth={step.node_depth}, idx={step.node_index})')
        lines.append(f'  Status: [color={status_color}]{step.execution_status.upper()}[/color]')
        lines.append(f'  Confidence: {step.confidence:.4f}')
        lines.append(f'  Tier: {step.evidence_tier}')
        lines.append(f'  Traceable: {step.traceable}  Synthetic: {step.synthetic}')
        if step.pruned:
            lines.append(f'  [color=ff4444]PRUNED[/color]')

        if step.breakpoint_hit:
            lines.append(f'  [color=ff0000]>>> BREAKPOINT: {step.breakpoint_hit}[/color]')

        if step.law_violations:
            lines.append(f'  [color=ff4444]LAW VIOLATIONS:[/color]')
            for v in step.law_violations:
                lines.append(f'    [color=ff4444]- {v}[/color]')

        self.node_label.text = '\n'.join(lines)
        self._current_step = step
        self._update_history()
        self._update_status()

    def _update_history(self):
        """Update the step history display."""
        steps = self.debugger.steps
        if not steps:
            return

        lines = ['[b]STEP HISTORY[/b] (last 20)']
        for s in steps[-20:]:
            color = {
                'executable': '00ff00',
                'validated': 'ffff00',
                'estimated': 'ff9900',
                'descriptive': '888888',
            }.get(s.execution_status, '666666')

            indent = '. ' * s.node_depth
            bp_marker = ' [color=ff0000]<!>[/color]' if s.breakpoint_hit else ''
            law_marker = ' [color=ff4444]*LAW*[/color]' if s.law_violations else ''

            lines.append(
                f'#{s.step_number:3d} {indent}'
                f'[color={color}]{s.node_op}[/color]  '
                f'c={s.confidence:.3f}  '
                f'{s.execution_status[:4].upper()}'
                f'{bp_marker}{law_marker}'
            )

        self.history_label.text = '\n'.join(lines)

    def _update_status(self):
        """Update the status bar."""
        pos = self.debugger.current_position
        total = self.debugger.total_nodes
        bps = len(self.debugger.breakpoints)
        steps = len(self.debugger.steps)
        self.status.text = f'Node {pos}/{total}  |  {steps} steps  |  {bps} breakpoints'

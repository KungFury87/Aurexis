"""Phoxelis Encoding Simulation.

The smallest correct stress test of the philosophical claim that meaning
can be carried by composable measurements. The encoder writes pixels
such that target predicates fire over target spatial regions; the
decoder evaluates the Phoxelis vocabulary on those regions and recovers
bits. Round-trip reliability is the empirical answer to whether
predicate-state-over-region works as an encoding alphabet.

v0.1 (this version):
  - 1 predicate per cell (has_red_dominant)
  - 4x4 grid, 16 bits per image
  - no distortion, clean encode -> decode round-trip
  - decoder uses the real Phoxelis runtime, not an inline reimplementation

If clean round-trip recovers 16/16 bits, the architecture is no longer
speculative. v0.2+ adds capture distortion sweeps, more predicates per
cell, and ultimately phone-camera-in-the-loop testing.
"""
__version__ = "0.1.0"

"""Aurexis Core V2 — benchmark artifact set (B1 base static screen family).

V2-M2 deterministic, zero-dependency benchmark generators for screen-based,
static-first, solo-feasible real-capture calibration work. This package
produces the five locked artifacts of the B1 family and their manifest.

All outputs are deterministic at the byte level. The PNG encoder uses
uncompressed zlib (deflate stored blocks) so byte-for-byte reproducibility
holds across Python / platform versions.

Artifacts in the B1 frozen set:
    b1-clean-solid         solid mid-gray                   (clean-detection baseline)
    b1-edge-half           bisected black/white             (edge/boundary stability)
    b1-grid-64             64 px checkerboard               (routing / moire observation)
    b1-gradient-h          horizontal luminance ramp        (signature / gradient stability)
    b1-corners-fiducials   4 white corner fiducials on black (angle / geometry baseline)

No protected or licensed code is used in this package. All source is
original Aurexis-V2 clean-room implementation.
"""

__all__ = ["png_writer", "generators", "render"]

SET_ID = "V2-BENCH-B1"
SET_VERSION = "1.0.0"
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080

"""Zero-dependency, byte-deterministic PNG encoder for V2 benchmark artifacts.

Emits 8-bit RGB PNGs (color type 2). Uses uncompressed zlib (deflate stored
blocks) so the output is byte-identical across Python versions, platforms,
and zlib implementations. This matters because `V2_BENCHMARK_SET_MANIFEST.json`
pins a SHA-256 per rendered asset and must match the bytes on disk exactly.

No external dependencies. Pure Python stdlib: struct, zlib only for CRC32,
and a hand-written deflate-stored-block + Adler-32 pipeline.

This code is original, clean-room, written for Aurexis Core V2.
"""

from __future__ import annotations

import struct
import zlib

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MAX_STORED_BLOCK = 65535  # max DEFLATE stored-block payload


def _adler32(data: bytes) -> int:
    """Compute Adler-32 per RFC 1950. Pure, deterministic."""
    MOD_ADLER = 65521
    a, b = 1, 0
    for byte in data:
        a = (a + byte) % MOD_ADLER
        b = (b + a) % MOD_ADLER
    return (b << 16) | a


def _zlib_stored(data: bytes) -> bytes:
    """Wrap `data` in a zlib stream using only DEFLATE stored blocks.

    Byte-deterministic. Independent of any zlib implementation's
    compression strategy.
    """
    # zlib header: CMF=0x78 (deflate, 32K window), FLG=0x01 (no preset dict,
    # FCHECK chosen so (CMF*256 + FLG) % 31 == 0).
    out = bytearray(b"\x78\x01")
    n = len(data)
    pos = 0
    while True:
        chunk_len = min(_MAX_STORED_BLOCK, n - pos)
        is_last = (pos + chunk_len) >= n
        bfinal = 1 if is_last else 0
        # Stored block: [BFINAL | BTYPE=00] in a single byte (LSB-first
        # bit packing puts BFINAL as bit 0, BTYPE as bits 1-2).
        out.append(bfinal & 0x01)
        out += struct.pack("<HH", chunk_len, (~chunk_len) & 0xFFFF)
        out += data[pos : pos + chunk_len]
        pos += chunk_len
        if is_last:
            break
    # Adler-32 of the uncompressed data, big-endian.
    out += struct.pack(">I", _adler32(data))
    return bytes(out)


def _chunk(tag: bytes, payload: bytes) -> bytes:
    """Build one PNG chunk: length | tag | payload | CRC32(tag+payload)."""
    crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)


def encode_rgb_png(width: int, height: int, rgb: bytes) -> bytes:
    """Encode an 8-bit RGB image to a byte-deterministic PNG.

    Parameters
    ----------
    width, height : int
        Image dimensions in pixels. Must be positive.
    rgb : bytes
        Raw image bytes, row-major, width * height * 3 bytes, 0-255 per channel,
        no padding, no filter bytes (we add them).

    Returns
    -------
    bytes
        A complete PNG file.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    expected = width * height * 3
    if len(rgb) != expected:
        raise ValueError(
            f"rgb buffer has {len(rgb)} bytes, expected {expected} "
            f"for {width}x{height} 8-bit RGB"
        )

    # Per PNG spec: each scanline is prefixed with a filter byte. We use
    # filter type 0 (None) for every row so the raw data is trivially
    # reproducible.
    stride = width * 3
    filtered = bytearray()
    for row in range(height):
        filtered.append(0)
        filtered += rgb[row * stride : (row + 1) * stride]

    idat = _zlib_stored(bytes(filtered))

    # IHDR: width, height, bit_depth=8, color_type=2 (RGB), compression=0,
    # filter=0, interlace=0.
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    return (
        _PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", idat)
        + _chunk(b"IEND", b"")
    )

"""Phoxelis-native image format (.phox) — v0.1.

The canonical content of a .phox image is *predicate states over a cell
grid*, not pixel values. Pixels are a downstream rendering for display
or for transport through pixel-only channels (web, social, JPEG email
attachments). The file IS the composition of measurements that the
philosophical position says carries the meaning.

This module defines the byte layout and read/write helpers. Renderer
and decoder live in phox_renderer.py and phox_decoder.py.

Layout (all integers little-endian):

  HEADER (16 bytes fixed):
    bytes 0..3   magic       'PHOX'
    byte  4      version     0x01
    bytes 5..6   grid_w      uint16 number of cell columns
    bytes 7..8   grid_h      uint16 number of cell rows
    byte  9      n_predicates uint8 (1..255)
    bytes 10..15 reserved    must be zero

  PREDICATE TABLE (variable):
    For each of n_predicates entries, in canonical order:
      byte 0       name_length uint8
      bytes 1..N   name        UTF-8 (no terminator)

  CELL DATA (n_cells * cell_byte_size bytes):
    cell_byte_size = ceil(n_predicates / 8)
    For each cell in row-major order (gy then gx),
    a packed bit array where bit i is the verdict of predicate i.

  OPTIONAL TAIL (TLV chunks, repeated until EOF):
    byte  0      type    uint8 (0x01=PNG render, 0x02=JPEG render,
                                 0xFF=user metadata)
    bytes 1..4   length  uint32
    bytes 5..    payload bytes
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

MAGIC = b"PHOX"
VERSION = 0x01

CHUNK_PNG = 0x01
CHUNK_JPEG = 0x02
CHUNK_USER = 0xFF


@dataclass
class PhoxImage:
    """In-memory representation of a .phox image."""
    grid_w: int
    grid_h: int
    predicate_names: list  # ordered list of predicate name strings
    # cell_states[gy][gx] = list[bool] of length n_predicates
    cell_states: list = field(default_factory=list)
    # tail TLV chunks
    chunks: list = field(default_factory=list)  # list of (type, payload_bytes)

    @property
    def n_predicates(self) -> int:
        return len(self.predicate_names)

    @property
    def n_cells(self) -> int:
        return self.grid_w * self.grid_h

    @property
    def cell_byte_size(self) -> int:
        return (self.n_predicates + 7) // 8

    @property
    def total_semantic_bits(self) -> int:
        return self.n_cells * self.n_predicates


def _pack_bits(bits) -> bytes:
    """Pack a list of bools into a big-endian-within-byte bitarray."""
    n = len(bits)
    out = bytearray((n + 7) // 8)
    for i, v in enumerate(bits):
        if v:
            out[i // 8] |= (1 << (7 - (i % 8)))
    return bytes(out)


def _unpack_bits(buf: bytes, n: int) -> list:
    """Reverse of _pack_bits."""
    out = []
    for i in range(n):
        out.append(bool(buf[i // 8] & (1 << (7 - (i % 8)))))
    return out


def write_phox(img: PhoxImage) -> bytes:
    """Serialize a PhoxImage to bytes."""
    if img.n_predicates < 1 or img.n_predicates > 255:
        raise ValueError(f"n_predicates must be in 1..255 (got {img.n_predicates})")
    if img.grid_w < 1 or img.grid_w > 65535:
        raise ValueError(f"grid_w out of range: {img.grid_w}")
    if img.grid_h < 1 or img.grid_h > 65535:
        raise ValueError(f"grid_h out of range: {img.grid_h}")
    if len(img.cell_states) != img.grid_h:
        raise ValueError(f"cell_states must have grid_h={img.grid_h} rows")
    for row in img.cell_states:
        if len(row) != img.grid_w:
            raise ValueError(f"each cell_states row must have grid_w={img.grid_w} entries")
        for cell in row:
            if len(cell) != img.n_predicates:
                raise ValueError(
                    f"each cell must have n_predicates={img.n_predicates} verdicts")

    out = bytearray()
    # header
    out += MAGIC
    out += bytes([VERSION])
    out += struct.pack("<HH", img.grid_w, img.grid_h)
    out += bytes([img.n_predicates])
    out += bytes(6)  # reserved

    # predicate table
    for name in img.predicate_names:
        nb = name.encode("utf-8")
        if len(nb) > 255:
            raise ValueError(f"predicate name too long: {name!r}")
        out += bytes([len(nb)])
        out += nb

    # cell data
    for gy in range(img.grid_h):
        for gx in range(img.grid_w):
            out += _pack_bits(img.cell_states[gy][gx])

    # optional tail chunks
    for chunk_type, payload in img.chunks:
        out += bytes([chunk_type])
        out += struct.pack("<I", len(payload))
        out += payload

    return bytes(out)


def read_phox(buf: bytes) -> PhoxImage:
    """Deserialize bytes back to a PhoxImage."""
    if len(buf) < 16:
        raise ValueError("buffer too small for header")
    if buf[:4] != MAGIC:
        raise ValueError(f"bad magic: {buf[:4]!r} (expected {MAGIC!r})")
    version = buf[4]
    if version != VERSION:
        raise ValueError(f"unsupported version: {version}")
    grid_w, grid_h = struct.unpack("<HH", buf[5:9])
    n_predicates = buf[9]
    # buf[10:16] reserved

    pos = 16
    predicate_names = []
    for _ in range(n_predicates):
        if pos >= len(buf):
            raise ValueError("truncated predicate table")
        name_len = buf[pos]; pos += 1
        if pos + name_len > len(buf):
            raise ValueError("truncated predicate name")
        predicate_names.append(buf[pos:pos + name_len].decode("utf-8"))
        pos += name_len

    cell_byte_size = (n_predicates + 7) // 8
    cell_states = []
    for gy in range(grid_h):
        row = []
        for gx in range(grid_w):
            if pos + cell_byte_size > len(buf):
                raise ValueError(f"truncated cell data at ({gy},{gx})")
            row.append(_unpack_bits(buf[pos:pos + cell_byte_size], n_predicates))
            pos += cell_byte_size
        cell_states.append(row)

    chunks = []
    while pos < len(buf):
        if pos + 5 > len(buf):
            break  # truncated chunk header — ignore tail
        ct = buf[pos]; pos += 1
        clen = struct.unpack("<I", buf[pos:pos + 4])[0]; pos += 4
        if pos + clen > len(buf):
            break
        chunks.append((ct, buf[pos:pos + clen]))
        pos += clen

    return PhoxImage(
        grid_w=grid_w,
        grid_h=grid_h,
        predicate_names=predicate_names,
        cell_states=cell_states,
        chunks=chunks,
    )

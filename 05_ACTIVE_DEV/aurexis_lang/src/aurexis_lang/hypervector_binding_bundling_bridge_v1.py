"""
Aurexis Core — Hypervector Binding / Bundling Bridge V1

Bounded executable high-dimensional representation layer for frozen
substrate outputs. Implements MAP (Multiply-Add-Permute) style
hyperdimensional computing with a very small set of operations.

What this proves:
  A small set of bounded hypervector operations (atomic generation,
  binding, bundling, permutation) can encode frozen substrate symbol
  identifiers into high-dimensional vectors. These vectors can be
  composed (bound/bundled) and later cleaned up to recover the original
  symbols.

What this does NOT prove:
  - Full hyperdimensional computing generality
  - Noise-robust real-camera cleanup
  - VSA as a replacement for the deterministic substrate
  - Full Aurexis Core completion

Design:
  - DIMENSION = 1024 (small but sufficient for bounded demo)
  - Bipolar encoding: vectors of +1/-1 values
  - generate_atomic(symbol_id, seed): deterministic random bipolar vector
  - bind(a, b): element-wise multiply (XOR-like for bipolar)
  - unbind(a, b): same as bind (self-inverse for bipolar multiply)
  - bundle(*vectors): element-wise sum + sign (majority vote)
  - permute(v, shifts): cyclic shift for ordered structure
  - inverse_permute(v, shifts): reverse cyclic shift
  - cosine_similarity(a, b): normalized dot product
  - Codebook: frozen mapping of symbol_id → atomic hypervector
  - V1_CODEBOOK: built from V1_CLEANUP_PROFILE

The VSA layer is AUXILIARY. It does NOT replace the deterministic substrate.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
import hashlib
import struct
import math

from aurexis_lang.vsa_cleanup_profile_bridge_v1 import (
    CLEANUP_PROFILE_VERSION, CLEANUP_PROFILE_FROZEN,
    V1_CLEANUP_PROFILE, FROZEN_SYMBOL_IDS,
    CleanupTarget, CleanupTargetKind,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

BINDING_VERSION = "V1.0"
BINDING_FROZEN = True


# ════════════════════════════════════════════════════════════
# HYPERVECTOR DIMENSION
# ════════════════════════════════════════════════════════════

DIMENSION = 1024


# ════════════════════════════════════════════════════════════
# BIPOLAR VECTOR TYPE (tuple of +1/-1 ints)
# ════════════════════════════════════════════════════════════

# We use plain tuples of ints for determinism and immutability.
# No numpy dependency.

HyperVector = Tuple[int, ...]


def _generate_bipolar_from_seed(seed_bytes: bytes, dim: int = DIMENSION) -> HyperVector:
    """
    Generate a deterministic bipolar vector from seed bytes.
    Uses SHA-256 chain to produce enough random bits.
    """
    values = []
    counter = 0
    while len(values) < dim:
        h = hashlib.sha256(seed_bytes + struct.pack(">I", counter)).digest()
        for byte in h:
            for bit in range(8):
                if len(values) >= dim:
                    break
                values.append(1 if (byte >> bit) & 1 else -1)
        counter += 1
    return tuple(values[:dim])


def generate_atomic(symbol_id: str, dim: int = DIMENSION) -> HyperVector:
    """
    Generate a deterministic atomic bipolar hypervector for a symbol.
    Same symbol_id always produces the same vector.
    """
    seed = f"aurexis_vsa_v1|{symbol_id}".encode("utf-8")
    return _generate_bipolar_from_seed(seed, dim)


# ════════════════════════════════════════════════════════════
# CORE OPERATIONS
# ════════════════════════════════════════════════════════════

def bind(a: HyperVector, b: HyperVector) -> HyperVector:
    """
    Bind two hypervectors (element-wise multiply).
    For bipolar vectors, this is equivalent to XOR.
    Self-inverse: bind(bind(a, b), b) ≈ a.
    """
    assert len(a) == len(b), f"Dimension mismatch: {len(a)} vs {len(b)}"
    return tuple(x * y for x, y in zip(a, b))


def unbind(a: HyperVector, b: HyperVector) -> HyperVector:
    """Unbind = bind (self-inverse for bipolar multiply)."""
    return bind(a, b)


def bundle(*vectors: HyperVector) -> HyperVector:
    """
    Bundle multiple hypervectors (element-wise sum + sign).
    This is the majority-vote superposition operation.
    Ties (sum=0) resolve to +1 for determinism.
    """
    if not vectors:
        raise ValueError("Cannot bundle zero vectors")
    dim = len(vectors[0])
    sums = [0] * dim
    for v in vectors:
        assert len(v) == dim, f"Dimension mismatch: {len(v)} vs {dim}"
        for i in range(dim):
            sums[i] += v[i]
    return tuple(1 if s >= 0 else -1 for s in sums)


def permute(v: HyperVector, shifts: int = 1) -> HyperVector:
    """
    Cyclic right-shift permutation for encoding order/position.
    permute(v, 1) shifts all elements one position to the right.
    """
    shifts = shifts % len(v)
    if shifts == 0:
        return v
    return v[-shifts:] + v[:-shifts]


def inverse_permute(v: HyperVector, shifts: int = 1) -> HyperVector:
    """Inverse of permute (cyclic left-shift)."""
    return permute(v, len(v) - (shifts % len(v)))


# ════════════════════════════════════════════════════════════
# SIMILARITY
# ════════════════════════════════════════════════════════════

def cosine_similarity(a: HyperVector, b: HyperVector) -> float:
    """
    Cosine similarity between two hypervectors.
    For bipolar vectors, this equals the normalized Hamming agreement.
    Returns a float in [-1.0, 1.0].
    """
    assert len(a) == len(b), f"Dimension mismatch: {len(a)} vs {len(b)}"
    dot = sum(x * y for x, y in zip(a, b))
    # For bipolar vectors, ||a|| = ||b|| = sqrt(dim)
    norm_sq = len(a)
    return dot / norm_sq


# ════════════════════════════════════════════════════════════
# CODEBOOK
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Codebook:
    """
    Frozen codebook mapping symbol IDs to atomic hypervectors.
    Used for encoding and cleanup retrieval.
    """
    entries: Tuple[Tuple[str, HyperVector], ...] = ()
    dimension: int = DIMENSION
    version: str = BINDING_VERSION

    @property
    def size(self) -> int:
        return len(self.entries)

    def get_vector(self, symbol_id: str) -> Optional[HyperVector]:
        for sid, vec in self.entries:
            if sid == symbol_id:
                return vec
        return None

    @property
    def all_symbol_ids(self) -> Tuple[str, ...]:
        return tuple(sid for sid, _ in self.entries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "size": self.size,
            "dimension": self.dimension,
            "symbol_ids": list(self.all_symbol_ids),
            "version": self.version,
        }


def build_codebook(symbol_ids: Tuple[str, ...], dim: int = DIMENSION) -> Codebook:
    """Build a frozen codebook from a tuple of symbol IDs."""
    entries = tuple((sid, generate_atomic(sid, dim)) for sid in symbol_ids)
    return Codebook(entries=entries, dimension=dim)


# ════════════════════════════════════════════════════════════
# FROZEN CODEBOOK INSTANCE
# ════════════════════════════════════════════════════════════

V1_CODEBOOK = build_codebook(FROZEN_SYMBOL_IDS)


# ════════════════════════════════════════════════════════════
# COMPOSITE ENCODING HELPERS
# ════════════════════════════════════════════════════════════

def encode_ordered_set(symbol_ids: Tuple[str, ...], codebook: Codebook = V1_CODEBOOK) -> HyperVector:
    """
    Encode an ordered set of symbols into a single hypervector.
    Uses permutation to encode position: bundle(permute(v0, 0), permute(v1, 1), ...).
    """
    vectors = []
    for i, sid in enumerate(symbol_ids):
        vec = codebook.get_vector(sid)
        if vec is None:
            raise ValueError(f"Symbol {sid} not in codebook")
        vectors.append(permute(vec, i))
    return bundle(*vectors)


def encode_bound_pair(sid_a: str, sid_b: str, codebook: Codebook = V1_CODEBOOK) -> HyperVector:
    """Encode a bound pair of symbols: bind(a, b)."""
    va = codebook.get_vector(sid_a)
    vb = codebook.get_vector(sid_b)
    if va is None or vb is None:
        raise ValueError(f"Symbol not in codebook: {sid_a if va is None else sid_b}")
    return bind(va, vb)


# ════════════════════════════════════════════════════════════
# NOISE INJECTION (for testing cleanup retrieval)
# ════════════════════════════════════════════════════════════

def add_noise(v: HyperVector, flip_fraction: float, seed: int = 42) -> HyperVector:
    """
    Add noise by flipping a fraction of bits.
    Deterministic given seed.
    """
    dim = len(v)
    n_flip = int(dim * flip_fraction)
    # Generate deterministic flip positions
    h = hashlib.sha256(f"noise|{seed}|{dim}|{flip_fraction}".encode()).digest()
    positions = set()
    counter = 0
    while len(positions) < n_flip:
        hh = hashlib.sha256(h + struct.pack(">I", counter)).digest()
        for i in range(0, len(hh) - 1, 2):
            pos = (hh[i] << 8 | hh[i + 1]) % dim
            positions.add(pos)
            if len(positions) >= n_flip:
                break
        counter += 1
    result = list(v)
    for pos in positions:
        result[pos] = -result[pos]
    return tuple(result)


# ════════════════════════════════════════════════════════════
# PREDEFINED COUNTS
# ════════════════════════════════════════════════════════════

EXPECTED_CODEBOOK_SIZE = len(FROZEN_SYMBOL_IDS)  # 11
EXPECTED_DIMENSION = DIMENSION  # 1024

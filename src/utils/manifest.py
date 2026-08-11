"""Parses Steam depot .manifest files to extract per-file uncompressed sizes.

Depot manifests are binary files (SteamKit2 format): a small header followed
by a protobuf payload. DDMod's stdout only prints per-file percentage
progress without byte counts, so we parse the manifest up front to derive
download speed (delta bytes / delta time) ourselves.

Supported magic values:
  - v3: 0x71F617D0 (protobuf at offset 8, headerSize bytes)
  - v2: 0x374A56  (protobuf at offset 12, headerSize bytes)
v1 ("VJ0", KeyValue binary) is not supported; parsing returns None and
downloads simply show no speed.
"""
from pathlib import Path
from typing import Dict, Optional

MANIFEST_MAGIC_V3 = 0x71F617D0
MANIFEST_MAGIC_V2 = 0x374A56


def _read_varint(data: bytes, pos: int) -> tuple:
    """Decodes a protobuf varint; returns (value, next_pos)."""
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError("truncated varint")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7


def _parse_mapping(data: bytes, start: int, end: int) -> tuple:
    """Parses one ContentManifestFileMapping (path=1, size=2, ...).

    Returns (path, size, next_pos). Unknown fields are skipped by wire type.
    """
    path = None
    size = None
    pos = start
    while pos < end:
        tag, pos = _read_varint(data, pos)
        field = tag >> 3
        wire = tag & 7
        if wire == 0:
            value, pos = _read_varint(data, pos)
            if field == 2:
                size = value
        elif wire == 1:
            pos += 8
        elif wire == 2:
            length, pos = _read_varint(data, pos)
            value = data[pos:pos + length]
            pos += length
            if field == 1:
                path = value.decode("utf-8", errors="replace")
        elif wire == 5:
            pos += 4
        else:
            # groups/unknown: cannot continue reliably
            break
    return path, size, pos


def parse_manifest(file_path: str) -> Optional[Dict[str, int]]:
    """Returns {relative_path: uncompressed_size} for a depot manifest file.

    Returns None when the format is unsupported (e.g. v1) or unreadable —
    callers then simply fall back to showing no download speed.
    """
    try:
        data = Path(file_path).read_bytes()
    except OSError:
        return None

    if len(data) < 8:
        return None

    magic = int.from_bytes(data[:4], "little")
    if magic == MANIFEST_MAGIC_V3:
        header_size = int.from_bytes(data[4:8], "little")
        start, end = 8, 8 + header_size
    elif magic == MANIFEST_MAGIC_V2:
        if len(data) < 12:
            return None
        header_size = int.from_bytes(data[4:8], "little")
        start, end = 12, 12 + header_size
    else:
        return None

    end = min(end, len(data))
    sizes: Dict[str, int] = {}
    pos = start
    try:
        while pos < end:
            tag, pos = _read_varint(data, pos)
            field = tag >> 3
            wire = tag & 7
            if wire != 2:
                break  # top-level scalar/unknown fields: stop
            length, pos = _read_varint(data, pos)
            sub_end = pos + length
            if sub_end > end:
                break
            if field == 1:
                path, size, _ = _parse_mapping(data, pos, sub_end)
                if path and size is not None:
                    sizes[path] = size
            pos = sub_end
    except (ValueError, IndexError):
        return None

    return sizes or None

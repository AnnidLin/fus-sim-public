#!/usr/bin/env python3
"""Inspect the official ITRUSST ZIP directory using HTTP byte ranges only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import urllib.request
import zlib
from pathlib import Path
from typing import Any


DEFAULT_URL = (
    "https://zenodo.org/api/records/6020543/files/"
    "INTERCOMPARISON-PH1-DATA-V1.0.zip/content"
)
EOCD_SIGNATURE = b"PK\x05\x06"
ZIP64_EOCD_SIGNATURE = b"PK\x06\x06"
ZIP64_LOCATOR_SIGNATURE = b"PK\x06\x07"
CENTRAL_SIGNATURE = b"PK\x01\x02"


def request_size(url: str, timeout: float) -> int:
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        size = response.headers.get("Content-Length")
    if size is None:
        raise RuntimeError("Remote server did not provide Content-Length")
    return int(size)


def request_range(url: str, start: int, end: int, timeout: float) -> bytes:
    if start < 0 or end < start:
        raise ValueError("Invalid byte range")
    request = urllib.request.Request(
        url, headers={"Range": f"bytes={start}-{end}"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 206:
            raise RuntimeError(
                f"Server ignored byte range: HTTP {response.status}; aborting"
            )
        expected = end - start + 1
        data = response.read(expected + 1)
    if len(data) != expected:
        raise RuntimeError(f"Expected {expected} bytes, received {len(data)}")
    return data


def locate_central_directory(url: str, size: int, timeout: float) -> tuple[int, int, int]:
    tail_size = min(size, 65557)
    tail_start = size - tail_size
    tail = request_range(url, tail_start, size - 1, timeout)
    eocd_index = tail.rfind(EOCD_SIGNATURE)
    if eocd_index < 0:
        raise RuntimeError("ZIP end-of-central-directory record not found")
    eocd = struct.unpack_from("<4s4H2LH", tail, eocd_index)
    entries, directory_size, directory_offset = int(eocd[4]), int(eocd[5]), int(eocd[6])
    if (
        entries != 0xFFFF
        and directory_size != 0xFFFFFFFF
        and directory_offset != 0xFFFFFFFF
    ):
        return directory_offset, directory_size, entries

    locator_index = tail.rfind(ZIP64_LOCATOR_SIGNATURE, 0, eocd_index)
    if locator_index < 0:
        raise RuntimeError("ZIP64 locator not found")
    _, _, zip64_offset, _ = struct.unpack_from("<4sLQL", tail, locator_index)
    zip64 = request_range(url, int(zip64_offset), int(zip64_offset) + 55, timeout)
    values = struct.unpack("<4sQ2H2L4Q", zip64)
    if values[0] != ZIP64_EOCD_SIGNATURE:
        raise RuntimeError("Invalid ZIP64 end-of-central-directory signature")
    return int(values[9]), int(values[8]), int(values[7])


def _zip64_values(
    extra: bytes,
    compressed_size: int,
    uncompressed_size: int,
    local_offset: int,
) -> tuple[int, int, int]:
    cursor = 0
    while cursor + 4 <= len(extra):
        header_id, length = struct.unpack_from("<HH", extra, cursor)
        cursor += 4
        payload = extra[cursor : cursor + length]
        cursor += length
        if header_id != 0x0001:
            continue
        value_cursor = 0
        if uncompressed_size == 0xFFFFFFFF:
            uncompressed_size = struct.unpack_from("<Q", payload, value_cursor)[0]
            value_cursor += 8
        if compressed_size == 0xFFFFFFFF:
            compressed_size = struct.unpack_from("<Q", payload, value_cursor)[0]
            value_cursor += 8
        if local_offset == 0xFFFFFFFF:
            local_offset = struct.unpack_from("<Q", payload, value_cursor)[0]
        break
    return int(compressed_size), int(uncompressed_size), int(local_offset)


def parse_central_directory(data: bytes, expected_entries: int | None = None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    cursor = 0
    header_format = "<4s6H3L5H2L"
    header_size = struct.calcsize(header_format)
    while cursor < len(data):
        if len(data) - cursor < header_size:
            raise RuntimeError("Truncated central-directory header")
        fields = struct.unpack_from(header_format, data, cursor)
        if fields[0] != CENTRAL_SIGNATURE:
            raise RuntimeError(f"Invalid central-directory signature at byte {cursor}")
        flags = int(fields[3])
        compression = int(fields[4])
        crc32 = int(fields[7])
        compressed_size = int(fields[8])
        uncompressed_size = int(fields[9])
        name_length, extra_length, comment_length = map(int, fields[10:13])
        local_offset = int(fields[16])
        variable_start = cursor + header_size
        name_bytes = data[variable_start : variable_start + name_length]
        extra_start = variable_start + name_length
        extra = data[extra_start : extra_start + extra_length]
        encoding = "utf-8" if flags & 0x800 else "cp437"
        name = name_bytes.decode(encoding)
        compressed_size, uncompressed_size, local_offset = _zip64_values(
            extra, compressed_size, uncompressed_size, local_offset
        )
        entries.append(
            {
                "name": name,
                "compressed_size": compressed_size,
                "uncompressed_size": uncompressed_size,
                "compression_method": compression,
                "flags": flags,
                "crc32": f"{crc32:08x}",
                "local_header_offset": local_offset,
            }
        )
        cursor = extra_start + extra_length + comment_length
    if expected_entries is not None and len(entries) != expected_entries:
        raise RuntimeError(
            f"Expected {expected_entries} entries, parsed {len(entries)}"
        )
    return entries


def inspect_archive(
    url: str,
    pattern: str | None,
    timeout: float,
    max_directory_bytes: int,
) -> dict[str, Any]:
    size = request_size(url, timeout)
    offset, directory_size, count = locate_central_directory(url, size, timeout)
    if directory_size > max_directory_bytes:
        raise RuntimeError(
            f"Central directory is {directory_size} bytes, above safety limit "
            f"{max_directory_bytes}"
        )
    directory = request_range(url, offset, offset + directory_size - 1, timeout)
    entries = parse_central_directory(directory, count)
    regex = re.compile(pattern) if pattern else None
    matches = [
        entry for entry in entries if regex is None or regex.search(entry["name"])
    ]
    return {
        "schema_version": "1.0",
        "mode": "metadata_only_http_range",
        "url": url,
        "archive_size_bytes": size,
        "central_directory_offset": offset,
        "central_directory_size_bytes": directory_size,
        "entry_count": count,
        "match_pattern": pattern,
        "matched_entry_count": len(matches),
        "matched_entries": matches,
        "payload_files_downloaded": False,
    }


def download_entry(
    url: str,
    entry: dict[str, Any],
    output_root: Path,
    timeout: float,
) -> dict[str, Any]:
    name = str(entry["name"])
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"Unsafe archive path: {name}")
    if int(entry["flags"]) & 0x1:
        raise RuntimeError(f"Encrypted ZIP entry is unsupported: {name}")
    local_offset = int(entry["local_header_offset"])
    header = request_range(url, local_offset, local_offset + 29, timeout)
    fields = struct.unpack("<4s5H3L2H", header)
    if fields[0] != b"PK\x03\x04":
        raise RuntimeError(f"Invalid local-file header for {name}")
    compression = int(fields[3])
    name_length, extra_length = int(fields[9]), int(fields[10])
    data_start = local_offset + 30 + name_length + extra_length
    compressed_size = int(entry["compressed_size"])
    compressed = request_range(
        url, data_start, data_start + compressed_size - 1, timeout
    )
    if compression == 0:
        payload = compressed
    elif compression == 8:
        payload = zlib.decompress(compressed, -zlib.MAX_WBITS)
    else:
        raise RuntimeError(
            f"Unsupported ZIP compression method {compression} for {name}"
        )
    if len(payload) != int(entry["uncompressed_size"]):
        raise RuntimeError(f"Uncompressed size mismatch for {name}")
    crc32 = f"{zlib.crc32(payload) & 0xFFFFFFFF:08x}"
    if crc32 != entry["crc32"]:
        raise RuntimeError(f"CRC32 mismatch for {name}")
    destination = (output_root / relative).resolve()
    destination.relative_to(output_root.resolve())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return {
        "archive_name": name,
        "path": str(destination),
        "size_bytes": len(payload),
        "crc32": crc32,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--match", default=r"PH1-BM(?:1|3|4)-SC1")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-directory-mib", type=float, default=8.0)
    parser.add_argument("--extract-dir")
    parser.add_argument("--max-payload-mib", type=float, default=16.0)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = inspect_archive(
        args.url,
        args.match,
        args.timeout,
        int(args.max_directory_mib * 1024 * 1024),
    )
    if args.extract_dir:
        total_compressed = sum(
            int(entry["compressed_size"]) for entry in report["matched_entries"]
        )
        limit = int(args.max_payload_mib * 1024 * 1024)
        if total_compressed > limit:
            raise RuntimeError(
                f"Selected payload is {total_compressed} compressed bytes, "
                f"above safety limit {limit}"
            )
        output_root = Path(args.extract_dir).resolve()
        extracted = [
            download_entry(args.url, entry, output_root, args.timeout)
            for entry in report["matched_entries"]
        ]
        report["payload_files_downloaded"] = True
        report["payload_compressed_bytes_requested"] = total_compressed
        report["extracted_entries"] = extracted
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "entry_count": report["entry_count"],
                "matched_entry_count": report["matched_entry_count"],
                "output": str(output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

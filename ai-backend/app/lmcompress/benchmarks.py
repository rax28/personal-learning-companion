from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = (".txt", ".log", ".md", ".json", ".xml", ".csv", ".y4m")


def _run(cmd: list[str]) -> None:
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def benchmark_text(input_dir: str, compression_type: str = "brotli", output_dir: str | None = None) -> dict:
    """Benchmark the classical text compressors from the supplied LMCompress script."""
    input_path = Path(input_dir)
    files = sorted(p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS)
    if not files:
        return {"files": 0, "original_bytes": 0, "compressed_bytes": 0, "ratio_percent": None, "seconds": 0.0}
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    original_total = 0
    compressed_total = 0
    elapsed = 0.0
    commands = {
        "zpaq": lambda src, dst: ["zpaq", "add", str(dst), str(src), "-method", "5", "-threads", "1"],
        "7z": lambda src, dst: ["7zz", "a", "-mx=9", "-mmt=1", str(dst), str(src)],
        "zstd": lambda src, dst: ["zstd", "--ultra", "-22", "-T1", "-f", str(src), "-o", str(dst)],
        "ppm": lambda src, dst: ["ppmd", "c", str(src), str(dst)],
    }
    if compression_type == "brotli":
        import brotli
    elif compression_type not in commands:
        raise ValueError(f"Unsupported text compressor: {compression_type}")

    with tempfile.TemporaryDirectory() as tmp:
        for src in files:
            original_total += src.stat().st_size
            ext = {"brotli": ".br", "zpaq": ".zpaq", "7z": ".7z", "zstd": ".zst", "ppm": ".ppm"}[compression_type]
            dst = Path(tmp) / (src.stem + ext)
            start = time.perf_counter()
            if compression_type == "brotli":
                dst.write_bytes(brotli.compress(src.read_bytes(), quality=11))
            else:
                _run(commands[compression_type](src, dst))
            elapsed += time.perf_counter() - start
            compressed_total += dst.stat().st_size
            if output_dir:
                shutil.copy2(dst, Path(output_dir) / dst.name)
    return {
        "files": len(files),
        "original_bytes": original_total,
        "compressed_bytes": compressed_total,
        "ratio_percent": 100.0 * compressed_total / original_total,
        "seconds": elapsed,
    }


def benchmark_audio(input_dir: str, compression_type: str = "flac", output_dir: str | None = None, level: int = 12) -> dict:
    """Benchmark FLAC, OptimFROG, or WavPack for WAV inputs."""
    input_path = Path(input_dir)
    files = sorted(p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() == ".wav")
    if not files:
        return {"files": 0, "original_bytes": 0, "compressed_bytes": 0, "ratio_percent": None, "seconds": 0.0}
    commands = {
        "flac": lambda src, dst: ["ffmpeg", "-i", str(src), "-c:a", "flac", "-compression_level", str(level), "-y", str(dst)],
        "ofr": lambda src, dst: ["ofr", "--encode", "--preset", "max", str(src), "--output", str(dst)],
        "wavpack": lambda src, dst: ["wavpack", "-hh", "-x3", "--threads=1", str(src), "-o", str(dst)],
    }
    if compression_type not in commands:
        raise ValueError(f"Unsupported audio compressor: {compression_type}")
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    ext = {"flac": ".flac", "ofr": ".ofr", "wavpack": ".wv"}[compression_type]
    original_total = compressed_total = 0
    elapsed = 0.0
    with tempfile.TemporaryDirectory() as tmp:
        for src in files:
            original_total += src.stat().st_size
            dst = Path(tmp) / (src.stem + ext)
            start = time.perf_counter(); _run(commands[compression_type](src, dst)); elapsed += time.perf_counter() - start
            compressed_total += dst.stat().st_size
            if output_dir:
                shutil.copy2(dst, Path(output_dir) / dst.name)
    return {"files": len(files), "original_bytes": original_total, "compressed_bytes": compressed_total, "ratio_percent": 100.0 * compressed_total / original_total, "seconds": elapsed}

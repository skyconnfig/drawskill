#!/usr/bin/env python3
"""Deterministic whiteboard-drawing renderer.

The renderer deliberately does not call an image model. Codex creates the
storyboard and ImageGen assets first; this script plans repeatable drawing
routes from those pixels and renders the animation.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])")
CLAUSE_SPLIT = re.compile(r"(?<=[，,、：:])")
SPEECH_CHARS = re.compile(r"[\u3400-\u9fffA-Za-z0-9]")
VISUAL_STYLES = ("reference-adapted", "editorial-character")
DEFAULT_CAPTION_SAFE_TOP_RATIO = 0.76
VISUAL_PROMPT_TODOS = {
    "reference-adapted": (
        "TODO: describe one original visual metaphor using only the approved abstract "
        "style_profile; do not copy reference characters, objects, poses, or composition"
    ),
    "editorial-character": (
        "TODO: describe one concrete visual metaphor; do not copy narration as text"
    ),
}


def ffmpeg_executable() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "FFmpeg is required. Run scripts/check_env.py for the install command."
        ) from exc


def resolve(base: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def split_long_unit(text: str, maximum: int) -> list[str]:
    if len(SPEECH_CHARS.findall(text)) <= maximum:
        return [text]
    clauses = [part.strip() for part in CLAUSE_SPLIT.split(text) if part.strip()]
    if len(clauses) <= 1:
        return [text[i : i + maximum] for i in range(0, len(text), maximum)]
    result: list[str] = []
    current = ""
    for clause in clauses:
        proposed = current + clause
        if current and len(SPEECH_CHARS.findall(proposed)) > maximum:
            result.append(current)
            current = clause
        else:
            current = proposed
    if current:
        result.append(current)
    return result


def split_narration(text: str, target: int, maximum: int) -> list[str]:
    normalized = re.sub(r"[ \t]+", "", text.replace("\r", "\n"))
    normalized = re.sub(r"\n+", "\n", normalized).strip()
    paragraphs = [p.strip() for p in normalized.split("\n") if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        for sentence in SENTENCE_SPLIT.split(paragraph):
            sentence = sentence.strip()
            if sentence:
                units.extend(split_long_unit(sentence, maximum))

    scenes: list[str] = []
    current = ""
    for unit in units:
        proposed = current + unit
        count = len(SPEECH_CHARS.findall(proposed))
        if current and count > maximum:
            scenes.append(current)
            current = unit
        elif current and len(SPEECH_CHARS.findall(current)) >= target:
            scenes.append(current)
            current = unit
        else:
            current = proposed
    if current:
        scenes.append(current)
    return scenes


def estimate_duration(text: str, cps: float) -> float:
    spoken = len(SPEECH_CHARS.findall(text)) / max(cps, 0.5)
    pause = (
        0.58 * sum(text.count(mark) for mark in "。！？!?")
        + 0.25 * sum(text.count(mark) for mark in "，,、")
        + 0.35 * sum(text.count(mark) for mark in "；;：:")
    )
    return round(min(15.0, max(4.5, spoken + pause + 0.35)), 2)


def create_project(args: argparse.Namespace) -> int:
    if args.input == "-":
        narration = sys.stdin.read()
        base = Path.cwd()
    else:
        source = Path(args.input).expanduser().resolve()
        narration = source.read_text(encoding="utf-8")
        base = source.parent

    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = base / output

    visual_style = args.visual_style or (
        "reference-adapted" if args.style_reference else "editorial-character"
    )
    if visual_style == "reference-adapted" and not args.style_reference:
        raise ValueError("reference-adapted requires --style-reference")
    if args.style_reference and visual_style != "reference-adapted":
        raise ValueError("--style-reference requires --visual-style reference-adapted")

    style_reference = None
    if args.style_reference:
        reference_source = Path(args.style_reference).expanduser().resolve()
        if not reference_source.is_file():
            raise FileNotFoundError(f"Style reference not found: {reference_source}")
        digest = hashlib.sha256(reference_source.read_bytes()).hexdigest()[:10]
        suffix = reference_source.suffix.lower() or ".png"
        reference_target = output.parent / "assets" / f"style-reference-{digest}{suffix}"
        reference_target.parent.mkdir(parents=True, exist_ok=True)
        if reference_source != reference_target:
            shutil.copy2(reference_source, reference_target)
        style_reference = str(reference_target.relative_to(output.parent))

    parts = split_narration(narration, args.target_chars, args.max_chars)
    if not parts:
        raise ValueError("Narration is empty after normalization")

    scenes: list[dict[str, Any]] = []
    for index, part in enumerate(parts, start=1):
        scene_id = f"scene-{index:03d}"
        scenes.append(
            {
                "id": scene_id,
                "narration": part,
                "duration": estimate_duration(part, args.speech_rate),
                "visual_prompt": VISUAL_PROMPT_TODOS[visual_style],
                "image": f"scenes/{scene_id}.png",
            }
        )

    project = {
        "version": 1,
        "title": args.title,
        "visual_style": visual_style,
        "narration": narration,
        "speech_rate_cps": args.speech_rate,
        "canvas": {
            "width": args.width,
            "height": args.height,
            "fps": args.fps,
            "background": "#fbf8ef",
            "caption_safe_area": {
                "enabled": True,
                "top_ratio": DEFAULT_CAPTION_SAFE_TOP_RATIO,
                "bottom_ratio": 1.0,
            },
        },
        "style": {
            "grid_cell": max(4, round(args.width / 240)),
            "ink_threshold": 170,
            "content_distance": 12,
            "fill_route_stride": 3,
            "max_reveal_radius_px": max(22, round(args.width * 0.014)),
            "draw_ratio": 0.67,
            "color_ratio": 0.33,
            "hold_seconds": 1.2,
            "paper_noise": 2.2,
        },
        "hand": {
            "image": "assets/hand.png",
            "metadata": "assets/hand.json",
            "width_ratio": 0.19,
        },
        "scenes": scenes,
    }
    if args.narrator_gender:
        project["narrator_gender"] = args.narrator_gender
    if style_reference:
        project["style_reference"] = style_reference
        project["style_profile"] = {
            "medium": "TODO: describe transferable medium",
            "line": "TODO: describe line weight, pressure, wobble, taper, and hierarchy",
            "palette": ["TODO: background", "TODO: primary ink", "TODO: accent colors"],
            "texture": "TODO: describe surface and fill texture",
            "shape_language": "TODO: describe abstract shape and proportion tendencies",
            "shading": "TODO: describe shading behavior",
            "density": "TODO: describe whitespace and detail density",
            "composition": "TODO: describe abstract hierarchy and rhythm without copying layout",
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {output} with {len(scenes)} scenes")
    return 0


def border_pixels(rgb: np.ndarray) -> np.ndarray:
    return np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]), axis=0)


def prepare_hand(args: argparse.Namespace) -> int:
    source_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    image = Image.open(source_path).convert("RGB")
    rgb = np.asarray(image, dtype=np.float32)
    key = np.median(border_pixels(rgb), axis=0)
    distance = np.linalg.norm(rgb - key[None, None, :], axis=2)
    alpha = np.clip(
        (distance - args.transparent_threshold)
        / max(1.0, args.opaque_threshold - args.transparent_threshold),
        0.0,
        1.0,
    )
    alpha = (alpha * alpha * (3.0 - 2.0 * alpha) * 255.0).astype(np.uint8)

    keyed = rgb.copy()
    if key[1] > key[0] * 1.25 and key[1] > key[2] * 1.25:
        excess = np.maximum(0.0, keyed[:, :, 1] - np.maximum(keyed[:, :, 0], keyed[:, :, 2]))
        keyed[:, :, 1] -= excess * 0.96
    if args.edge_contract > 0:
        matte = Image.fromarray(alpha)
        for _ in range(args.edge_contract):
            matte = matte.filter(ImageFilter.MinFilter(3))
        alpha = np.asarray(matte, dtype=np.uint8)
    rgba = np.dstack((np.clip(keyed, 0, 255).astype(np.uint8), alpha))

    ys, xs = np.where(alpha > 8)
    if not len(xs):
        raise ValueError("No foreground found; verify that the source uses a flat chroma key")
    margin = max(2, args.margin)
    left = max(0, int(xs.min()) - margin)
    top = max(0, int(ys.min()) - margin)
    right = min(rgba.shape[1], int(xs.max()) + 1 + margin)
    bottom = min(rgba.shape[0], int(ys.max()) + 1 + margin)
    cropped = rgba[top:bottom, left:right]

    source_tip_x = args.tip_x * rgba.shape[1]
    source_tip_y = args.tip_y * rgba.shape[0]
    anchor_x = (source_tip_x - left) / max(1, right - left)
    anchor_y = (source_tip_y - top) / max(1, bottom - top)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cropped).save(output_path)
    metadata_path = (
        Path(args.metadata).expanduser().resolve()
        if args.metadata
        else output_path.with_suffix(".json")
    )
    metadata = {
        "source": str(source_path),
        "tip_anchor": [round(anchor_x, 6), round(anchor_y, 6)],
        "source_tip": [args.tip_x, args.tip_y],
        "key_rgb": [round(float(value), 2) for value in key],
        "crop": [left, top, right, bottom],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {output_path}")
    print(f"Marker-tip anchor: {metadata['tip_anchor']}")
    return 0


def parse_color(value: str) -> tuple[int, int, int]:
    stripped = value.lstrip("#")
    if len(stripped) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {value}")
    return tuple(int(stripped[i : i + 2], 16) for i in (0, 2, 4))


def fit_to_canvas(path: Path, width: int, height: int, background: tuple[int, int, int]) -> np.ndarray:
    source = Image.open(path).convert("RGB")
    fitted = ImageOps.contain(source, (width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), background)
    x = (width - fitted.width) // 2
    y = (height - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    return np.asarray(canvas, dtype=np.uint8)


def grid_counts(mask: np.ndarray, cell: int) -> np.ndarray:
    height, width = mask.shape
    rows = math.ceil(height / cell)
    cols = math.ceil(width / cell)
    padded = np.zeros((rows * cell, cols * cell), dtype=np.uint8)
    padded[:height, :width] = mask.astype(np.uint8)
    return padded.reshape(rows, cell, cols, cell).sum(axis=(1, 3))


def thin_grid(active: np.ndarray) -> np.ndarray:
    """Reduce a thick binary grid to one-cell centerlines with Zhang-Suen thinning."""
    skeleton = active.astype(np.uint8).copy()
    for _ in range(100):
        removed = 0
        for subiteration in (0, 1):
            padded = np.pad(skeleton, 1)
            neighbors = [
                padded[:-2, 1:-1],
                padded[:-2, 2:],
                padded[1:-1, 2:],
                padded[2:, 2:],
                padded[2:, 1:-1],
                padded[2:, :-2],
                padded[1:-1, :-2],
                padded[:-2, :-2],
            ]
            neighbor_count = sum(item.astype(np.int16) for item in neighbors)
            transitions = sum(
                ((neighbors[index] == 0) & (neighbors[(index + 1) % 8] == 1)).astype(np.int16)
                for index in range(8)
            )
            if subiteration == 0:
                topology = (
                    (neighbors[0] * neighbors[2] * neighbors[4] == 0)
                    & (neighbors[2] * neighbors[4] * neighbors[6] == 0)
                )
            else:
                topology = (
                    (neighbors[0] * neighbors[2] * neighbors[6] == 0)
                    & (neighbors[0] * neighbors[4] * neighbors[6] == 0)
                )
            remove = (
                (skeleton == 1)
                & (neighbor_count >= 2)
                & (neighbor_count <= 6)
                & (transitions == 1)
                & topology
            )
            count = int(remove.sum())
            if count:
                skeleton[remove] = 0
                removed += count
        if not removed:
            break
    result = skeleton.astype(bool)
    return result if result.any() else active.copy()


NEIGHBORS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def adjacent(cell: tuple[int, int], active: set[tuple[int, int]]) -> list[tuple[int, int]]:
    row, col = cell
    return [(row + dr, col + dc) for dr, dc in NEIGHBORS if (row + dr, col + dc) in active]


def components(active_array: np.ndarray) -> list[set[tuple[int, int]]]:
    active = set(map(tuple, np.argwhere(active_array)))
    result: list[set[tuple[int, int]]] = []
    while active:
        start = min(active)
        active.remove(start)
        queue = [start]
        component = {start}
        while queue:
            current = queue.pop()
            for neighbor in adjacent(current, active):
                active.remove(neighbor)
                component.add(neighbor)
                queue.append(neighbor)
        result.append(component)
    return result


def nearest_cell(cells: Iterable[tuple[int, int]], origin: tuple[int, int]) -> tuple[int, int]:
    oy, ox = origin
    return min(cells, key=lambda item: (item[0] - oy) ** 2 + (item[1] - ox) ** 2)


def dfs_route(component: set[tuple[int, int]], start: tuple[int, int]) -> list[tuple[int, int]]:
    visited = {start}
    route = [start]
    stack: list[tuple[tuple[int, int], list[tuple[int, int]], int]] = [
        (start, sorted(adjacent(start, component)), 0)
    ]
    while stack:
        current, neighbors, index = stack[-1]
        if index >= len(neighbors):
            stack.pop()
            if stack:
                route.append(stack[-1][0])
            continue
        candidate = neighbors[index]
        stack[-1] = (current, neighbors, index + 1)
        if candidate in visited:
            continue
        visited.add(candidate)
        route.append(candidate)
        ordered = sorted(
            adjacent(candidate, component),
            key=lambda item: ((item[0] - candidate[0]) ** 2 + (item[1] - candidate[1]) ** 2, item),
        )
        stack.append((candidate, ordered, 0))
    return route


def order_components(parts: list[set[tuple[int, int]]]) -> list[tuple[set[tuple[int, int]], tuple[int, int]]]:
    remaining = list(parts)
    current = (0, 0)
    ordered: list[tuple[set[tuple[int, int]], tuple[int, int]]] = []
    while remaining:
        candidates = [(nearest_cell(part, current), part) for part in remaining]
        start, chosen = min(
            candidates,
            key=lambda pair: (
                (pair[0][0] - current[0]) ** 2 + (pair[0][1] - current[1]) ** 2,
                pair[0][0],
                pair[0][1],
            ),
        )
        ordered.append((chosen, start))
        remaining.remove(chosen)
        current = start
    return ordered


def components_in_ordered_regions(
    active_array: np.ndarray,
    regions: Sequence[Sequence[float]],
    cell: int,
) -> list[set[tuple[int, int]]]:
    """Split connected artwork at ordered object boundaries.

    A character's hair, face, clothing, and nearby props often touch in the
    thresholded route mask. Plain connected-component traversal can therefore
    leave a dense object half-finished while following a touching contour into
    another object. Ordered regions claim route cells in priority order and
    intentionally break those connections before component traversal.
    """
    if not regions:
        return components(active_array)

    rows, cols = active_array.shape
    row_centers = (np.arange(rows, dtype=np.float32) + 0.5) * cell
    col_centers = (np.arange(cols, dtype=np.float32) + 0.5) * cell
    remaining = active_array.copy()
    result: list[set[tuple[int, int]]] = []

    for region in regions:
        if len(region) != 4:
            continue
        x0, y0, x1, y1 = map(float, region)
        inside = (
            (row_centers[:, None] >= y0)
            & (row_centers[:, None] <= y1)
            & (col_centers[None, :] >= x0)
            & (col_centers[None, :] <= x1)
        )
        claimed = remaining & inside
        if claimed.any():
            result.extend(components(claimed))
        remaining &= ~inside

    if remaining.any():
        result.extend(components(remaining))
    return result


def order_components_in_regions(
    parts: list[set[tuple[int, int]]],
    regions: Sequence[Sequence[float]],
    cell: int,
) -> list[tuple[set[tuple[int, int]], tuple[int, int], int, int]]:
    """Order writing groups, text lines, and strokes in human reading order."""
    if not regions:
        return [(part, start, 0, 0) for part, start in order_components(parts)]

    buckets: list[list[set[tuple[int, int]]]] = [[] for _ in regions]
    unassigned: list[set[tuple[int, int]]] = []
    for part in parts:
        mean_row = sum(row for row, _ in part) / len(part)
        mean_col = sum(col for _, col in part) / len(part)
        x = (mean_col + 0.5) * cell
        y = (mean_row + 0.5) * cell
        region_index = next(
            (
                index
                for index, region in enumerate(regions)
                if len(region) == 4
                and float(region[0]) <= x <= float(region[2])
                and float(region[1]) <= y <= float(region[3])
            ),
            None,
        )
        if region_index is None:
            unassigned.append(part)
        else:
            buckets[region_index].append(part)

    ordered: list[tuple[set[tuple[int, int]], tuple[int, int], int, int]] = []
    for group_index, bucket in enumerate(buckets):
        # A glyph with an ascender (for example the final "b" in "p = c b")
        # may begin higher than earlier glyphs. Sorting by top-most pixel would
        # therefore write the expression right-to-left. Cluster vertically
        # overlapping strokes into text lines first, then sort every line by x.
        infos = []
        for part in bucket:
            rows = [row for row, _ in part]
            cols = [col for _, col in part]
            infos.append(
                {
                    "part": part,
                    "y0": min(rows),
                    "y1": max(rows),
                    "x0": min(cols),
                    "x1": max(cols),
                }
            )
        infos.sort(key=lambda info: ((info["y0"] + info["y1"]) / 2, info["x0"]))
        lines: list[dict[str, Any]] = []
        for info in infos:
            candidates = [
                line
                for line in lines
                if min(int(info["y1"]), int(line["y1"]))
                >= max(int(info["y0"]), int(line["y0"]))
            ]
            if candidates:
                line = min(
                    candidates,
                    key=lambda item: abs(
                        (int(info["y0"]) + int(info["y1"]))
                        - (int(item["y0"]) + int(item["y1"]))
                    ),
                )
                line["items"].append(info)
                line["y0"] = min(int(line["y0"]), int(info["y0"]))
                line["y1"] = max(int(line["y1"]), int(info["y1"]))
            else:
                lines.append({"y0": info["y0"], "y1": info["y1"], "items": [info]})

        lines.sort(key=lambda line: (int(line["y0"]), int(line["y1"])))
        for line_index, line in enumerate(lines):
            line["items"].sort(
                key=lambda info: (
                    int(info["x0"]),
                    int(info["y0"]),
                    int(info["x1"]),
                )
            )
            for info in line["items"]:
                part = info["part"]
                # Start each disconnected glyph/stroke at its upper-left edge.
                start = min(part, key=lambda item: (item[1], item[0]))
                ordered.append((part, start, group_index, line_index))

    if unassigned:
        for part, start in order_components(unassigned):
            ordered.append((part, start, len(regions), 0))
    return ordered


def propagate_content_order(
    ink_order: np.ndarray, content_active: np.ndarray
) -> tuple[np.ndarray, int, np.ndarray, np.ndarray, np.ndarray]:
    rows, cols = content_active.shape
    distance = np.full((rows, cols), np.iinfo(np.int32).max, dtype=np.int32)
    seed_order = np.full((rows, cols), np.iinfo(np.int32).max, dtype=np.int32)
    nearest_seed_row = np.full((rows, cols), -1, dtype=np.int32)
    nearest_seed_col = np.full((rows, cols), -1, dtype=np.int32)
    heap: list[tuple[int, int, int, int]] = []
    for row, col in np.argwhere(ink_order >= 0):
        order = int(ink_order[row, col])
        distance[row, col] = 0
        seed_order[row, col] = order
        nearest_seed_row[row, col] = row
        nearest_seed_col[row, col] = col
        heapq.heappush(heap, (0, order, int(row), int(col)))

    if not heap:
        order_map = np.full((rows, cols), -1, dtype=np.int32)
        distance_map = np.full((rows, cols), -1, dtype=np.int32)
        cells = list(map(tuple, np.argwhere(content_active)))
        cells.sort(key=lambda item: (item[0], item[1] if item[0] % 2 == 0 else -item[1]))
        for index, (row, col) in enumerate(cells):
            order_map[row, col] = index
            distance_map[row, col] = 0
            nearest_seed_row[row, col] = row
            nearest_seed_col[row, col] = col
        return order_map, len(cells), distance_map, nearest_seed_row, nearest_seed_col

    while heap:
        dist, order, row, col = heapq.heappop(heap)
        if dist != int(distance[row, col]) or order != int(seed_order[row, col]):
            continue
        for dr, dc in NEIGHBORS:
            nr, nc = row + dr, col + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            nd = dist + (14 if dr and dc else 10)
            if nd < distance[nr, nc] or (nd == distance[nr, nc] and order < seed_order[nr, nc]):
                distance[nr, nc] = nd
                seed_order[nr, nc] = order
                nearest_seed_row[nr, nc] = nearest_seed_row[row, col]
                nearest_seed_col[nr, nc] = nearest_seed_col[row, col]
                heapq.heappush(heap, (nd, order, nr, nc))

    cells = list(map(tuple, np.argwhere(content_active)))
    # Preserve the nearest route seed for every planning cell, not only cells
    # marked active. The renderer uses neighboring seed labels to create a
    # pixel-resolution Voronoi reveal instead of repeating square grid blocks.
    return (
        seed_order,
        len(cells),
        distance,
        nearest_seed_row,
        nearest_seed_col,
    )


def build_plan(
    rgb: np.ndarray,
    cell: int,
    ink_threshold: int,
    content_distance: float,
    hand_regions: Sequence[Sequence[float]] = (),
    object_regions: Sequence[Sequence[float]] = (),
    direct_draw: bool = False,
    fill_route_stride: int = 0,
) -> dict[str, Any]:
    height, width, _ = rgb.shape
    border = border_pixels(rgb.astype(np.float32))
    background = np.median(border, axis=0)
    rgb_float = rgb.astype(np.float32)
    gray = rgb_float[..., 0] * 0.299 + rgb_float[..., 1] * 0.587 + rgb_float[..., 2] * 0.114
    bg_gray = float(background[0] * 0.299 + background[1] * 0.587 + background[2] * 0.114)
    distance_from_bg = np.linalg.norm(rgb_float - background[None, None, :], axis=2)
    ink_mask = (gray < min(float(ink_threshold), bg_gray - 24.0)) & (distance_from_bg > 10.0)
    content_mask = distance_from_bg > content_distance

    ink_counts = grid_counts(ink_mask, cell)
    content_counts = grid_counts(content_mask, cell)
    ink_active = ink_counts >= max(2, cell // 2)
    content_active = content_counts >= max(3, cell)
    if not ink_active.any():
        ink_active = content_active.copy()
    if not content_active.any():
        raise ValueError("No drawable content detected. Use a clean off-white background and dark outlines.")

    # Isolated near-background pixels are paper grain, resampling noise, or
    # sparse print speckle—not independent strokes. Keep only pixels supported
    # by a content-active planning cell in the animated mask; compose the rest
    # as static board texture from frame one.
    content_mask &= expand_grid(content_active, cell, height, width)
    ink_mask &= expand_grid(ink_active, cell, height, width)

    route_active = thin_grid(ink_active)
    # Direct-color stills can contain broad fills whose nearest dark outline
    # is far from the marker. Add sparse routes through the actual content so
    # those fills cannot bloom after the nib has moved elsewhere.
    coverage_stride = max(0, int(fill_route_stride))
    if direct_draw and coverage_stride > 0:
        row_indices = np.indices(content_active.shape, dtype=np.int32)[0]
        coverage_tracks = content_active & (row_indices % coverage_stride == 0)
        route_active |= thin_grid(content_active) | coverage_tracks
    parts = [
        part
        for part in components_in_ordered_regions(route_active, object_regions, cell)
        if len(part) >= 1
    ]
    route_regions = object_regions if object_regions else hand_regions
    ordered_parts = order_components_in_regions(parts, route_regions, cell)
    route_seed_order = np.full(ink_active.shape, -1, dtype=np.int32)
    route: list[dict[str, Any]] = []
    order_index = 0
    for component_index, (part, start, group_index, line_index) in enumerate(ordered_parts):
        component_route = dfs_route(part, start)
        first = True
        for row, col in component_route:
            route_step = len(route)
            if route_seed_order[row, col] < 0:
                # Store the first arrival on the complete route, including
                # DFS backtracking. The hand and reveal threshold then share
                # exactly the same clock.
                route_seed_order[row, col] = route_step
                order_index += 1
            route.append(
                {
                    "x": min(width - 1, int(col * cell + cell / 2)),
                    "y": min(height - 1, int(row * cell + cell / 2)),
                    "pen_down": not first,
                    "component": component_index,
                    "group": group_index,
                    "line": line_index,
                }
            )
            first = False

    (
        ink_order,
        ink_count,
        ink_distance_map,
        ink_seed_row,
        ink_seed_col,
    ) = propagate_content_order(route_seed_order, ink_active)
    (
        content_order,
        content_count,
        content_distance_map,
        content_seed_row,
        content_seed_col,
    ) = propagate_content_order(route_seed_order, content_active)
    return {
        "background_rgb": background.tolist(),
        "ink_mask": ink_mask,
        "content_mask": content_mask,
        "ink_order": ink_order,
        "ink_distance_map": ink_distance_map,
        "ink_seed_row": ink_seed_row,
        "ink_seed_col": ink_seed_col,
        "route_seed_order": route_seed_order,
        "content_order": content_order,
        "content_distance_map": content_distance_map,
        "content_seed_row": content_seed_row,
        "content_seed_col": content_seed_col,
        "ink_count": ink_count,
        "route_seed_count": order_index,
        "content_count": content_count,
        "route_steps": len(route),
        "route": route,
        "cell": cell,
        "component_count": len(ordered_parts),
        "hand_region_count": len(hand_regions),
        "object_region_count": len(object_regions),
        "fill_route_stride": coverage_stride if direct_draw else 0,
    }


def caption_safe_top(canvas: dict[str, Any], height: int) -> int | None:
    spec = canvas.get("caption_safe_area", {})
    if spec is False or (isinstance(spec, dict) and not spec.get("enabled", True)):
        return None
    if not isinstance(spec, dict):
        raise ValueError("canvas.caption_safe_area must be an object or false")
    ratio = float(spec.get("top_ratio", DEFAULT_CAPTION_SAFE_TOP_RATIO))
    if not 0.5 <= ratio <= 0.9:
        raise ValueError("canvas.caption_safe_area.top_ratio must be between 0.5 and 0.9")
    return max(1, min(height - 1, round(height * ratio)))


def verify_caption_safe_area(
    rgb: np.ndarray,
    safe_top: int | None,
    content_distance: float,
    scene_id: str,
) -> dict[str, Any]:
    if safe_top is None:
        return {"enabled": False, "top": None, "unsafe_pixels": 0}
    background = np.median(border_pixels(rgb.astype(np.float32)), axis=0)
    distance = np.linalg.norm(rgb.astype(np.float32) - background[None, None, :], axis=2)
    unsafe_pixels = int(np.count_nonzero(distance[safe_top:, :] > content_distance))
    # Permit only a handful of resampling/noise pixels. Even a small label or
    # decorative mark must fail instead of quietly sharing the caption band.
    tolerance = 64
    if unsafe_pixels > tolerance:
        ratio = safe_top / rgb.shape[0]
        raise ValueError(
            f"{scene_id} places {unsafe_pixels} content pixels inside the caption safe area "
            f"(y >= {safe_top}, top_ratio={ratio:.3f}). Regenerate or recompose the still; "
            "keep the full lower caption band blank."
        )
    return {
        "enabled": True,
        "top": safe_top,
        "top_ratio": safe_top / rgb.shape[0],
        "unsafe_pixels": unsafe_pixels,
        "tolerance": tolerance,
    }


def expand_grid(order: np.ndarray, cell: int, height: int, width: int) -> np.ndarray:
    return np.repeat(np.repeat(order, cell, axis=0), cell, axis=1)[:height, :width]


def shift_grid(array: np.ndarray, row_offset: int, col_offset: int, fill: int = -1) -> np.ndarray:
    """Return neighbor values without the wraparound behavior of np.roll."""
    rows, cols = array.shape
    shifted = np.full(array.shape, fill, dtype=array.dtype)

    if row_offset >= 0:
        source_rows = slice(row_offset, rows)
        target_rows = slice(0, rows - row_offset)
    else:
        source_rows = slice(0, rows + row_offset)
        target_rows = slice(-row_offset, rows)

    if col_offset >= 0:
        source_cols = slice(col_offset, cols)
        target_cols = slice(0, cols - col_offset)
    else:
        source_cols = slice(0, cols + col_offset)
        target_cols = slice(-col_offset, cols)

    shifted[target_rows, target_cols] = array[source_rows, source_cols]
    return shifted


def continuous_pixel_order(
    order: np.ndarray,
    nearest_seed_row: np.ndarray,
    nearest_seed_col: np.ndarray,
    cell: int,
    height: int,
    width: int,
    spread_steps: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Map coarse route timing to pixels using nearby route-seed Voronoi cells.

    Route planning stays inexpensive on the coarse grid, while every source
    pixel chooses the geometrically nearest route seed represented by its own
    or one of the eight neighboring planning cells. Pixels then receive a
    tightly capped radial sub-delay. The returned distance map lets nib-sync
    QA reject any content assigned to a remote route seed.
    """
    pixel_y = np.arange(height, dtype=np.int32)[:, None]
    pixel_x = np.arange(width, dtype=np.int32)[None, :]
    best_distance = np.full((height, width), np.iinfo(np.int32).max, dtype=np.int32)
    best_order = np.full((height, width), -1, dtype=np.int32)

    for row_offset in (-1, 0, 1):
        for col_offset in (-1, 0, 1):
            candidate_order = expand_grid(
                shift_grid(order, row_offset, col_offset), cell, height, width
            )
            candidate_seed_row = expand_grid(
                shift_grid(nearest_seed_row, row_offset, col_offset), cell, height, width
            )
            candidate_seed_col = expand_grid(
                shift_grid(nearest_seed_col, row_offset, col_offset), cell, height, width
            )
            valid = (
                (candidate_order >= 0)
                & (candidate_seed_row >= 0)
                & (candidate_seed_col >= 0)
            )
            candidate_y = np.minimum(height - 1, candidate_seed_row * cell + cell // 2)
            candidate_x = np.minimum(width - 1, candidate_seed_col * cell + cell // 2)
            delta_y = pixel_y - candidate_y
            delta_x = pixel_x - candidate_x
            candidate_distance = delta_y * delta_y + delta_x * delta_x
            replace = valid & (
                (candidate_distance < best_distance)
                | (
                    (candidate_distance == best_distance)
                    & ((best_order < 0) | (candidate_order < best_order))
                )
            )
            best_distance[replace] = candidate_distance[replace]
            best_order[replace] = candidate_order[replace]

    if np.any(best_order < 0):
        fallback = expand_grid(order, cell, height, width)
        best_order[best_order < 0] = fallback[best_order < 0]

    smooth_order = best_order.astype(np.float32)
    if spread_steps > 0:
        normalized_distance = np.minimum(
            1.0,
            np.sqrt(best_distance.astype(np.float32)) / max(1.0, float(cell)),
        )
        radial_delay = normalized_distance * float(spread_steps)
        max_order = float(max(0, int(order.max(initial=0))))
        remaining = np.maximum(0.0, max_order - smooth_order)
        smooth_order += np.minimum(radial_delay, remaining)
    seed_distance = np.sqrt(best_distance.astype(np.float32))
    return smooth_order, seed_distance


def add_paper_texture(frame: np.ndarray, amount: float, seed: int) -> np.ndarray:
    if amount <= 0:
        return frame
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, amount, frame.shape[:2]).astype(np.float32)
    textured = frame.astype(np.float32) + noise[:, :, None]
    return np.clip(textured, 0, 255).astype(np.uint8)


def load_hand(project_base: Path, hand_spec: dict[str, Any], canvas_width: int) -> tuple[Image.Image, tuple[float, float]] | None:
    image_value = hand_spec.get("image")
    if not image_value:
        return None
    image_path = resolve(project_base, image_value)
    if not image_path.exists():
        raise FileNotFoundError(f"Hand asset not found: {image_path}")
    hand = Image.open(image_path).convert("RGBA")
    target_width = max(64, round(canvas_width * float(hand_spec.get("width_ratio", 0.19))))
    target_height = max(1, round(hand.height * target_width / hand.width))
    hand = hand.resize((target_width, target_height), Image.Resampling.LANCZOS)

    anchor = hand_spec.get("tip_anchor")
    metadata_value = hand_spec.get("metadata")
    if metadata_value:
        metadata_path = resolve(project_base, metadata_value)
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            anchor = metadata.get("tip_anchor", anchor)
    if not anchor:
        anchor = [0.023, 0.013]
    return hand, (float(anchor[0]), float(anchor[1]))


def composite_hand(
    rgb: np.ndarray,
    hand_info: tuple[Image.Image, tuple[float, float]] | None,
    point: tuple[int, int] | None,
    opacity: float,
) -> np.ndarray:
    if hand_info is None or point is None or opacity <= 0:
        return rgb
    hand, anchor = hand_info
    overlay = hand.copy()
    if opacity < 0.999:
        alpha = overlay.getchannel("A").point(lambda value: round(value * opacity))
        overlay.putalpha(alpha)
    left = round(point[0] - anchor[0] * overlay.width)
    top = round(point[1] - anchor[1] * overlay.height)
    base = Image.fromarray(rgb).convert("RGBA")
    base.alpha_composite(overlay, (left, top))
    return np.asarray(base.convert("RGB"), dtype=np.uint8)


def route_point(route: Sequence[dict[str, Any]], progress: float) -> tuple[tuple[int, int] | None, float]:
    if not route:
        return None, 0.0
    scaled = min(len(route) - 1, max(0.0, progress) * (len(route) - 1))
    index = int(scaled)
    item = route[index]
    opacity = 1.0 if item.get("pen_down", False) or index == 0 else 0.35
    return (int(item["x"]), int(item["y"])), opacity


def write_path_evidence(plan: dict[str, Any], rgb: np.ndarray, output: Path) -> None:
    preview = Image.fromarray(rgb).convert("RGBA")
    wash = Image.new("RGBA", preview.size, (255, 255, 255, 168))
    preview = Image.alpha_composite(preview, wash)
    draw = ImageDraw.Draw(preview)
    safe_top = plan.get("caption_safe_top")
    if safe_top is not None:
        draw.rectangle(
            (0, int(safe_top), preview.width - 1, preview.height - 1),
            fill=(241, 86, 86, 34),
        )
        draw.line(
            (0, int(safe_top), preview.width - 1, int(safe_top)),
            fill=(210, 52, 52, 210),
            width=3,
        )
    palette = ((232, 91, 78, 230), (25, 138, 132, 230), (225, 151, 53, 230), (74, 111, 190, 230))
    previous: tuple[int, int] | None = None
    previous_component = -1
    for item in plan["route"]:
        point = (int(item["x"]), int(item["y"]))
        component = int(item["component"])
        if previous is not None and component == previous_component and item["pen_down"]:
            draw.line((previous, point), fill=palette[component % len(palette)], width=2)
        elif component != previous_component:
            radius = 5
            draw.ellipse((point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius), fill=palette[component % len(palette)])
        previous = point
        previous_component = component
    output.parent.mkdir(parents=True, exist_ok=True)
    preview.convert("RGB").save(output, quality=92)


def compose_frame(
    source: np.ndarray,
    base: np.ndarray,
    plan: dict[str, Any],
    line_pixel_order: np.ndarray,
    color_pixel_order: np.ndarray,
    phase: str,
    progress: float,
    direct_draw: bool,
) -> np.ndarray:
    frame = base.copy()
    frame[~plan["content_mask"]] = source[~plan["content_mask"]]
    ink_mask = plan["ink_mask"]
    if phase == "draw":
        threshold = progress * max(0, plan["route_steps"] - 1)
        if direct_draw:
            eligible = plan["content_mask"] & (color_pixel_order >= 0)
            visible = eligible & (color_pixel_order <= threshold)
            frame[visible] = source[visible]
        else:
            eligible = ink_mask & (line_pixel_order >= 0)
            visible = eligible & (line_pixel_order <= threshold)
            frame[visible] = np.minimum(
                source[visible], np.array([35, 35, 35], dtype=np.uint8)
            )
    else:
        frame[ink_mask] = np.minimum(source[ink_mask], np.array([35, 35, 35], dtype=np.uint8))
        if phase == "color":
            threshold = progress * max(0, plan["route_steps"] - 1)
            eligible = plan["content_mask"] & (color_pixel_order >= 0)
            visible = eligible & (color_pixel_order <= threshold)
            frame[visible] = source[visible]
        elif phase == "hold":
            frame[plan["content_mask"]] = source[plan["content_mask"]]
    return frame


def encode_scene(
    source: np.ndarray,
    base: np.ndarray,
    plan: dict[str, Any],
    hand_info: tuple[Image.Image, tuple[float, float]] | None,
    duration: float,
    fps: int,
    draw_ratio: float,
    color_ratio: float,
    direct_draw: bool,
    write_seconds: float | None,
    hold_seconds: float,
    paper_noise: float,
    max_reveal_radius_px: float,
    output: Path,
    stage_output: Path,
) -> dict[str, Any]:
    height, width, _ = source.shape
    total_frames = max(1, round(duration * fps))
    if direct_draw:
        requested = duration - hold_seconds if write_seconds is None else write_seconds
        draw_frames = max(1, min(total_frames - 1, round(max(0.5, requested) * fps)))
        color_frames = 0
        hold_frames = total_frames - draw_frames
    else:
        hold_frames = min(total_frames - 1, max(1, round(min(hold_seconds, duration * 0.4) * fps)))
        action_frames = max(1, total_frames - hold_frames)
        ratio_sum = max(0.001, draw_ratio + color_ratio)
        draw_frames = max(1, round(action_frames * draw_ratio / ratio_sum))
        color_frames = max(1, action_frames - draw_frames)
        if draw_frames + color_frames + hold_frames > total_frames:
            hold_frames = max(0, total_frames - draw_frames - color_frames)

    steps_per_frame = max(
        1.0,
        float(max(1, plan["route_steps"] - 1)) / max(1, draw_frames - 1),
    )
    # Reveal only after the corresponding seed is reached, and finish the
    # local micro-frontier within one fifth of a frame. This removes the
    # visible trailing fade that used to continue after the nib left.
    spread_steps = steps_per_frame * 0.12
    dither_steps = steps_per_frame * 0.08
    reveal_dither = np.random.default_rng(421337).random(
        (height, width), dtype=np.float32
    )
    line_pixel_order, _line_seed_distance = continuous_pixel_order(
        plan["ink_order"],
        plan["ink_seed_row"],
        plan["ink_seed_col"],
        plan["cell"],
        height,
        width,
        spread_steps,
    )
    color_pixel_order, color_seed_distance = continuous_pixel_order(
        plan["content_order"],
        plan["content_seed_row"],
        plan["content_seed_col"],
        plan["cell"],
        height,
        width,
        spread_steps,
    )
    line_pixel_order = line_pixel_order + reveal_dither * dither_steps
    color_pixel_order = color_pixel_order + reveal_dither * dither_steps

    reveal_pixels = plan["content_mask"] & (color_pixel_order >= 0)
    reveal_distances = color_seed_distance[reveal_pixels]
    max_seed_distance = float(reveal_distances.max(initial=0.0))
    p99_seed_distance = (
        float(np.percentile(reveal_distances, 99.0)) if reveal_distances.size else 0.0
    )
    if max_seed_distance > max_reveal_radius_px:
        raise ValueError(
            f"Remote reveal detected: a content pixel is {max_seed_distance:.1f}px from its "
            f"nearest marker route seed (limit {max_reveal_radius_px:.1f}px). Lower "
            "fill_route_stride, lower grid_cell, or add a tighter object route."
        )
    ffmpeg = ffmpeg_executable()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s:v",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    if process.stdin is None:
        raise RuntimeError("Could not open FFmpeg stdin")

    stage_indices = {
        0,
        max(0, draw_frames // 2),
        max(0, draw_frames - 1),
        min(total_frames - 1, draw_frames + max(0, color_frames // 2)),
        total_frames - 1,
    }
    stages: list[Image.Image] = []
    try:
        for frame_index in range(total_frames):
            if frame_index < draw_frames:
                phase = "draw"
                progress = (frame_index + 1) / draw_frames
                hand_point, hand_opacity = route_point(plan["route"], progress)
            elif frame_index < draw_frames + color_frames:
                phase = "color"
                progress = (frame_index - draw_frames + 1) / color_frames
                hand_point, hand_opacity = route_point(plan["route"], progress)
            else:
                phase = "hold"
                progress = 1.0
                hand_point = None
                hand_opacity = 0.0

            frame = compose_frame(
                source,
                base,
                plan,
                line_pixel_order,
                color_pixel_order,
                phase,
                progress,
                direct_draw,
            )
            frame = add_paper_texture(frame, paper_noise, seed=17)
            frame = composite_hand(frame, hand_info, hand_point, hand_opacity)
            process.stdin.write(np.ascontiguousarray(frame).tobytes())
            if frame_index in stage_indices:
                stages.append(Image.fromarray(frame))
    finally:
        process.stdin.close()
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"FFmpeg failed with exit code {return_code}")

    if stages:
        thumb_width = min(480, width)
        thumb_height = round(height * thumb_width / width)
        sheet = Image.new("RGB", (thumb_width * len(stages), thumb_height), (245, 245, 245))
        for index, stage in enumerate(stages):
            thumb = stage.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (index * thumb_width, 0))
        stage_output.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(stage_output, quality=92)

    return {
        "frames": total_frames,
        "duration": total_frames / fps,
        "draw_frames": draw_frames,
        "color_frames": color_frames,
        "hold_frames": hold_frames,
        "components": plan["component_count"],
        "ink_cells": plan["ink_count"],
        "route_seed_cells": plan["route_seed_count"],
        "content_cells": plan["content_count"],
        "route_steps": plan["route_steps"],
        "hand_regions": plan["hand_region_count"],
        "object_regions": plan["object_region_count"],
        "direct_draw": direct_draw,
        "fill_route_stride": plan["fill_route_stride"],
        "reveal_sync": {
            "mode": "nib-locked",
            "max_seed_distance_px": round(max_seed_distance, 3),
            "p99_seed_distance_px": round(p99_seed_distance, 3),
            "limit_px": round(max_reveal_radius_px, 3),
            "max_temporal_lag_frames": 0.2,
        },
        "write_seconds": draw_frames / fps,
    }


def srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def concat_clips(clips: list[Path], output: Path) -> None:
    if not clips:
        raise ValueError("No clips to concatenate")
    concat_file = output.parent / "clips.ffconcat"
    lines = ["ffconcat version 1.0"]
    for clip in clips:
        escaped = str(clip.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    command = [
        ffmpeg_executable(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True)


def render_project(args: argparse.Namespace) -> int:
    project_path = Path(args.project).expanduser().resolve()
    project_base = project_path.parent
    project = json.loads(project_path.read_text(encoding="utf-8"))
    if int(project.get("version", 0)) != 1:
        raise ValueError("Only project schema version 1 is supported")
    visual_style = project.get("visual_style", "editorial-character")
    if visual_style not in VISUAL_STYLES:
        raise ValueError(
            f"Unsupported visual_style {visual_style!r}; expected one of {VISUAL_STYLES}"
        )
    if visual_style == "reference-adapted":
        reference_value = project.get("style_reference")
        if not reference_value or not resolve(project_base, reference_value).is_file():
            raise FileNotFoundError(
                "reference-adapted project requires an existing style_reference"
            )
        profile = project.get("style_profile")
        required_traits = {
            "medium",
            "line",
            "palette",
            "texture",
            "shape_language",
            "shading",
            "density",
            "composition",
        }
        if not isinstance(profile, dict) or not required_traits.issubset(profile):
            raise ValueError(
                "reference-adapted project requires a complete style_profile"
            )
        if "TODO" in json.dumps(profile, ensure_ascii=False):
            raise ValueError("Resolve every TODO in style_profile before rendering")

    canvas = project["canvas"]
    width = int(canvas["width"])
    height = int(canvas["height"])
    fps = int(canvas.get("fps", 24))
    background = parse_color(canvas.get("background", "#fbf8ef"))
    paper = np.full((height, width, 3), background, dtype=np.uint8)
    safe_top = caption_safe_top(canvas, height)
    style = project.get("style", {})
    hand_info = None if args.no_hand else load_hand(project_base, project.get("hand", {}), width)

    output_dir = resolve(project_base, args.output_dir or "output")
    clips_dir = output_dir / "clips"
    evidence_dir = output_dir / "evidence"
    output_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, Any]] = []
    clips: list[Path] = []
    srt_entries: list[str] = []
    cursor = 0.0

    for index, scene in enumerate(project["scenes"], start=1):
        scene_id = scene.get("id", f"scene-{index:03d}")
        image_path = resolve(project_base, scene["image"])
        if not image_path.exists():
            raise FileNotFoundError(f"Scene image not found: {image_path}")
        duration = float(scene.get("duration") or estimate_duration(scene["narration"], float(project.get("speech_rate_cps", 4.2))))
        source = fit_to_canvas(image_path, width, height, background)
        base_value = scene.get("base_image")
        draw_value = scene.get("draw_image")
        base = (
            fit_to_canvas(resolve(project_base, base_value), width, height, background)
            if base_value
            else paper
        )
        draw_source = (
            fit_to_canvas(resolve(project_base, draw_value), width, height, background)
            if draw_value
            else source
        )
        hand_regions = scene.get("hand_regions", [])
        object_regions = scene.get("object_regions", [])
        content_distance = float(scene.get("content_distance", style.get("content_distance", 12)))
        direct_draw = bool(scene.get("direct_draw", style.get("direct_draw", False)))
        fill_route_stride = int(
            scene.get("fill_route_stride", style.get("fill_route_stride", 3 if direct_draw else 0))
        )
        max_reveal_radius_px = float(
            scene.get(
                "max_reveal_radius_px",
                style.get("max_reveal_radius_px", max(22, round(width * 0.014))),
            )
        )
        safe_area_report = verify_caption_safe_area(
            source,
            safe_top,
            content_distance,
            scene_id,
        )
        for region_name, regions in (("hand_regions", hand_regions), ("object_regions", object_regions)):
            if safe_top is not None:
                for region_index, region in enumerate(regions):
                    if len(region) == 4 and float(region[3]) > safe_top:
                        raise ValueError(
                            f"{scene_id} {region_name}[{region_index}] enters the caption safe area; "
                            f"its bottom must be <= {safe_top}."
                        )
        plan = build_plan(
            draw_source,
            int(scene.get("grid_cell", style.get("grid_cell", max(4, width // 240)))),
            int(scene.get("ink_threshold", style.get("ink_threshold", 170))),
            content_distance,
            hand_regions,
            object_regions,
            direct_draw,
            fill_route_stride,
        )
        plan["caption_safe_top"] = safe_top
        if safe_top is not None and any(int(point["y"]) >= safe_top for point in plan["route"]):
            raise ValueError(
                f"{scene_id} has a drawing route inside the caption safe area; recompose the route source."
            )
        clip_path = clips_dir / f"{scene_id}.mp4"
        path_preview = evidence_dir / f"{scene_id}-path.jpg"
        motion_stages = evidence_dir / f"{scene_id}-stages.jpg"
        route_json = evidence_dir / f"{scene_id}-route.json"
        write_path_evidence(plan, source, path_preview)
        route_json.parent.mkdir(parents=True, exist_ok=True)
        route_json.write_text(
            json.dumps(
                {
                    "cell": plan["cell"],
                    "component_count": plan["component_count"],
                    "ink_cells": plan["ink_count"],
                    "route_seed_cells": plan["route_seed_count"],
                    "content_cells": plan["content_count"],
                    "route_steps": plan["route_steps"],
                    "hand_region_count": plan["hand_region_count"],
                    "object_region_count": plan["object_region_count"],
                    "fill_route_stride": plan["fill_route_stride"],
                    "caption_safe_area": safe_area_report,
                    "route": plan["route"],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        report = encode_scene(
            source,
            base,
            plan,
            hand_info,
            duration,
            fps,
            float(scene.get("draw_ratio", style.get("draw_ratio", 0.67))),
            float(scene.get("color_ratio", style.get("color_ratio", 0.33))),
            direct_draw,
            (
                float(scene.get("write_seconds", style.get("write_seconds")))
                if scene.get("write_seconds", style.get("write_seconds")) is not None
                else None
            ),
            float(scene.get("hold_seconds", style.get("hold_seconds", 1.2))),
            float(scene.get("paper_noise", style.get("paper_noise", 2.2))),
            max_reveal_radius_px,
            clip_path,
            motion_stages,
        )
        report.update(
            {
                "id": scene_id,
                "image": str(image_path),
                "base_image": str(resolve(project_base, base_value)) if base_value else None,
                "draw_image": str(resolve(project_base, draw_value)) if draw_value else None,
                "clip": str(clip_path),
                "path_preview": str(path_preview),
                "motion_stages": str(motion_stages),
                "caption_safe_area": safe_area_report,
            }
        )
        reports.append(report)
        clips.append(clip_path)
        end = cursor + report["duration"]
        srt_entries.append(
            f"{index}\n{srt_timestamp(cursor)} --> {srt_timestamp(end)}\n{scene['narration']}\n"
        )
        cursor = end
        print(f"Rendered {scene_id}: {report['duration']:.2f}s, {report['components']} paths")

    final_video = output_dir / (args.name or "whiteboard-video.mp4")
    concat_clips(clips, final_video)
    (output_dir / "narration.srt").write_text("\n".join(srt_entries), encoding="utf-8")
    final_report = {
        "project": str(project_path),
        "video": str(final_video),
        "visual_style": visual_style,
        "duration": cursor,
        "resolution": [width, height],
        "fps": fps,
        "caption_safe_area": {
            "enabled": safe_top is not None,
            "top": safe_top,
            "top_ratio": (safe_top / height) if safe_top is not None else None,
        },
        "audio_tracks": 0,
        "scenes": reports,
    }
    (output_dir / "render-report.json").write_text(
        json.dumps(final_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Final video: {final_video}")
    print(f"Estimated subtitles: {output_dir / 'narration.srt'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-project", help="Create a timed project skeleton from narration text")
    create.add_argument("--input", required=True, help="UTF-8 narration text file, or - for stdin")
    create.add_argument("--output", default="storyboard.json")
    create.add_argument("--title", default="Whiteboard narration")
    create.add_argument("--width", type=int, default=1920)
    create.add_argument("--height", type=int, default=1080)
    create.add_argument("--fps", type=int, default=24)
    create.add_argument("--speech-rate", type=float, default=4.2, help="Estimated Chinese characters per second")
    create.add_argument(
        "--narrator-gender",
        choices=("male", "female"),
        help="Speaking narrator gender used later for default TTS voice selection",
    )
    create.add_argument("--target-chars", type=int, default=42)
    create.add_argument("--max-chars", type=int, default=62)
    create.add_argument(
        "--visual-style",
        choices=VISUAL_STYLES,
        help="Visual style; inferred as reference-adapted when --style-reference is supplied",
    )
    create.add_argument(
        "--style-reference",
        help="Reference image copied into project assets for original trait-level style adaptation",
    )
    create.set_defaults(func=create_project)

    hand = subparsers.add_parser("prepare-hand", help="Remove a flat chroma key and record marker-tip anchor")
    hand.add_argument("--input", required=True)
    hand.add_argument("--output", required=True)
    hand.add_argument("--metadata")
    hand.add_argument("--tip-x", type=float, default=0.28, help="Marker tip x on the source canvas, normalized")
    hand.add_argument("--tip-y", type=float, default=0.05, help="Marker tip y on the source canvas, normalized")
    hand.add_argument("--transparent-threshold", type=float, default=18.0)
    hand.add_argument("--opaque-threshold", type=float, default=105.0)
    hand.add_argument("--edge-contract", type=int, default=1)
    hand.add_argument("--margin", type=int, default=8)
    hand.set_defaults(func=prepare_hand)

    render = subparsers.add_parser("render", help="Render all scenes and concatenate the final MP4")
    render.add_argument("project", help="Project JSON path")
    render.add_argument("--output-dir")
    render.add_argument("--name", default="whiteboard-video.mp4")
    render.add_argument("--no-hand", action="store_true")
    render.set_defaults(func=render_project)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Synthesize Edge TTS, derive timed subtitles, and finish whiteboard videos."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


TICKS_PER_SECOND = 10_000_000
SPOKEN_RE = re.compile(r"[\u3400-\u9fffA-Za-z0-9]")
PUNCTUATION = set("，。！？!?；;：:\n")
DEFAULT_VOICES = {
    "male": "zh-CN-YunxiNeural",
    "female": "zh-CN-XiaoxiaoNeural",
}


def resolve_narrator_gender(project: dict[str, Any], cli_gender: str | None) -> str:
    gender = cli_gender or project.get("narrator_gender")
    if gender not in DEFAULT_VOICES:
        raise ValueError(
            "Set root-level narrator_gender to 'male' or 'female', or pass "
            "--narrator-gender before synthesizing TTS"
        )
    return str(gender)


def resolve_voice(cli_voice: str | None, narrator_gender: str) -> str:
    return cli_voice or DEFAULT_VOICES[narrator_gender]


def ffmpeg_executable() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("Install imageio-ffmpeg or provide ffmpeg on PATH") from exc


def resolve(base: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def decoded_duration(path: Path) -> float:
    command = [
        ffmpeg_executable(),
        "-v",
        "error",
        "-i",
        str(path),
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        "24000",
        "-",
    ]
    completed = subprocess.run(command, check=True, stdout=subprocess.PIPE)
    return len(completed.stdout) / (2 * 24_000)


def caption_chunks(
    text: str,
    boundaries: Sequence[dict[str, Any]] | None = None,
    target: int = 16,
    maximum: int = 22,
    minimum: int = 8,
) -> list[str]:
    normalized = "".join(text.split())
    if not normalized:
        return []
    breakpoints: set[int] = set()
    punctuation_breaks: set[int] = set()
    spoken_targets: list[int] = []
    cumulative = 0
    for boundary in boundaries or []:
        cumulative += max(1, spoken_length(str(boundary["text"])))
        spoken_targets.append(cumulative)
    spoken_cursor = 0
    target_index = 0
    for index, character in enumerate(normalized):
        if SPOKEN_RE.match(character):
            spoken_cursor += 1
        while target_index < len(spoken_targets) and spoken_cursor >= spoken_targets[target_index]:
            endpoint = index + 1
            while endpoint < len(normalized) and normalized[endpoint] in PUNCTUATION:
                endpoint += 1
            breakpoints.add(endpoint)
            if endpoint > index + 1:
                punctuation_breaks.add(endpoint)
            target_index += 1
        if character in PUNCTUATION:
            breakpoints.add(index + 1)
            punctuation_breaks.add(index + 1)
    breakpoints.add(len(normalized))

    chunks: list[str] = []
    cursor = 0
    while cursor < len(normalized):
        remaining = len(normalized) - cursor
        if remaining <= maximum:
            chunks.append(normalized[cursor:])
            break
        low = min(len(normalized), cursor + minimum)
        high = min(len(normalized), cursor + maximum)
        candidates = [point for point in breakpoints if low <= point <= high]
        marked = [point for point in candidates if point in punctuation_breaks]
        if marked:
            endpoint = min(marked, key=lambda value: (abs(value - (cursor + target)), -value))
        elif candidates:
            endpoint = min(candidates, key=lambda value: (abs(value - (cursor + target)), -value))
        else:
            endpoint = high
        chunks.append(normalized[cursor:endpoint])
        cursor = endpoint
    if len(chunks) > 1 and len(chunks[-1]) < minimum:
        tail = chunks.pop()
        chunks[-1] += tail
    return chunks


def spoken_length(text: str) -> int:
    return len(SPOKEN_RE.findall(text))


def timed_captions(text: str, boundaries: Sequence[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    chunks = caption_chunks(text, boundaries)
    if not chunks:
        return []
    if not boundaries:
        unit = duration / len(chunks)
        return [
            {"start": index * unit, "end": min(duration, (index + 1) * unit), "text": chunk}
            for index, chunk in enumerate(chunks)
        ]

    token_spans: list[tuple[int, int, float, float]] = []
    spoken_cursor = 0
    for boundary in boundaries:
        length = max(1, spoken_length(str(boundary["text"])))
        token_spans.append(
            (
                spoken_cursor,
                spoken_cursor + length,
                float(boundary["offset"]) / TICKS_PER_SECOND,
                (float(boundary["offset"]) + float(boundary["duration"])) / TICKS_PER_SECOND,
            )
        )
        spoken_cursor += length

    captions: list[dict[str, Any]] = []
    caption_cursor = 0
    for chunk in chunks:
        length = spoken_length(chunk)
        wanted_start = caption_cursor
        wanted_end = caption_cursor + length
        overlapping = [span for span in token_spans if span[1] > wanted_start and span[0] < wanted_end]
        if overlapping:
            start = overlapping[0][2]
            end = overlapping[-1][3]
        else:
            start = captions[-1]["end"] if captions else 0.0
            end = min(duration, start + max(0.8, duration / len(chunks)))
        captions.append({"start": start, "end": min(duration, end), "text": chunk})
        caption_cursor = wanted_end

    for index, caption in enumerate(captions):
        next_start = captions[index + 1]["start"] if index + 1 < len(captions) else duration
        caption["end"] = max(caption["start"] + 0.65, min(duration, next_start - 0.04))
    return captions


async def synthesize_scene(
    text: str,
    media_path: Path,
    voice: str,
    rate: str,
    volume: str,
    pitch: str,
) -> list[dict[str, Any]]:
    try:
        import edge_tts  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Install edge-tts in the active project environment") from exc

    communicate = edge_tts.Communicate(
        text,
        voice=voice,
        rate=rate,
        volume=volume,
        pitch=pitch,
        boundary="WordBoundary",
    )
    boundaries: list[dict[str, Any]] = []
    media_path.parent.mkdir(parents=True, exist_ok=True)
    with media_path.open("wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append(
                    {
                        "offset": int(chunk["offset"]),
                        "duration": int(chunk["duration"]),
                        "text": str(chunk["text"]),
                    }
                )
    return boundaries


def combine_audio(scene_audio: Sequence[Path], paddings: Sequence[float], output: Path, duration: float) -> None:
    command = [ffmpeg_executable(), "-y", "-loglevel", "error"]
    for path in scene_audio:
        command.extend(["-i", str(path)])
    filters: list[str] = []
    labels: list[str] = []
    for index, padding in enumerate(paddings):
        label = f"a{index}"
        filters.append(f"[{index}:a]apad=pad_dur={max(0.0, padding):.6f}[{label}]")
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}concat=n={len(scene_audio)}:v=0:a=1[outa]")
    output.parent.mkdir(parents=True, exist_ok=True)
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[outa]",
            "-t",
            f"{duration:.6f}",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            str(output),
        ]
    )
    subprocess.run(command, check=True)


def write_srt(captions: Sequence[dict[str, Any]], output: Path) -> None:
    entries = []
    for index, caption in enumerate(captions, start=1):
        entries.append(
            f"{index}\n{srt_timestamp(float(caption['start']))} --> "
            f"{srt_timestamp(float(caption['end']))}\n{caption['text']}\n"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(entries), encoding="utf-8")


async def synthesize_project_async(args: argparse.Namespace) -> int:
    project_path = Path(args.project).expanduser().resolve()
    project_base = project_path.parent
    project = json.loads(project_path.read_text(encoding="utf-8"))
    fps = int(project["canvas"].get("fps", 24))
    audio_dir = resolve(project_base, args.audio_dir or "audio")
    scenes_dir = audio_dir / "scenes"

    narrator_gender = resolve_narrator_gender(project, args.narrator_gender)
    project["narrator_gender"] = narrator_gender
    voice = resolve_voice(args.voice, narrator_gender)
    rate = args.rate
    volume = args.volume
    pitch = args.pitch
    all_captions: list[dict[str, Any]] = []
    scene_audio: list[Path] = []
    paddings: list[float] = []
    scene_reports: list[dict[str, Any]] = []
    global_cursor = 0.0

    for index, scene in enumerate(project["scenes"], start=1):
        scene_id = scene.get("id", f"scene-{index:03d}")
        media_path = scenes_dir / f"{scene_id}.mp3"
        boundaries = await synthesize_scene(scene["narration"], media_path, voice, rate, volume, pitch)
        raw_duration = decoded_duration(media_path)
        frame_duration = math.ceil(raw_duration * fps) / fps
        padding = max(0.0, frame_duration - raw_duration)
        local_captions = timed_captions(scene["narration"], boundaries, raw_duration)
        for caption in local_captions:
            all_captions.append(
                {
                    "start": global_cursor + float(caption["start"]),
                    "end": global_cursor + float(caption["end"]),
                    "text": caption["text"],
                    "scene": scene_id,
                }
            )

        scene["duration"] = round(frame_duration, 6)
        scene["audio"] = str(media_path.relative_to(project_base))
        scene["audio_duration"] = round(raw_duration, 6)
        scene_audio.append(media_path)
        paddings.append(padding)
        scene_reports.append(
            {
                "id": scene_id,
                "audio": str(media_path),
                "audio_duration": raw_duration,
                "timeline_duration": frame_duration,
                "padding": padding,
                "word_boundaries": len(boundaries),
                "captions": len(local_captions),
            }
        )
        global_cursor += frame_duration
        print(f"Synthesized {scene_id}: {raw_duration:.3f}s -> {frame_duration:.3f}s timeline")

    audio_path = audio_dir / "narration.m4a"
    subtitle_path = audio_dir / "narration.srt"
    metadata_path = audio_dir / "tts-report.json"
    combine_audio(scene_audio, paddings, audio_path, global_cursor)
    write_srt(all_captions, subtitle_path)
    project["tts"] = {
        "engine": "Microsoft Edge online TTS via edge-tts",
        "narrator_gender": narrator_gender,
        "voice": voice,
        "rate": rate,
        "volume": volume,
        "pitch": pitch,
        "audio": str(audio_path.relative_to(project_base)),
        "subtitles": str(subtitle_path.relative_to(project_base)),
        "timing_basis": "Edge WordBoundary metadata plus decoded per-scene audio duration",
    }
    output_project = resolve(project_base, args.output_project or project_path)
    output_project.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metadata_path.write_text(
        json.dumps(
            {
                "narrator_gender": narrator_gender,
                "voice": voice,
                "rate": rate,
                "volume": volume,
                "pitch": pitch,
                "duration": global_cursor,
                "audio": str(audio_path),
                "subtitles": str(subtitle_path),
                "scenes": scene_reports,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Narration audio: {audio_path}")
    print(f"Timed subtitles: {subtitle_path}")
    print(f"Updated project: {output_project}")
    return 0


def synthesize_project(args: argparse.Namespace) -> int:
    return asyncio.run(synthesize_project_async(args))


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def finish_video(args: argparse.Namespace) -> int:
    project_path = Path(args.project).expanduser().resolve()
    project_base = project_path.parent
    project = json.loads(project_path.read_text(encoding="utf-8"))
    tts = project.get("tts")
    if not tts:
        raise ValueError("Project has no tts block; run synthesize first")
    video = resolve(project_base, args.video or "output/whiteboard-video.mp4")
    audio = resolve(project_base, args.audio or tts["audio"])
    subtitles = resolve(project_base, args.subtitles or tts["subtitles"])
    output = resolve(project_base, args.output or "output/whiteboard-video-tts-subtitles.mp4")
    for path in (video, audio, subtitles):
        if not path.exists():
            raise FileNotFoundError(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    canvas_height = int(project["canvas"]["height"])
    # libass scales SRT style units from its default 288-line script space.
    # At 1080p, 17 units render near 64 physical pixels.
    font_size = args.font_size or max(14, round(canvas_height * 0.016))
    margin_v = args.margin_v or max(12, round(canvas_height * 0.018))
    if getattr(args, "subtitle_box", False):
        border_style = "BorderStyle=3,BackColour=&H88000000,Outline=1,Shadow=0"
    else:
        # BorderStyle=1 renders only a glyph outline. Keep BackColour fully
        # transparent so captions never create a black rectangle.
        border_style = "BorderStyle=1,BackColour=&HFF000000,Outline=1,Shadow=0"
    style = (
        f"FontName={args.font_name},FontSize={font_size},"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00191919,"
        f"{border_style},Alignment=2,MarginL=80,MarginR=80,MarginV={margin_v}"
    )
    subtitle_filter = (
        f"subtitles=filename='{escape_filter_path(subtitles)}':"
        f"fontsdir='{escape_filter_path(Path(args.fonts_dir))}':"
        f"force_style='{style}'"
    )
    command = [
        ffmpeg_executable(),
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-vf",
        subtitle_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        "-shortest",
        str(output),
    ]
    subprocess.run(command, check=True)
    sidecar = output.parent / "narration-tts.srt"
    shutil.copy2(subtitles, sidecar)
    duration = sum(float(scene["duration"]) for scene in project["scenes"])
    report = {
        "project": str(project_path),
        "video": str(output),
        "duration": duration,
        "resolution": [int(project["canvas"]["width"]), canvas_height],
        "fps": int(project["canvas"].get("fps", 24)),
        "video_codec": "H.264",
        "audio_codec": "AAC",
        "audio_tracks": 1,
        "narrator_gender": tts.get("narrator_gender") or project.get("narrator_gender"),
        "voice": tts.get("voice"),
        "timing_basis": tts.get("timing_basis"),
        "embedded_subtitles": True,
        "subtitle_sidecar": str(sidecar),
    }
    (output.parent / "final-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Finished video: {output}")
    print(f"Subtitle sidecar: {sidecar}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    synthesize = subparsers.add_parser("synthesize", help="Create timed Edge TTS audio and subtitles")
    synthesize.add_argument("project")
    synthesize.add_argument("--output-project")
    synthesize.add_argument("--audio-dir")
    synthesize.add_argument(
        "--narrator-gender",
        choices=sorted(DEFAULT_VOICES),
        help="Speaking narrator gender; overrides storyboard narrator_gender",
    )
    synthesize.add_argument(
        "--voice",
        help="Explicit Edge TTS voice override; otherwise selected from narrator_gender",
    )
    synthesize.add_argument("--rate", default="+0%")
    synthesize.add_argument("--volume", default="+0%")
    synthesize.add_argument("--pitch", default="+0Hz")
    synthesize.set_defaults(func=synthesize_project)

    finish = subparsers.add_parser("finish", help="Mux narration and burn subtitles into a rendered video")
    finish.add_argument("project")
    finish.add_argument("--video")
    finish.add_argument("--audio")
    finish.add_argument("--subtitles")
    finish.add_argument("--output")
    finish.add_argument("--font-name", default="Heiti SC")
    finish.add_argument("--fonts-dir", default="/System/Library/Fonts")
    finish.add_argument("--font-size", type=int)
    finish.add_argument("--margin-v", type=int)
    finish.add_argument(
        "--subtitle-box",
        action="store_true",
        help="Opt in to the legacy translucent black subtitle box",
    )
    finish.set_defaults(func=finish_video)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

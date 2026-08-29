# Project schema v1

All relative paths resolve from the directory containing `storyboard.json`.

## Contents

- Complete example
- Fields
- Visual style
- Canvas
- Style
- Hand
- Scene
- Timing rules without SRT

## Complete example

```json
{
  "version": 1,
  "title": "咖啡渍为什么越擦越大",
  "visual_style": "reference-adapted",
  "style_reference": "assets/style-reference.png",
  "style_profile": {
    "medium": "slightly dry felt-tip marker with sparse flat color",
    "line": "dark uneven outlines with subtle pressure variation",
    "palette": ["#fbf8ef", "#202426", "#d9865b", "#76aaa0"],
    "texture": "fine paper grain and occasional imperfect fill edges",
    "shape_language": "rounded simplified subjects with angular diagram accents",
    "shading": "minimal flat shadow shapes",
    "density": "2-5 large subjects with generous whitespace",
    "composition": "one dominant relationship with a clear directional flow"
  },
  "narration": "出门前，衣服上溅了一滴咖啡。很多人第一反应是来回擦，但这会让污渍扩散。",
  "narrator_gender": "female",
  "speech_rate_cps": 4.2,
  "canvas": {
    "width": 1920,
    "height": 1080,
    "fps": 24,
    "background": "#fbf8ef",
    "caption_safe_area": {
      "enabled": true,
      "top_ratio": 0.76,
      "bottom_ratio": 1.0
    }
  },
  "style": {
    "grid_cell": 8,
    "ink_threshold": 170,
    "content_distance": 12,
    "draw_ratio": 0.67,
    "color_ratio": 0.33,
    "direct_draw": false,
    "fill_route_stride": 3,
    "max_reveal_radius_px": 27,
    "hold_seconds": 1.2,
    "paper_noise": 2.2
  },
  "hand": {
    "image": "assets/hand.png",
    "metadata": "assets/hand.json",
    "width_ratio": 0.19
  },
  "tts": {
    "engine": "edge-tts",
    "provider": "online",
    "narrator_gender": "female",
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": "+0%",
    "volume": "+0%",
    "pitch": "+0Hz",
    "audio": "audio/narration.m4a",
    "subtitles": "audio/narration.srt",
    "timing_basis": "Edge WordBoundary metadata plus decoded per-scene audio duration",
    "voice_reference": null
  },
  "scenes": [
    {
      "id": "scene-001",
      "narration": "出门前，衣服上溅了一滴咖啡。",
      "duration": 6.4,
      "audio": "audio/scenes/scene-001.mp3",
      "audio_duration": 6.37,
      "visual_prompt": "A clean shirt receives one falling coffee drop; a small starburst marks the impact.",
      "image": "scenes/scene-001.png"
    },
    {
      "id": "scene-002",
      "narration": "很多人第一反应是来回擦，但这会让污渍扩散。",
      "duration": 8.1,
      "visual_prompt": "A cloth rubs a small stain into a visibly larger stain, connected by one clear arrow.",
      "image": "scenes/scene-002.png",
      "grid_cell": 10,
      "hold_seconds": 1.5
    }
  ]
}
```

## Fields

### Root

- `version`: Require integer `1`.
- `title`: Use a short project label.
- `visual_style`: Use `reference-adapted` when a reference image is supplied; otherwise use `editorial-character`.
- `style_reference`: For `reference-adapted`, point to a project-local copy of the supplied reference image.
- `style_profile`: For `reference-adapted`, record abstract medium, line, palette, texture, shape-language, shading, density, and composition traits. Do not record instructions to reproduce protected characters, logos, signature objects, exact poses, or layouts.
- `narration`: Preserve the complete supplied text.
- `narrator_gender`: Require `male` or `female` whenever TTS is requested. For first-person narration, match the speaking protagonist; for third-person narration without a distinct narrator, match the main protagonist. Do not infer it from secondary characters. The default voice map is `male` → `zh-CN-YunxiNeural`, `female` → `zh-CN-XiaoxiaoNeural`.
- `speech_rate_cps`: Estimate Mandarin timing in spoken characters per second. Default to `4.2`.
- `canvas`: Define one shared output canvas for all scenes.
- `style`: Define route-detection and timing defaults.
- `hand`: Define the transparent marker-hand overlay.
- `tts`: Records the selected TTS pipeline, resolved narrator gender, voice or non-secret voice-reference label, and authoritative audio/subtitle paths. The bundled `edge_tts_pipeline.py synthesize` command writes the Edge form; a local IndexTTS or other voice-clone runner should write the equivalent fields.
- `scenes`: List scenes in final playback order.

### Visual style

- `reference-adapted`: Original scene art guided only by transferable craft traits extracted from `style_reference`.
- `editorial-character`: Friendly editorial explainer; may use sparse people, objects, environments, and visual metaphors.

The renderer does not inspect or copy the reference. These fields guide ImageGen and visual QA only. Keep `style_profile` stable across scenes and create new subjects and compositions for every narration beat.

### Canvas

- `width`, `height`: Use even dimensions. Prefer `1920×1080` or `1080×1920`.
- `fps`: Default to `24`.
- `background`: Use a six-digit hex color close to the generated still background.
- `caption_safe_area`: Reserve a full-width caption-only band before composing images. Default to `enabled: true`, `top_ratio: 0.76`, and `bottom_ratio: 1.0`. All scene marks and route points must remain above it. Set `enabled: false` only for a deliverable with no subtitles.

### Style

- `grid_cell`: Set the path-planning cell size in output pixels. Start near `width / 240` (`8` at 1920 px); use `6` for dense hair or print-textured fills. It controls route density only; the renderer must still reveal the original artwork at pixel resolution using nearest route seeds, never as repeated square cells.
- `ink_threshold`: Treat darker pixels as drawable ink. Start at `170`; lower it when colored fills become false ink, raise it when gray outlines disappear.
- `content_distance`: Minimum RGB distance from the sampled border background. Raise it when paper noise activates empty cells; lower it when pale fills fail to reveal.
- `draw_ratio`, `color_ratio`: Divide the non-hold time. Use `2:1` by default.
- `direct_draw`: Reveal original stroke color in one marker pass and do not retrace during a color phase. Prefer `true` for natural single-pass marker writing.
- `fill_route_stride`: With `direct_draw`, add one horizontal content-coverage track every N planning rows so broad fills have a real nearby nib path. Default to `3`; lower it for finer tracking and raise it only after `reveal_sync` still passes.
- `max_reveal_radius_px`: Hard maximum distance from any animated source pixel to its assigned marker route seed. Start near `width × 0.014` (`27` at 1920 px); use about `18` with a 6 px grid. The renderer rejects the scene when this is exceeded; repair route coverage instead of loosening the limit.
- `write_seconds`: Optional cap on visible hand-writing time when `direct_draw` is true. The remaining scene time becomes a hand-free completed hold.
- `hold_seconds`: Reserve a hand-free final lock. Keep at least `0.8` seconds.
- `paper_noise`: Add subtle deterministic texture after compositing. Set `0` for perfectly clean white.

### Hand

- `image`: Point to an RGBA PNG.
- `metadata`: Point to the JSON emitted by `prepare-hand`; it supplies `tip_anchor`.
- `tip_anchor`: Optionally provide `[x, y]` normalized inside the cropped PNG.
- `width_ratio`: Size the hand relative to canvas width. Start at `0.19` for the bundled bottom-entry portrait hand. Verify that its forearm reaches the bottom edge without obscuring most of the scene.

Do not change hand fields merely because `visual_style` changes. Reference adaptation affects scene art, not the hand anchor, route ordering, reveal behavior, or bottom-entry pose.

### Scene

- `id`: Use stable zero-padded names such as `scene-001`.
- `narration`: Preserve the complete spoken clause for this scene.
- `duration`: Store estimated seconds before synthesis. After the selected TTS pipeline, store the frame-aligned timeline duration.
- `audio`: Optional per-scene TTS media path.
- `audio_duration`: Optional decoded source-audio length before frame padding.
- `visual_prompt`: Describe what ImageGen should draw. Never leave `TODO` at render time.
- `image`: Point to the approved generated still.
- `base_image`: Optional completed static skeleton visible from frame zero. Place titles, panels, axes, grids, ticks, diagram structure, and supporting labels here when they should not be animated.
- `draw_image`: Optional clean route-source image containing only dynamic marker strokes on the canvas background. The renderer reveals corresponding pixels from `image`, not the background of this layer.
- `hand_regions`: Optional ordered list of `[x1, y1, x2, y2]` canvas rectangles. Finish every connected stroke in one region before moving to the next.
- `object_regions`: Optional ordered list of `[x1, y1, x2, y2]` canvas rectangles for character and object illustrations. Earlier boxes have priority where boxes overlap. The renderer must split touching route components at these boundaries and complete every component in one region before entering the next. For characters, put dense hair first, the remainder of that character second, and later characters or props afterward.
- `grid_cell`, `ink_threshold`, `content_distance`, `draw_ratio`, `color_ratio`, `direct_draw`, `fill_route_stride`, `max_reveal_radius_px`, `write_seconds`, `hold_seconds`, `paper_noise`: Override shared style values only when a scene needs repair.

For layered scenes, require `image = base_image + draw_image strokes` at identical pixel coordinates. Keep each `hand_regions` rectangle large enough to contain its complete word, equation, or intentional multi-line calculation, but small enough that unrelated writing cannot enter the group.

The renderer treats the caption safe area as a hard constraint. It rejects a final scene image with meaningful foreground pixels in the band, any `hand_regions` or `object_regions` rectangle whose bottom enters the band, and any computed route point inside the band.

For character scenes with dense black hair or touching objects, use `object_regions` instead of relying on raw connected-component order. Cover every priority object completely; any unassigned route cells are drawn after all declared regions.

## Timing ownership

Before TTS, `speech_rate_cps` supplies only an edit estimate. After synthesis, the final decoded audio and its matching timing artifact are authoritative. For Edge TTS, these are the fields written by `edge_tts_pipeline.py synthesize`; for local IndexTTS or another runner, record the equivalent paths and timing basis in `tts`. See [tts-and-subtitles.md](tts-and-subtitles.md) for timing and subtitle rules.

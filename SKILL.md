---
name: hand-drawn-follow-animation
description: Turn Chinese narration and an optional visual reference into an original hand-drawn follow-along animation with ImageGen scene art, deterministic nib-locked drawing motion, a user-supplied or gender-matched TTS voice, timed Chinese subtitles, and an H.264 deliverable. Use this skill whenever the user asks for a hand-drawn explainer, whiteboard animation, local IndexTTS voice clone, narration-to-video workflow, interrupted long render recovery, embedded subtitles, or Remotion + React technology covers. Also use it for Kling AI-style covers, independent 3:4 and 4:3 compositions, AI-generated text-free visual assets with programmatic typography, exact cover render commands, or PNG QA. Trigger for 手绘跟随动画、参考图风格、类似画风、白板手绘视频、手绘讲解动画、口播转视频、线稿绘制动画、画笔与画面不同步、分块描出、人物没画完就跳走、IndexTTS、本地音色克隆、长视频断点续渲染、字幕安全区、hand-drawn follow animation、whiteboard animation、drawing-hand video、Edge TTS、Remotion 封面、React 封面、Kling AI 封面、3:4/4:3 双比例封面、or embedded subtitles without a supplied SRT.
---

# Hand-Drawn Follow Animation

Convert narration into original scene stills and animate them with a marker whose physical nib follows deterministic, content-aware routes. Use ImageGen for visible scene art and the bundled scripts for timing, motion, TTS, subtitles, and QA.

Chinese edition: [SKILL.zh-CN.md](SKILL.zh-CN.md).

## Language selection and bilingual synchronization

Choose the rule edition from the language used to interact with the user for the current task:

- Chinese interaction: read [SKILL.zh-CN.md](SKILL.zh-CN.md) and only the matching files under `references/zh-CN/`.
- English interaction: read this `SKILL.md` and the matching English files directly under `references/`.
- Mixed-language interaction: follow the language of the user's latest explicit task. Ask only when the intended interaction language is genuinely ambiguous.

Do not read one language edition and answer from memory in the other language. Once the edition is selected, read every required rule from that edition completely.

Treat the two editions as synchronized normative mirrors. Whenever any workflow rule, default, field meaning, prompt constraint, QA threshold, or delivery requirement changes:

1. Update the corresponding English and Chinese passages in the same change.
2. Update both reference counterparts when the rule lives in `references/`.
3. Keep scripts, schemas, and assets language-neutral when they do not need separate localized copies.
4. Never complete a rule change after editing only one language.
5. Run `python3 scripts/validate_bilingual_docs.py` and the skill validator before accepting the change.

## 1. Reference routing

Read each required reference completely before its corresponding work:

- Analyze a supplied reference or choose a fallback style: [references/visual-styles.md](references/visual-styles.md).
- Generate or inspect scene and hand assets: [references/imagegen-prompts.md](references/imagegen-prompts.md).
- Create or edit `storyboard.json`: [references/project-schema.md](references/project-schema.md).
- Select a voice, synthesize TTS, time captions, or finish a narrated video: [references/tts-and-subtitles.md](references/tts-and-subtitles.md).
- Render, tune routes, inspect evidence, or accept output: [references/rendering-and-qa.md](references/rendering-and-qa.md).
- Generate Remotion + React covers with independent 3:4 and 4:3 layouts: [references/remotion-react.md](references/remotion-react.md).
- Apply lessons from local IndexTTS, Windows paths, long-render recovery, compact SRTs, and final handoff: [references/production-lessons.md](references/production-lessons.md).

Inspect `assets/motion-stages.jpg` and `assets/default-hand.png` when calibrating motion. Inspect `assets/style-anchor.png` only when no reference image is supplied.

## 2. Non-negotiable invariants

- Preserve every supplied narration clause exactly once and in order.
- Transfer only abstract visual traits from a reference. Invent new identities, silhouettes, poses, props, relationships, framing, and composition; never trace, recolor, or character-swap the source.
- Reserve the full-width lower 24% for captions by default. Keep all scene marks, shadows, regions, and nib routes above `caption_safe_area.top_ratio`.
- Keep the hand independent from scene style. Place the recorded marker-tip anchor—not the palm or fingertip—on the active route.
- Reveal each animated pixel only when a real nearby route seed is reached. Require nib-locked timing, pixel-resolution edges, no remote fill bloom, no grid tiles, no trailing fade, and no generic wipe.
- Complete each declared object before entering the next. For characters, finish dense hair first, then the rest of that character, then later characters or props. Do not impose a global top-to-bottom fill order.
- Complete each declared writing group before leaving it. Write lines top-to-bottom and Latin text or formulas left-to-right.
- Match the default TTS voice to the speaking protagonist or narrator. Never reuse a previous project's voice after changing character gender.
- End every scene on a hand-free completed hold and accept output only from visual evidence plus machine-readable reports.

## 3. Build the project

Collect the narration, reference image, audience, aspect ratio, resolution, pace, voice, and delivery requirements. Use 16:9, 1920×1080, 24 fps, and a light route-detectable background when unspecified.

Resolve `narrator_gender` before TTS:

- First person: match the speaking protagonist.
- Third person without a distinct narrator: match the main protagonist.
- Distinct narrator: match that narrator.
- Mixed or ambiguous protagonists: ask; do not guess from secondary cast.

Use `male` or `female`; an explicit user-selected voice overrides the default mapping defined in the TTS reference.

Create a dedicated project folder with `narration.txt`, `storyboard.json`, `scenes/`, `assets/`, `audio/`, and `output/`. Resolve the skill path once:

```bash
WHITEBOARD_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/hand-drawn-follow-animation"
```

Create the initial project, adding `--style-reference` only when supplied:

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/whiteboard_renderer.py" create-project \
  --input /absolute/path/narration.txt \
  --output /absolute/path/storyboard.json \
  --narrator-gender <male-or-female> \
  --style-reference /absolute/path/reference.png
```

## 4. Design the storyboard and assets

Split by meaning, keep clauses intact, and give each scene one communication job and one concrete visual metaphor. Replace every `TODO`. Preserve narration in the project instead of turning it into image text. Add exact notation programmatically.

When a reference is supplied, inspect it first, copy it into project assets, record `visual_style: reference-adapted`, and store one stable `style_profile`. Without a reference, use `editorial-character` and the bundled style anchor.

Present a compact scene plan before spending ImageGen calls. Generate each distinct scene separately at the target ratio. Keep the background uniform, important boundaries dark, all art outside the caption band, and the scene free of hands, pseudo-text, logos, and watermarks. Regenerate malformed or compositionally unsafe results.

Use ordered `object_regions` for touching character parts or props. Use `base_image`, `draw_image`, and ordered `hand_regions` for notation-heavy scenes so the hand writes only key groups, not static scaffolding. Follow the schema reference for field semantics.

Reuse the bundled hand unless the user explicitly requests another appearance. If replacing it, generate it separately on flat chroma key and run `prepare-hand`; never bake a hand into scene art.

## 5. Establish authoritative timing

After semantic scene boundaries and narrator gender are final, synthesize TTS before rendering:

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/edge_tts_pipeline.py" synthesize \
  /absolute/path/storyboard.json
```

Treat decoded per-scene audio duration and Edge WordBoundary timestamps as authoritative. They replace text-only duration estimates and produce `audio/narration.m4a`, per-scene audio, and `audio/narration.srt`.

When the user supplies a local IndexTTS or other voice-clone pipeline, use that exact voice and its final audio/timing artifacts instead of silently falling back to Edge TTS. Record the provider, voice-reference label, timing basis, and any limitation such as segment-only timestamps in `tts`.

## 6. Render and finish

Check the runtime and install only the missing packages into a project-local environment when requested:

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/check_env.py"
```

Render the silent master:

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/whiteboard_renderer.py" render \
  /absolute/path/storyboard.json \
  --output-dir /absolute/path/output
```

Do not replace computed drawing motion with a pan, zoom, dissolve, generic hand loop, or directional wipe. Repair source art, regions, route coverage, thresholds, or the hand anchor when evidence fails.

For long renders, preserve completed scene clips and evidence as checkpoints. A 0-byte or tiny MP4 left by an interruption is not a completed scene; validate each clip with `ffprobe` before concatenation and rerender only missing or invalid scenes when safe.

Mux narration and burn the authoritative subtitles:

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/edge_tts_pipeline.py" finish \
  /absolute/path/storyboard.json \
  --video /absolute/path/output/whiteboard-video.mp4 \
  --output /absolute/path/output/whiteboard-video-tts-subtitles.mp4
```

## 7. Verify and deliver

Inspect every path preview, stage sheet, and route JSON, then open the first scene clip and final video. Pass every acceptance row in the rendering reference. At minimum require:

- `caption_safe_area.unsafe_pixels == 0` within tolerance.
- `reveal_sync.mode == "nib-locked"`.
- `max_seed_distance_px <= limit_px`.
- `max_temporal_lag_frames <= 0.2`.
- Ordered hair/object and writing-group completion.
- A hand-free final hold of at least 0.8 seconds.
- Narration, subtitle, scene-boundary, voice-gender, stream, resolution, fps, and duration integrity.

Deliver the narrated MP4, silent master, TTS audio and timed SRT, `storyboard.json`, representative evidence, `render-report.json`, and `final-report.json`. Report duration, resolution, fps, audio-track count, voice, timing basis, and any remaining limitation. Label `audio/narration.srt` as TTS-timed and the renderer's `output/narration.srt` as estimated.

## 8. Remotion + React cover generation

Enter this branch when the user asks for a technology cover, a Kling AI-style cover, Remotion/React cover code, independent 3:4 and 4:3 outputs, or a named `npm` cover-render command. Read [references/remotion-react.md](references/remotion-react.md) before implementation. This branch adds a cover deliverable; it does not replace the hand-drawn animation, TTS, or subtitle rules when those are also requested.

Use the following contract unless the user explicitly supplies a different one:

| Item | Contract |
| --- | --- |
| Component | `src/KlingAiCover.tsx` |
| Compositions | `KlingAiThreeFourCover`, `KlingAiFourThreeCover` |
| 3:4 canvas | `900x1200` |
| 4:3 canvas | `1200x900` |
| Command | `npm run kling-ai:covers` |
| Outputs | `renders/kling-ai-cover-3x4.png`, `renders/kling-ai-cover-4x3.png` |

Design the two aspect ratios as separate compositions with separate safe areas, title blocks, hero placement, and spacing. Never create one by cropping, stretching, or resizing the other. Keep Chinese titles, metrics, badges, labels, outlines, shadows, and source statements in React/Remotion so they remain accurate and editable. If ImageGen or another model supplies art, request only a text-free background or hero visual: no pseudo-Chinese, random glyphs, extra logos, watermarks, people, platform UI, or unrelated words.

Prefer the smallest implementation that satisfies the visual brief. Before adding custom illustration code, check whether a reusable project component, CSS shape, SVG primitive, or existing asset already solves it. Preserve contrast, input validation, error handling, security, and accessibility-related requirements even when reducing code. Use `white-space: nowrap` or deliberately controlled line breaks for Chinese text; never rely on accidental browser wrapping for titles or metrics.

After implementation, run the named npm command from the actual Remotion project and inspect both real PNGs. Verify exact dimensions with `ffprobe` (or an equivalent image probe), inspect each full-size image, and inspect a thumbnail-sized version for title and metric readability. A passing TypeScript/build check alone is not delivery evidence. Report the component, composition IDs, command, output paths, dimensions, and any visual limitation. Keep the supplied full Kling AI visual prompt in the Remotion reference as a reusable prompt, while following the text-free AI asset rule above.

## 9. Production lessons and reusable recovery

Read [references/production-lessons.md](references/production-lessons.md) for the reusable runbook captured from real production failures. It covers input-versus-instruction boundaries, dedicated project scope, local IndexTTS timing, phrase-level subtitle repair, caption-band preflight, safe recovery after interruption, Windows execution, selective Git staging, and the evidence required before claiming delivery.

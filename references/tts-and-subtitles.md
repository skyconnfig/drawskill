# TTS and embedded subtitles

This reference covers both the default online Edge TTS pipeline and a user-supplied local voice-clone pipeline such as IndexTTS.

## Defaults

- Resolve the speaking narrator's gender before choosing a voice. For first-person narration, match the speaking protagonist rather than secondary characters visible in the scene. For third-person narration without a distinct narrator, match the main protagonist; if a separate narrator is identified, match that narrator.
- Record `narrator_gender` as `male` or `female` in `storyboard.json` before synthesis.
- Use Edge TTS `zh-CN-YunxiNeural` for an unspecified Mandarin male narrator and `zh-CN-XiaoxiaoNeural` for an unspecified Mandarin female narrator. A user-requested `--voice` overrides this mapping when the Edge path is used.
- If the story has mixed or ambiguous protagonists and no distinct narrator, ask instead of guessing from the visual cast.
- Keep `rate=+0%`, `volume=+0%`, and `pitch=+0Hz` unless the user requests another delivery.
- Treat Edge TTS as an online dependency. If the user supplies IndexTTS or another local voice-clone pipeline, use that exact pipeline and final audio instead of silently falling back to Edge TTS. Preserve the supplied narration exactly.
- Generate one audio file per semantic scene. Do not synthesize one sentence per arbitrary subtitle line.

## Authoritative timing

For the default Edge path, run `edge_tts_pipeline.py synthesize` after the semantic scene split and before rendering. The command requests `WordBoundary` metadata, decodes every scene audio file to measure its true length, rounds each scene duration up to a video frame, and writes those durations back into `storyboard.json`. For a local pipeline, perform the equivalent steps with its own synthesis and timing tools before rendering.

The combined narration audio pads each scene to the same frame-aligned duration used by the renderer. Subtitle cues are grouped into readable Chinese phrases while retaining source timestamps. With Edge, these are WordBoundary start and end times; with segment-only local timing, split at semantic punctuation and allocate interior cue intervals deterministically by spoken-character proportion. Label that limitation in the final report. This shared scene clock is the authoritative timing basis.

Do not replace the timed subtitle file with the renderer's estimated `output/narration.srt`. The authoritative files are the final TTS audio and its matching timed SRT, normally `audio/narration.m4a` and `audio/narration.srt`. Record the actual paths and timing basis in `tts`.

## Subtitle treatment

- Keep one or two lines centered inside the reserved full-width lower 24% caption safe area.
- Prefer 8–22 Chinese characters per cue; split a long clause semantically when possible.
- Use white text with a compact dark outline and transparent background. Never add a black or translucent caption box unless the user explicitly requests it.
- At 1920×1080, start near 48 px type and a 59 px bottom margin.
- Require the scene image, critical subject, and active marker-tip route to remain above the caption safe area rather than moving subtitles around individual compositions.

## Failure handling

- If `edge-tts` is missing, create a project-local virtual environment and install the exact dependency reported by `check_env.py`.
- If online synthesis fails, retry once. Then report the network/service failure; do not fabricate timestamps.
- If the selected voice is unavailable, run `edge-tts --list-voices` and choose a currently listed fixed `zh-CN` voice with the closest requested gender and tone.
- If FFmpeg lacks the `subtitles` filter, install an FFmpeg build with libass or deliver the timed SRT as a separate track and state that subtitles are not burned in.
- If a local timing file contains one long segment, do not claim word-level alignment after proportional splitting; preserve the segment boundaries and call the result phrase-level or proportional timing.

## Acceptance checks

- The final MP4 contains one H.264 video stream and one AAC audio stream.
- The first spoken word, every scene boundary, and the last spoken word remain aligned to the drawing timeline.
- Every supplied clause appears once and in order across subtitle cues.
- Captions remain readable at normal playback size and stay inside the lower safe area.
- The final duration matches the frame-aligned TTS timeline within one video frame.
- `tts.narrator_gender` matches the speaking protagonist or narrator, and the selected voice reports the same gender unless the user explicitly requested otherwise.
- `tts.engine`, the non-secret voice-reference label, final audio path, subtitle path, and timing basis are present and match the delivered files.

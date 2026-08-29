# Rendering and QA

## What the renderer does

1. Load the final `image`; when present, load `base_image` as the starting frame and `draw_image` as the only route source.
2. Resolve `canvas.caption_safe_area` and reject any final-image content, declared region, or marker-tip route inside it.
3. Sample the route-source border color and detect dark ink and non-background content separately.
4. Aggregate pixels into a small grid.
5. Thin thick ink regions to one-cell centerlines, while retaining the full ink mask for reveal.
6. Split touching centerlines at ordered `object_regions`, then traverse and complete every component in the current object before entering the next. For notation, complete declared `hand_regions` in order; inside each text region, cluster vertically overlapping strokes into lines, order lines top-to-bottom, and order components left-to-right before recording first-visit order on the complete route.
7. Propagate that order into nearby colored content, retaining each planning cell's nearest route-seed coordinate.
8. For direct-color scenes, add sparse fill-coverage tracks so broad hair, clothing, and pigment blocks have nearby real nib routes. Convert the coarse timing map to a pixel-resolution reveal: every animated source pixel chooses the geometrically nearest route seed, begins only after that seed is reached, and completes its radial single-pixel micro-dither within `0.2` output frame. Classify isolated near-background paper grain as static texture. Never repeat one order value into a hard square tile, reveal a remote patch, keep fading after the nib leaves, or blur the source texture into a halo.
9. In legacy mode, render black line work first and restore original color along the same route.
10. With `direct_draw`, reveal original stroke color in one pass and keep the hand off during the completed hold.
11. Place the marker nib on the current route point.
12. Remove the hand and hold the complete still.

The first-visit order must store the index on the complete marker route, including DFS backtracking. Never time image reveal by the number of unique cells while timing the hand by the longer full route; that creates a systematic hand/image phase error. Full-width ink and colored cells inherit the complete-route step of their nearest centerline seed, so thick strokes and fills appear locally around the nib without forcing the hand to raster-scan every dark pixel.

This is deterministic: the same project JSON and source assets produce the same routes and timing.

## Tuning guide

| Symptom | Repair |
| --- | --- |
| Empty background receives many routes | Raise `content_distance`; regenerate with a flatter background. |
| Pale outlines are skipped | Raise `ink_threshold` or regenerate with darker black outlines. |
| Colored fills are treated as black line work | Lower `ink_threshold`. |
| Hand motion looks too blocky | Lower `grid_cell`; expect more route points and render work. Pixel reveal itself must remain smooth at the default cell size. |
| Dense hair or fills reveal as square stair-step tiles | Reject the render; verify pixel-resolution nearest-seed reveal is enabled. Do not hide the defect only by lowering `grid_cell`. |
| Dense hair or fills reveal as hard polygon patches | Verify tightly capped radial seed-distance delay and single-pixel micro-dither are enabled; reject a boolean whole-patch reveal or temporal alpha feather. |
| Content continues appearing after the nib leaves | Enable nib-locked reveal, remove anticipatory/trailing alpha feathering, and require temporal lag no greater than `0.2` frame. |
| A colored area appears while the nib is elsewhere | Lower `fill_route_stride` or `grid_cell` until `max_seed_distance_px <= max_reveal_radius_px`; never raise the limit merely to pass QA. |
| Paper speckles slowly appear across empty space | Keep only content supported by active planning cells in the animated mask and composite isolated near-background grain as static texture from frame one. |
| Hair or another object is left half-drawn while the hand follows a touching contour elsewhere | Add ordered `object_regions`, with the dense object first, and verify the route is split at the region boundary. |
| Hand jitters across tiny speckles | Raise `grid_cell` or regenerate without paper texture/noise. |
| Some color never appears until the final frame | Lower `content_distance` or simplify the generated image. |
| Hand touches the line with its palm instead of the nib | Correct the hand `tip_anchor` by rerunning `prepare-hand`. |
| Hand is too dominant | Lower `hand.width_ratio`. |
| Hand is constantly busy or traces the whole board | Move scaffolding to `base_image`; keep only 1–3 key groups in `draw_image`; shorten `write_seconds`. |
| Hand leaves a half-written word or formula | Expand one `hand_regions` rectangle to contain the complete text group and verify monotonic group order. |
| A formula starts at its rightmost letter | Do not sort components by top-most pixel. Cluster strokes into text lines, then sort each line by left edge. |
| A label touches an axis, arrowhead, tick, or diagram | Move it outside the collision map; preserve 18–24 px clearance at 1920×1080. |
| Scene content approaches or enters subtitles | Recompose above `caption_safe_area.top_ratio`; keep the full-width lower 24% blank. Never solve this only by nudging the subtitle. |
| Scene finishes before it can be read | Increase `duration` or `hold_seconds`. |
| A scene MP4 exists but is 0 bytes or only a few dozen bytes | Treat it as an interrupted or corrupt checkpoint. Rerender that scene and validate it with `ffprobe` before concatenation. |

## Interrupted render recovery

Keep each scene clip, route JSON, path preview, and stage sheet as a checkpoint. After an interruption, enumerate the expected scene IDs and validate every clip individually. A valid checkpoint must open with `ffprobe`, contain a video stream at the expected width, height, and fps, and have a plausible duration; file existence and encoder exit status are not enough. Rerender only missing or invalid scenes when the storyboard and assets are unchanged.

Concatenate only after every expected clip passes those checks, then validate the assembled silent master separately. Keep the silent render report distinct from the final mux report: the latter must prove the H.264/AAC streams, subtitle burn, final duration, and audio-track count. Preserve partial evidence when recovery fails so the next run can resume from the last verified boundary.

## Acceptance gate

| Area | Must pass | Hard fail |
| --- | --- | --- |
| Narration integrity | All supplied clauses appear once, in order, in `storyboard.json` and `narration.srt`. | Missing, duplicated, rewritten, or reordered narration. |
| Scene image | Clean off-white field, dark readable outlines, intentional accents, no hand or pseudo-text, and content matching `visual_style`. | Hand baked into scene, watermark, malformed text, muddy background, or clipped subject. |
| Reference adaptation | For `reference-adapted`, the medium, line behavior, palette roles, texture, shape language, and density agree with the approved `style_profile`. | The result ignores the profile or copies only a superficial color palette while losing the reference's broader visual grammar. |
| Originality | Subjects, silhouettes, poses, props, framing, focal arrangement, and composition are newly designed for the narration. | Recognizable character, face, mascot, costume, logo, signature object, exact pose, or one-to-one reference layout is reproduced; the result is traced, recolored, or character-swapped. |
| Hand-drawn provenance | When hand-drawn output is requested, every scene visibly retains ImageGen-made structural strokes/cards/guides and analog pressure, wobble, or paper character beneath exact programmatic notation. | Fully programmatic/vector scene, procedural noise presented as generated art, or ImageGen content hidden by opaque reconstruction. |
| Route coverage | Path preview touches every important subject and relationship. | Major subject, arrow, or diagram block is never visited. |
| Hand economy | The hand writes only key groups and is absent while the viewer reads the completed board. | Hand traces titles, panels, axes, grids, ticks, diagram scaffolding, or remains active for nearly the entire scene. |
| Text-group integrity | Every declared word, label, equation, or grouped calculation is completed before the route enters the next region. | The hand abandons a partial text group, interleaves unrelated formulas, or returns later to finish the same group. |
| Human writing order | Text lines are written top-to-bottom; Latin text and formulas are written left-to-right, with disconnected strokes at the same x completed before advancing. | A later glyph appears first because it is taller, a formula begins from the right, or separate lines are interleaved. |
| Label clearance | Labels clear protected geometry and the caption band; necessary chips preserve legibility without covering a line. | Any character is hidden by an axis, arrow, or tick; any label obscures geometry; or two annotations overlap. |
| Caption safe area | The full-width lower 24% contains only board background; every subject, prop, baseline, arrow, label, panel, static scaffold, region, and route stays above the boundary. | Any scene mark or marker-tip route enters the caption band, even when the subtitle itself remains readable. |
| Hand alignment | Physical marker nib sits on the current route and stays plausibly scaled. | Palm, fingertip, or floating marker body traces the route; visible green fringe. |
| Reveal synchronization | Each animated pixel is assigned to a real nearby route seed, begins no earlier than that seed, and completes within `0.2` frame; `reveal_sync.mode` is `nib-locked` and the measured maximum distance passes its configured limit. | Hand progress uses a different clock, a patch appears before/after its seed window, trailing fade continues after the nib leaves, or new pixels appear in a remote region. |
| Reveal resolution | Dense ink, hair, clothing, and filled regions use fill-coverage routes plus pixel-resolution boundaries derived from nearest route seeds and fixed micro-dither. | Any visible `grid_cell`-sized square tiles, stair-step chunks, hard Voronoi polygons, blurry halos, or locally unsupported fill blooms appear during drawing. |
| Object completion | Hair and every declared priority object are completed before the hand enters the next `object_regions` box. | The hand abandons a partially drawn object, draws another object, then returns to finish it. |
| Drawing order | Dark line work appears before color, and color follows the established route. | Generic wipe, random tile noise, full-image fade, or color appearing before structure. |
| Final lock | Final frame matches the approved still, contains no hand, and holds for at least 0.8 seconds. | Hand remains, content is incomplete, or the frame cuts immediately. |
| Timing | Every scene duration comes from narration timing or the documented text-only estimate. | Arbitrary fixed duration unrelated to narration. |
| TTS synchronization | With TTS enabled, scene lengths, combined audio padding, and captions use the same frame-aligned clock. | Text-only estimates overwrite verified audio timing; captions visibly lead or lag speech. |
| Embedded captions | Readable one- or two-line Chinese captions stay inside the lower safe area and preserve all clauses. | Cropped, unreadable, duplicated, missing, or critical-content-obscuring captions. |
| Motion | Marker position changes in relation to visible content; scene is not a camera move on a still. | Pan, zoom, shake, dissolve, or one identical motion applied to the whole frame. |
| Technical output | Playable H.264 MP4 at configured resolution and fps, with audio state reported accurately. | Wrong dimensions, corrupt file, unexpected audio, or missing evidence. |

## Evidence review

Inspect every `*-path.jpg` at normal playback scale. The renderer shades the caption safe area and draws its top boundary in red; no route or scene mark may touch or cross that boundary. A dense route is acceptable only when it corresponds to real detail. For layered scenes, require route JSON `group` and `line` values to be monotonic at their respective scopes; within one line, require each newly entered component's first x coordinate to be nondecreasing. Inspect early frames of at least one formula—not only the final stage sheet—to prove that writing begins at the leftmost glyph. Inspect every `*-stages.jpg` from left to right and verify the static skeleton, complete group-by-group writing, no repeated color pass when `direct_draw` is enabled, and hand-free final art.

Open the first scene clip and the final concatenated MP4. Before concatenation, probe every scene clip for a valid video stream, expected dimensions/fps, and plausible duration; confirm that concatenation uses hard cuts and that no scene loses its last frame. Inspect consecutive frames around at least one dense fill: new pixels must lie near route points swept during that frame, not fade in around an earlier pen position. Confirm every scene report has `reveal_sync.mode = nib-locked`, `max_seed_distance_px <= limit_px`, and `max_temporal_lag_frames <= 0.2`. When TTS is enabled, inspect the finished narrated MP4 near the first word, every scene cut, and the final word; verify one audio track and visibly synchronized captions.

For `reference-adapted`, review the reference and at least three representative scene stills side by side. Confirm trait-level consistency and content-level distance. If a scene preserves the source's object map, pose, or focal layout, replace its visual metaphor and regenerate rather than applying a cosmetic edit.

Record any parameter repair, caption-band cleanup, or recovery rerender in the final notes. If lower-band pixels were cleaned, document why they were disposable background rather than meaningful subject matter. Do not accept a render based only on a successful encoder exit or file existence.

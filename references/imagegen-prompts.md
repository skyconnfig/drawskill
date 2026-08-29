# ImageGen prompt recipes

Use Codex's built-in ImageGen. Generate each distinct scene with a separate call. Keep scene art and the hand independent.

## `reference-adapted` scene still

Attach the project `style_reference` to the ImageGen call. Fill the trait fields from the approved `style_profile`; do not ask ImageGen to identify or reproduce a named IP or artist.

```text
Use case: scientific-educational whiteboard animation
Asset type: original whiteboard drawing-animation source still
Primary request: <one concrete visual metaphor for this narration scene>
Reference use: use the attached image only for high-level <medium>, <line behavior>, <palette roles>, <texture>, <shape language>, <shading>, and <drawing density>
Original subject: <new subjects, silhouettes, poses, props, relationships, and environment invented for this scene>
Scene/backdrop: a light, nearly uniform route-detectable board or paper field adapted to the reference's material character
Style/medium: <style_profile summary>; strong readable outlines; analog irregularity where supported by the reference
Composition/framing: exact <16:9 or 9:16> canvas; a new composition unrelated to the reference layout; every subject fully visible; at least 8% outer safe margin; place all visual content above y=76% of canvas height
Constraints: completed still only; reserve the full-width lower 24% from y=76% to the bottom as completely blank board background with no subject, prop, floor or ground line, arrow, label, panel, decoration, shadow, or texture change; no hand, arm, marker, writing action, pseudo-text, captions, logo, watermark, signature, or UI chrome; do not reproduce any recognizable character, face, mascot, costume, brand element, signature prop, exact pose, camera angle, or composition from the reference
Avoid: tracing; near-copying; recoloring the reference; character substitution in the same layout; one-to-one object correspondence; tiny details; faint primary outlines; muddy or strongly varying borders
```

### Reference-adaptation rules

- Preserve abstract craft traits, not source identity or scene content.
- Change subject identity, silhouettes, poses, props, focal arrangement, framing, and object relationships.
- Keep a shared `style_profile` across scenes instead of repeatedly improvising from the raw reference.
- Use ImageGen for the visible structural art; add exact notation programmatically.
- If the first result resembles the reference too closely, do not make a minor edit. Recompose the scene from a different visual metaphor.

## `editorial-character` scene still

Adapt only the `Primary request`, `Subject`, and composition to the approved scene. Preserve the shared style wording across all scenes.

```text
Use case: scientific-educational
Asset type: whiteboard hand-drawing animation source still
Primary request: <one concrete visual metaphor for this scene>
Scene/backdrop: a warm off-white fibrous whiteboard or drawing-paper field with subtle natural grain and extremely faint erased-marker traces
Subject: <2–5 large identifiable subjects, objects, arrows, or simple diagram elements>
Style/medium: editorial whiteboard marker illustration; thin slightly imperfect black ink outlines; sparse muted orange and mint flat accents; subtle human-drawn wobble; no paper collage and no photorealism
Composition/framing: exact <16:9 or 9:16> canvas; balanced explanatory composition contained above y=76% of canvas height; every subject fully visible; at least 8% outer safe margin; large simple shapes that remain readable at normal video size
Lighting/mood: flat, bright, friendly educational tone; no directional lighting
Constraints: completed still only; reserve the full-width lower 24% from y=76% to the bottom as completely blank board background with no subject, prop, floor or ground line, arrow, label, panel, decoration, shadow, or texture change; no hand, arm, marker, pen, brush, writing action, text, letters, numbers, captions, logo, watermark, border, frame, shadow, gradient, texture, or UI chrome
Avoid: tiny details; gray low-contrast outlines; filled dark backgrounds; pseudo-writing; overlapping unrelated objects; decorative doodles that do not explain the narration
```

### Consistency rules

- Keep the same background tone, line weight, palette, and drawing density in all scenes.
- Let the image communicate the idea without copying narration into the image.
- Prefer one focal action or relationship per scene.
- Use arrows only when they explain flow, cause, transformation, or direction.
- Keep important outlines dark enough for threshold extraction.
- Regenerate any scene that includes a hand or malformed text.

## Marker hand on chroma key

Reuse the bundled hand regardless of scene style. Generate a replacement only when explicitly requested. The requested marker-tip coordinate becomes the `prepare-hand` anchor input; its logic does not change with the reference.

```text
Use case: background-extraction
Asset type: reusable foreground overlay for a whiteboard drawing animation
Primary request: a realistic adult right hand naturally holding one plain black felt-tip marker in a writing grip; the marker nib visibly touches the exact normalized canvas position x=28%, y=5%; the nib stays above the hand while the wrist and forearm extend downward and exit through the bottom edge; the full hand, marker, wrist, and a short section of forearm are visible
Scene/backdrop: perfectly flat solid #00ff00 chroma-key background for local background removal
Style/medium: clean realistic studio cutout, anatomically natural fingers, crisp silhouette
Composition/framing: portrait-like square canvas; marker tip is the upper-leftmost functional point and remains clearly visible; the direction is unmistakably bottom-to-top; forearm exits only through the bottom edge; generous side padding
Lighting/mood: soft even neutral studio light on the subject only
Constraints: exactly one hand and one marker; no drawing, no board, no ink line, no cast shadow, no contact shadow, no reflection, no text, no logo, no watermark; background must be one uniform #00ff00 with no gradient, texture, floor plane, lighting variation, or green inside the subject
Avoid: forearm entering from the left, right, or top; horizontal arm; marker nib near the bottom; extra fingers; duplicated marker; cropped wrist; hidden marker nib; bent marker; jewelry; nail art; sleeve logos
```

## Image inspection gate

Before rendering, verify:

- The scene has a nearly uniform border/background.
- Important line work is black or dark charcoal, not pale gray.
- The subject fits the safe area and has no unintended text or hand.
- Every visual mark ends above y=76%; the full-width lower 24% matches the empty board background.
- A reference-adapted scene matches the approved abstract style profile without reusing recognizable reference content or layout.
- The hand key is flat, its marker nib is visible, and the physical tip matches the recorded anchor.
- Scene and hand assets contain no watermark or logo.

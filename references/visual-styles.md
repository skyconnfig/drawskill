# Reference-driven visual styles

Store `reference-adapted` in root-level `visual_style` when a reference image is supplied. Use `editorial-character` only as the no-reference fallback.

## Reference analysis

Inspect the image and write a compact `style_profile` before storyboarding:

- `medium`: marker, pencil, ink wash, crayon, flat paint, cut-paper simulation, or another visible medium.
- `line`: weight, pressure variation, wobble, taper, edge softness, and outline hierarchy.
- `palette`: background, primary ink, accent roles, saturation, and contrast; do not sample protected logos as palette anchors.
- `texture`: paper grain, dry brush, speckle, fill irregularity, or clean flatness.
- `shape_language`: rounded/angular balance, proportion tendencies, simplification, and geometric vocabulary.
- `shading`: none, hatching, flat shadow shapes, stipple, or sparse tonal blocks.
- `density`: whitespace, object count, detail scale, and clustering.
- `composition`: hierarchy, directional flow, framing, and rhythm expressed abstractly rather than as coordinates copied from the reference.

Keep only traits that remain useful on a light, route-detectable whiteboard field. Translate dark or highly textured references into a light-background equivalent while preserving their line, color-role, and shape-language character.

## Originality boundary

Transfer visual grammar, not depicted identity. Never reproduce or closely imitate:

- a recognizable character, face, mascot, creature design, costume, or body silhouette;
- a logo, brand mark, signature, watermark, franchise symbol, or distinctive text treatment;
- a signature prop or distinctive collection of accessories strongly tied to the source;
- the same pose, camera angle, focal placement, scene layout, or object-to-object arrangement;
- a near-identical scene with only colors, labels, or character names changed.

Invent new subjects, silhouettes, expressions, poses, props, relationships, backgrounds, and compositions from the narration. If the reference is dominated by protected identity rather than transferable craft traits, extract only broad medium and palette behavior and increase visual distance.

## Consistency and selection

Use one approved `style_profile` for all scenes. Preserve its medium, line behavior, palette roles, texture, shape language, and density while varying compositions according to narration.

Selection precedence:

1. With a user-supplied reference, use `reference-adapted` and record `style_reference` plus `style_profile`.
2. Without a reference, use `editorial-character` and inspect `assets/style-anchor.png`.
3. Keep the hand overlay and all motion planning independent of visual-style selection.

## Fallback `editorial-character`

Use a friendly editorial explainer look with sparse people, objects, environments, diagrams, and visual metaphors. Preserve the off-white board, dark imperfect marker outlines, restrained accent colors, and generous whitespace.

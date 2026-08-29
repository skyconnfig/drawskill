# Remotion + React cover generation

Use this reference when a task asks for a technology cover, a Kling AI-style cover, Remotion/React implementation, or independent portrait and landscape PNG exports. The cover workflow is intentionally separate from the hand-drawn route renderer: Remotion owns exact text and layout, while AI is limited to text-free visual material.

## Required workflow

1. Inspect the target Remotion project, existing scripts, fonts, assets, and composition registration before editing. Reuse an existing component or primitive when it already solves the requirement.
2. Create or update `src/KlingAiCover.tsx`. Keep the two layouts as explicit branches or components with independent coordinates and safe areas.
3. Register `KlingAiThreeFourCover` at `900x1200` and `KlingAiFourThreeCover` at `1200x900`.
4. Add or preserve the exact script command `npm run kling-ai:covers`, producing the two exact PNG paths below.
5. Render, inspect, and verify the real artifacts. Do not report code completion as media completion.
6. Run typecheck/build and the cover render as separate checks. A passing TypeScript check does not prove that the PNGs exist, have the requested dimensions, or remain readable at thumbnail size.

## Contract

| Field | Required value |
| --- | --- |
| Component | `src/KlingAiCover.tsx` |
| Portrait composition | `KlingAiThreeFourCover`, `900x1200` |
| Landscape composition | `KlingAiFourThreeCover`, `1200x900` |
| Render command | `npm run kling-ai:covers` |
| Portrait output | `renders/kling-ai-cover-3x4.png` |
| Landscape output | `renders/kling-ai-cover-4x3.png` |

## Layout and typography rules

- Treat 3:4 and 4:3 as independent art direction. Do not crop, stretch, or derive one from the other.
- Keep generous margins and aspect-ratio-specific safe areas. In 4:3, normally put the title block on the left and the hero card on the right. In 3:4, stack the title at the top, put the hero card in the lower middle, and keep the metric strip and footer separate.
- Render all Chinese text, numbers, badges, labels, outlines, shadows, and source statements in Remotion. Use explicit strings, suitable Chinese fonts, `white-space: nowrap`, and controlled line breaks where needed.
- Make the main keyword the largest text, the result statement the next level, and supporting statements smaller. Check readability at thumbnail size, not only at full resolution.
- Preserve the visual hierarchy and accessibility of text contrast. Do not remove meaningful labels merely to shorten code.

## AI asset boundary

Use AI only for a text-free background, radar/grid texture, or hero visual. The asset prompt must explicitly exclude readable text, pseudo-Chinese, random glyphs, logos, watermarks, people, platform UI, and unrelated words. If an AI image contains malformed text, regenerate or mask it; never ship it as typography. Keep the generated asset replaceable and render the final text layer programmatically.

## Verification

Run the project command from the project directory:

```powershell
npm run kling-ai:covers
```

Verify both files exist and probe their dimensions:

```powershell
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 renders/kling-ai-cover-3x4.png
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 renders/kling-ai-cover-4x3.png
```

Expected results are `900,1200` and `1200,900`. Confirm both files are non-empty before probing them. Open both full-size images, then inspect deliberately reduced thumbnail versions; browser or code previews alone are not enough. Acceptance requires no clipped edge text, no overlap caused by accidental wrapping, readable main title/result/metric, and no AI-generated pseudo-text. Record the command, composition IDs, paths, dimensions, typecheck result, and any unresolved visual issue in the handoff.

## Reusable Kling AI visual prompt

The following prompt is a visual reference for the requested style. It is deliberately paired with the AI asset boundary above: use it to guide background and hero art, but implement every word and number in Remotion.

```text
Create a high-click-through Chinese technology education video cover.

Topic:
AI video generation industry, Kling AI, the shift from flashy demos to real production tools.

Style:
premium Chinese technology creator thumbnail,
Bilibili and Douyin knowledge channel style,
bold editorial poster design,
high contrast,
modern AI industry analysis,
professional but dramatic,
clean information hierarchy.

Canvas:
create two independent layouts:
1. 3:4 vertical poster, 900x1200
2. 4:3 horizontal poster, 1200x900

Do not crop one layout from the other.
Design each aspect ratio independently with its own safe areas.

Background:
dark charcoal black background,
color approximately #0B0B0B,
subtle halftone dot pattern,
futuristic circular radar lines,
very subtle orange glow,
minimal technology grid texture,
no clutter,
no photographic background.

Color palette:
main orange #FF5A00,
pure white #FFFFFF,
dark black #111111,
secondary gray #777777,
orange glow,
white and orange high-contrast typography.

Typography hierarchy:
the main topic keyword must be the largest element,
the result statement must be below it,
supporting information must be much smaller.

Main title:
“AI 视频”
Use bright orange,
extra-bold Chinese typography,
large heavy black font,
thin white outline,
hard black drop shadow,
slight 3D extrusion,
strong visual impact.

Result title:
“真正战场变了”
Use white,
extra-bold Chinese typography,
dark outline,
orange offset shadow,
large and highly readable.

Small supporting statement:
“从炫技产品，到生产工具”
Use light gray or white,
smaller than the main title,
placed above the main title.

Supporting promise:
“谁能把奇迹稳定生成 100 次？”
Use white bold text,
inside a thin orange rounded rectangle,
dark translucent background.

Top-left badge:
“AI 视频观察”
Small rounded capsule,
orange outline,
small orange glowing dot,
dark translucent fill.

Top-right badge:
“可灵 AI”
Small rounded capsule,
orange outline,
white bold text,
dark translucent fill.

Hero visual:
show a stylized AI video production system interface,
large white information card with black border,
orange circular radar rings behind it,
strong hard shadow,
clean UI composition.

Inside the hero card:
large metric:
“8.5 亿+”
small supporting text:
“同比增长 200% 以上”

Below the card show three compact labels:
“模型”
“工作流”
“成本”

Highlight “成本” with bright orange fill.
Keep the other two labels white with black borders.

Add a small source-derived statement:
“生成一次 ≠ 交付一次”

Composition for 4:3:
title block on the left,
hero visual card on the right,
large empty margins around all elements,
no text touching the edges,
title remains readable at thumbnail size.

Composition for 3:4:
stack the title area at the top,
place the hero visual card in the lower middle,
place the metric strip below the hero card,
keep the footer separate from the hero visual,
do not overlap any elements.

Visual language:
bold Chinese technology news thumbnail,
orange and white collision,
large readable text,
strong hierarchy,
hard shadows,
rounded cards,
clean spacing,
high CTR composition,
professional AI industry commentary cover.

Important:
all Chinese text must be rendered accurately and remain readable,
do not use random Chinese characters,
do not add unrelated words,
do not add extra logos,
do not add people,
do not add realistic photography,
do not add watermarks,
do not add platform UI,
do not overcrowd the design.
```

For implementation, the final instruction is authoritative: AI generates only text-free visual material; Remotion generates the exact Chinese typography and metrics. Keep rendered PNGs and temporary AI assets outside a focused Skill commit unless the user explicitly requests them.

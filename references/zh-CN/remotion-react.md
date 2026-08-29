# Remotion + React 封面生成

当任务要求科技封面、类似可灵 AI 的封面、Remotion/React 实现，或分别输出竖版与横版 PNG 时，读取本 reference。封面流程与手绘路径渲染器分开：Remotion 负责精确文字和布局，AI 只负责无文字视觉素材。

## 必须执行的流程

1. 先检查目标 Remotion 项目的现有脚本、字体、素材和 Composition 注册方式，再修改代码。已有组件或基元能满足要求时优先复用。
2. 创建或更新 `src/KlingAiCover.tsx`。将两种画幅写成明确独立的布局分支或组件，分别设置坐标和安全区。
3. 注册 `900x1200` 的 `KlingAiThreeFourCover` 与 `1200x900` 的 `KlingAiFourThreeCover`。
4. 添加或保留精确脚本命令 `npm run kling-ai:covers`，生成下面规定的两个 PNG 路径。
5. 完成真实渲染、视觉检查和尺寸验证。不能把“代码写完”当成“媒体交付”。
6. 把 typecheck/build 和封面渲染作为两项独立检查。TypeScript 通过不能证明 PNG 已生成、尺寸正确或缩略图仍然可读。

## 契约

| 字段 | 必须值 |
| --- | --- |
| 组件 | `src/KlingAiCover.tsx` |
| 竖版 Composition | `KlingAiThreeFourCover`，`900x1200` |
| 横版 Composition | `KlingAiFourThreeCover`，`1200x900` |
| 渲染命令 | `npm run kling-ai:covers` |
| 竖版输出 | `renders/kling-ai-cover-3x4.png` |
| 横版输出 | `renders/kling-ai-cover-4x3.png` |

## 布局与排版规则

- 3:4 和 4:3 是两套独立的设计。禁止裁切、拉伸或由其中一个缩放得到另一个。
- 保留足够边距并分别设置安全区。4:3 通常左侧放标题、右侧放 Hero 卡片；3:4 顶部堆叠标题，中下部放 Hero 卡片，指标条和页脚分开。
- 所有中文文字、数字、徽章、标签、描边、阴影和来源说明都由 Remotion 渲染。使用明确字符串、合适的中文字体、`white-space: nowrap`，必要时使用受控换行。
- 主关键词字号最大，结果陈述次之，辅助陈述更小。必须在缩略图尺寸下检查可读性，不能只看原尺寸。
- 保持文字对比度和无障碍可读性。不能为了减少代码而删掉有意义的标签。

## AI 素材边界

AI 只用于生成无文字背景、雷达/网格纹理或 Hero 视觉。素材提示词必须明确排除可读文字、伪中文、随机字形、Logo、水印、人物、平台 UI 和无关词语。AI 图片出现乱码时要重新生成或遮罩，不能把它当作排版交付。生成素材应保持可替换，最终文字层必须程序化渲染。

## 验证

在实际项目目录执行：

```powershell
npm run kling-ai:covers
```

确认两个文件存在，并检查尺寸：

```powershell
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 renders/kling-ai-cover-3x4.png
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 renders/kling-ai-cover-4x3.png
```

预期结果为 `900,1200` 和 `1200,900`。探测前确认两张文件都不是空文件。打开两张全尺寸图片，再检查主动缩小后的缩略图；浏览器或代码预览本身不够作为证据。验收要求：边缘文字未被裁切，没有意外换行造成的重叠，主标题/结果标题/指标清晰可读，且没有 AI 伪文字。交接时记录命令、Composition ID、路径、尺寸、typecheck 结果和未解决的视觉问题。

## 可复用的 Kling AI 视觉提示词

下面的提示词用于复用用户要求的风格。它必须与上面的 AI 素材边界一起使用：用它指导背景和 Hero 视觉，但每个文字和数字都必须由 Remotion 实现。

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

实现时以最后一条规则为准：AI 只生成无文字视觉素材；精确的中文排版和指标全部由 Remotion 生成。除非用户明确要求，生成的 PNG 和临时 AI 素材不要加入聚焦的 Skill 提交。

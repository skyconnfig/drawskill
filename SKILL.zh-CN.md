# 手绘跟随动画

把口播转换为原创场景静帧，并用实体笔尖沿确定性的内容感知路径完成绘制动画。使用 ImageGen 生成可见场景画面，使用本 skill 自带脚本处理时间、动画、配音、字幕与质量验收。

英文主文件：[SKILL.md](SKILL.md)。

## 语言选择与双语同步

根据当前任务中与用户交互所使用的语言选择规则版本：

- 中文交互：读取本文件 [SKILL.zh-CN.md](SKILL.zh-CN.md)，并且只读取 `references/zh-CN/` 下对应的中文 reference。
- 英文交互：读取 [SKILL.md](SKILL.md)，并读取 `references/` 目录下对应的英文 reference。
- 中英混合交互：以用户最新明确任务所使用的语言为准；只有确实无法判断交互语言时才询问。

禁止读取一种语言的规则后，凭记忆用另一种语言执行。选定版本后，必须完整读取该语言版本中当前任务需要的所有规则。

中英文两版是同步且具有同等规范效力的镜像。任何工作流规则、默认值、字段含义、提示词限制、QA 阈值或交付要求发生变化时：

1. 在同一次变更中修改对应的英文和中文段落。
2. 规则位于 `references/` 时，同时修改中英文 reference 对应文件。
3. 不需要本地化的脚本、Schema 和素材保持单一的语言无关版本。
4. 只修改一种语言时，不得把规则变更标记为完成。
5. 验收前运行 `python3 scripts/validate_bilingual_docs.py` 和 skill 结构校验器。

## 1. Reference 读取路由

在执行对应工作前，完整阅读所需 reference：

- 分析用户参考图或选择无参考图的默认风格：[references/zh-CN/visual-styles.md](references/zh-CN/visual-styles.md)。
- 生成或检查场景与手部素材：[references/zh-CN/imagegen-prompts.md](references/zh-CN/imagegen-prompts.md)。
- 创建或修改 `storyboard.json`：[references/zh-CN/project-schema.md](references/zh-CN/project-schema.md)。
- 选择声音、合成 TTS、生成时间戳字幕或完成有声视频：[references/zh-CN/tts-and-subtitles.md](references/zh-CN/tts-and-subtitles.md)。
- 渲染、调节路径、检查证据或验收输出：[references/zh-CN/rendering-and-qa.md](references/zh-CN/rendering-and-qa.md)。
- 生成 Remotion + React 封面，并分别设计 3:4 与 4:3：[references/zh-CN/remotion-react.md](references/zh-CN/remotion-react.md)。
- 处理本地 IndexTTS、Windows 路径、长渲染恢复、短语字幕和最终交付：[references/zh-CN/production-lessons.md](references/zh-CN/production-lessons.md)。

调试绘制动作时检查 `assets/motion-stages.jpg` 和 `assets/default-hand.png`。只有在用户没有提供参考图时才检查 `assets/style-anchor.png`。

## 2. 不可妥协的硬性规则

- 用户提供的每个口播分句必须按原顺序完整出现一次。
- 参考图只迁移抽象视觉特征。人物身份、轮廓、姿势、道具、关系、取景和构图必须重新设计；禁止描摹、换色或原构图换角色。
- 默认将画面下方全宽 24% 预留给字幕。所有画面内容、阴影、区域框和笔尖路径都必须位于 `caption_safe_area.top_ratio` 以上。
- 手部系统与场景风格保持独立。必须把记录的马克笔笔尖锚点放在当前路径上，不能用手掌或手指代替笔尖。
- 每个动画像素只能在附近真实路径种子到达后出现。必须采用笔尖锁定时间、像素级边缘，禁止远处填色绽开、网格方块、拖尾淡入和通用擦除动画。
- 每个声明的对象必须画完后才能进入下一个对象。人物先完成浓密头发，再画该人物其余部分，之后再画其他人物或道具。禁止对整张画面施加全局“从上到下填色”顺序。
- 每个声明的书写组必须写完后才能离开。多行内容按从上到下，拉丁文字和公式按从左到右书写。
- 默认配音必须匹配正在说话的主角或旁白。人物性别改变后不得沿用旧项目声音。
- 每场必须以无手的完整定格结束；只有视觉证据和机器可读报告同时通过后才能交付。

## 3. 建立项目

收集口播、参考图、受众、画幅、分辨率、节奏、声音和交付要求。未指定时使用 16:9、1920×1080、24 fps 和便于路径识别的浅色背景。

在 TTS 之前确定 `narrator_gender`：

- 第一人称：匹配正在说话的主角。
- 第三人称且没有独立旁白：匹配主角。
- 存在独立旁白：匹配该旁白。
- 多主角或性别不明确：询问用户，不能根据次要角色猜测。

字段使用 `male` 或 `female`；用户明确指定的声音优先级高于 TTS reference 中的默认映射。

建立独立项目文件夹，包含 `narration.txt`、`storyboard.json`、`scenes/`、`assets/`、`audio/` 和 `output/`。只解析一次 skill 路径：

```bash
WHITEBOARD_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/hand-drawn-follow-animation"
```

创建初始项目；只有用户提供参考图时才加入 `--style-reference`：

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/whiteboard_renderer.py" create-project \
  --input /absolute/path/narration.txt \
  --output /absolute/path/storyboard.json \
  --narrator-gender <male-or-female> \
  --style-reference /absolute/path/reference.png
```

## 4. 设计分镜与素材

按语义切分场景，保持分句完整，并让每场只承担一个表达任务和一个具体视觉隐喻。替换所有 `TODO`。口播保存在项目字段中，不要变成画面文字；精确公式和符号使用程序绘制。

用户提供参考图时，先检查参考图，再复制到项目素材目录，记录 `visual_style: reference-adapted`，并保存一套稳定的 `style_profile`。没有参考图时使用 `editorial-character` 和自带风格锚点。

在消耗 ImageGen 调用前先向用户展示精简分镜方案。每个不同场景分别按目标画幅生成。保持背景均匀、重要边界清晰、全部内容避开字幕区，并确保场景中没有手、伪文字、Logo 或水印。出现畸形内容或不安全构图时重新生成。

人物部位或道具相连时使用有序 `object_regions`。公式和文字较多时使用 `base_image`、`draw_image` 与有序 `hand_regions`，让手只书写关键内容，不描绘静态框架。字段含义以 schema reference 为准。

除非用户明确要求更换外观，否则复用自带手部素材。需要更换时，单独在纯色抠像背景上生成并运行 `prepare-hand`；禁止把手直接生成到场景图中。

## 5. 建立权威时间轴

语义场景边界和旁白性别确定后，在渲染前合成 TTS：

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/edge_tts_pipeline.py" synthesize \
  /absolute/path/storyboard.json
```

以解码后的逐场音频时长和 Edge WordBoundary 时间戳为准。它们会覆盖文本估算时长，并生成 `audio/narration.m4a`、逐场音频和 `audio/narration.srt`。

如果用户提供本地 IndexTTS 或其他音色克隆流程，必须使用该指定声音及其最终音频/时间轴，不能静默回退到 Edge TTS。将引擎、音色参考标签、时间依据以及“只有分段时间戳”等限制记录在 `tts` 中。

## 6. 渲染并完成成片

检查运行环境；缺少依赖时，只在项目本地环境中安装检查器列出的包：

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/check_env.py"
```

渲染无声母版：

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/whiteboard_renderer.py" render \
  /absolute/path/storyboard.json \
  --output-dir /absolute/path/output
```

禁止用平移、缩放、溶解、通用手部循环或方向擦除代替计算出的绘制动作。证据不通过时，应修复源图、区域框、路径覆盖、阈值或笔尖锚点。

长视频渲染要保留已完成的场景片段和证据作为检查点。中断后留下的 0 字节或极小 MP4 不算完成；拼接前逐片段用 `ffprobe` 验证，只对缺失或无效场景安全补渲染。

混入口播并烧录权威字幕：

```bash
python3 "$WHITEBOARD_SKILL_DIR/scripts/edge_tts_pipeline.py" finish \
  /absolute/path/storyboard.json \
  --video /absolute/path/output/whiteboard-video.mp4 \
  --output /absolute/path/output/whiteboard-video-tts-subtitles.mp4
```

## 7. 验收与交付

检查每场路径预览、阶段图和 route JSON，再打开第一场片段与最终视频。通过 rendering reference 的全部验收项，至少满足：

- `caption_safe_area.unsafe_pixels == 0`，且处于允许误差内。
- `reveal_sync.mode == "nib-locked"`。
- `max_seed_distance_px <= limit_px`。
- `max_temporal_lag_frames <= 0.2`。
- 头发、对象和书写组均按声明顺序完整完成。
- 结尾至少保留 0.8 秒无手完整定格。
- 口播、字幕、场景切点、配音性别、媒体流、分辨率、帧率和时长均一致。

交付有声 MP4、无声母版、TTS 音频与定时 SRT、`storyboard.json`、代表性证据、`render-report.json` 和 `final-report.json`。说明时长、分辨率、帧率、音轨数、声音、时间依据和仍存在的限制。将 `audio/narration.srt` 标记为 TTS 定时字幕，将渲染器生成的 `output/narration.srt` 标记为估算字幕。

## 8. Remotion + React 封面生成

当用户要求科技封面、类似可灵 AI 的封面、Remotion/React 封面代码、独立的 3:4 与 4:3 输出，或指定 `npm` 封面渲染命令时，进入本分支。实现前完整阅读[Remotion + React reference](references/zh-CN/remotion-react.md)。如果用户同时要求手绘动画、TTS 或字幕，本分支只增加封面交付，不替代原有规则。

除非用户明确给出其他契约，否则使用以下默认契约：

| 项目 | 契约 |
| --- | --- |
| 组件 | `src/KlingAiCover.tsx` |
| Composition | `KlingAiThreeFourCover`、`KlingAiFourThreeCover` |
| 3:4 画布 | `900x1200` |
| 4:3 画布 | `1200x900` |
| 命令 | `npm run kling-ai:covers` |
| 输出 | `renders/kling-ai-cover-3x4.png`、`renders/kling-ai-cover-4x3.png` |

两个画幅必须分别设计，分别设置安全区、标题区、Hero 位置和间距。禁止通过裁切、拉伸或缩放其中一个画幅得到另一个。中文标题、数字、徽章、标签、描边、阴影和来源说明全部由 React/Remotion 渲染，确保文字准确且可编辑。如果使用 ImageGen 或其他模型生成视觉素材，只生成无文字背景或 Hero 视觉：禁止伪中文、随机字形、额外 Logo、水印、人物、平台 UI 和无关词语。

优先采用能满足简报的最小实现。新增自定义插画代码前，先检查项目现有组件、CSS 图形、SVG 基元和已有素材是否可复用。即使压缩代码，也不能删除对比度、输入校验、错误处理、安全和无障碍相关要求。中文标题或指标使用 `white-space: nowrap` 或明确控制的换行；不能依赖浏览器偶然换行。

实现后必须在实际 Remotion 项目目录执行指定 npm 命令，并检查两个真实 PNG。用 `ffprobe`（或等价图片探针）验证精确尺寸，分别检查全尺寸画面，再检查缩略图尺寸下的标题和数字可读性。TypeScript/build 通过不等于已经交付。报告组件、Composition ID、命令、输出路径、尺寸和视觉限制。将用户给出的完整 Kling AI 视觉提示词保存在 Remotion reference 中作为可复用提示词，但始终遵守“AI 只生成无文字视觉素材”的规则。

## 9. 生产经验与可复用恢复流程

阅读[references/zh-CN/production-lessons.md](references/zh-CN/production-lessons.md)，使用其中从真实生产失败中提炼的流程。内容包括输入与指令边界、独立项目范围、本地 IndexTTS 时间轴、短语级字幕修复、字幕带预检、中断后的安全恢复、Windows 执行、Git 选择性暂存，以及可以声称交付前必须具备的证据。

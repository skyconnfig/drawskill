# 项目 Schema v1

所有相对路径均以 `storyboard.json` 所在目录为基准。

## 目录

- 完整示例
- 字段
- 视觉风格
- 画布
- 风格与路径
- 手部
- 场景
- 时间归属

## 完整示例

```json
{
  "version": 1,
  "title": "咖啡渍为什么越擦越大",
  "visual_style": "reference-adapted",
  "style_reference": "assets/style-reference.png",
  "style_profile": {
    "medium": "略干的毡尖笔与少量平涂色",
    "line": "深色不均匀轮廓，带轻微压力变化",
    "palette": ["#fbf8ef", "#202426", "#d9865b", "#76aaa0"],
    "texture": "细纸张颗粒与偶尔不规则的填色边缘",
    "shape_language": "圆润简化主体与有棱角的图示强调",
    "shading": "少量平面阴影块",
    "density": "2–5 个大型主体和充足留白",
    "composition": "一个主关系与清晰方向流"
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
      "visual_prompt": "一滴咖啡落在干净衬衫上，用小型爆点强调接触。",
      "image": "scenes/scene-001.png"
    },
    {
      "id": "scene-002",
      "narration": "很多人第一反应是来回擦，但这会让污渍扩散。",
      "duration": 8.1,
      "visual_prompt": "一块布把小污渍擦成更大的污渍，中间用一个清晰箭头连接。",
      "image": "scenes/scene-002.png",
      "grid_cell": 10,
      "hold_seconds": 1.5
    }
  ]
}
```

## 字段

### 根字段

- `version`：必须为整数 `1`。
- `title`：简短项目名称。
- `visual_style`：有参考图时使用 `reference-adapted`，否则使用 `editorial-character`。
- `style_reference`：在 `reference-adapted` 项目中指向项目本地的参考图副本。
- `style_profile`：记录抽象媒介、线条、配色、纹理、形状语言、阴影、密度和构图特征；不能包含复制受保护人物、Logo、标志性道具、精确姿势或布局的指令。
- `narration`：完整保留用户口播。
- `narrator_gender`：使用 TTS 时必须为 `male` 或 `female`。第一人称匹配说话主角；第三人称没有独立旁白时匹配主角；不能根据次要角色推断。默认声音映射见 [tts-and-subtitles.md](tts-and-subtitles.md)。
- `speech_rate_cps`：中文估算语速，默认 `4.2`。
- `canvas`：全项目共用画布。
- `style`：路径检测和时间默认值。
- `hand`：透明马克笔手叠加层。
- `tts`：记录 TTS 管线、旁白性别、声音或非敏感的音色参考标识，以及权威音频/字幕路径。内置的 `edge_tts_pipeline.py synthesize` 写入 Edge 字段；本地 IndexTTS 或其他音色克隆脚本应写入等价字段。
- `scenes`：按最终播放顺序排列的场景。

### 视觉风格

- `reference-adapted`：只用 `style_reference` 中可迁移的工艺特征指导原创场景。
- `editorial-character`：友好编辑式讲解画风，可使用少量人物、物体、环境、图示和视觉隐喻。

渲染器不会分析或复制参考图；这些字段只用于 ImageGen 与视觉 QA。所有场景保持同一套 `style_profile`，同时重新设计主体和构图。

### 画布

- `width`、`height`：使用偶数，优先 1920×1080 或 1080×1920。
- `fps`：默认 24。
- `background`：接近静帧背景的六位十六进制颜色。
- `caption_safe_area`：默认启用，`top_ratio: 0.76`、`bottom_ratio: 1.0`。所有画面痕迹与路径都必须位于其上方；只有无字幕交付才可关闭。

### 风格与路径

- `grid_cell`：输出像素中的路径规划网格。可从 `width / 240` 开始（1920 宽时为 8）；浓密头发或印刷纹理填色使用 6。该字段只影响规划密度，最终揭示必须保持像素级边界。
- `ink_threshold`：把较暗像素识别为墨线。灰色轮廓丢失时提高；彩色填充被误判为墨线时降低。
- `content_distance`：与采样边缘背景的最小 RGB 距离。背景纹理触发空白路径时提高；浅色填充未出现时降低。
- `draw_ratio`、`color_ratio`：分配非定格时间，默认 2:1。
- `direct_draw`：一次绘制直接显示原色，不再重复上色；自然单次彩色绘制优先设为 `true`。
- `fill_route_stride`：`direct_draw` 下每隔 N 个规划行增加真实填色覆盖路径，默认 3。只有 `reveal_sync` 仍通过时才能增大。
- `max_reveal_radius_px`：动画像素到真实路径种子的硬距离上限。1920 宽可从 27 开始；6 px 网格可使用约 18。失败时修复覆盖，不能只放宽上限。
- `write_seconds`：`direct_draw` 下可见书写时间上限；剩余时间成为无手完整定格。
- `hold_seconds`：结尾无手定格，至少 0.8 秒。
- `paper_noise`：合成后确定性纸张纹理；纯净白板设为 0。

### 手部

- `image`：RGBA PNG 路径。
- `metadata`：`prepare-hand` 生成的 JSON，提供 `tip_anchor`。
- `tip_anchor`：可选的裁切图内归一化 `[x, y]` 坐标。
- `width_ratio`：手相对画布宽度的尺寸。自带底部进入手部可从 0.19 开始。

视觉风格改变时不要修改手部字段。参考图适配不影响手部锚点、路径顺序、揭示逻辑或进入方向。

### 场景

- `id`：稳定的零填充名称，如 `scene-001`。
- `narration`：该场完整口播分句。
- `duration`：合成前为估算秒数；选定 TTS 管线合成后为帧对齐权威时长。
- `audio`：可选的逐场 TTS 文件路径。
- `audio_duration`：可选的逐场音频解码原始时长。
- `visual_prompt`：ImageGen 场景说明；渲染前不得保留未完成占位内容。
- `image`：已批准最终静帧。
- `base_image`：从首帧可见的静态框架，可放标题、面板、坐标轴、网格、刻度、图示结构和辅助标签。
- `draw_image`：只含动态马克笔笔迹的干净路径源；渲染器从 `image` 揭示对应像素。
- `hand_regions`：有序 `[x1, y1, x2, y2]` 列表；一个区域内的完整文字或公式必须先完成。
- `object_regions`：人物与物体的有序矩形列表。重叠时前面的区域优先；人物先头发，再身体，再其他人物或道具。
- `grid_cell`、`ink_threshold`、`content_distance`、`draw_ratio`、`color_ratio`、`direct_draw`、`fill_route_stride`、`max_reveal_radius_px`、`write_seconds`、`hold_seconds`、`paper_noise`：只在修复具体场景时覆盖全局值。

分层场景要求 `image = base_image + draw_image 笔迹` 且坐标完全一致。每个 `hand_regions` 必须包含完整词、公式或有意组合的多行计算，同时不能包含无关书写。

字幕安全区是硬约束：最终图、区域框或路径进入该区域都会失败。浓密头发或相连对象必须使用 `object_regions`；未分配路径在所有声明区域完成后绘制。

## 时间归属

TTS 前，`speech_rate_cps` 只用于编辑估算；合成后，以最终解码音频和匹配的时间轴文件为准。Edge TTS 使用 `edge_tts_pipeline.py synthesize` 写入的字段；本地 IndexTTS 或其他管线应在 `tts` 中记录等价路径和时间基准。时间与字幕规则见 [tts-and-subtitles.md](tts-and-subtitles.md)。

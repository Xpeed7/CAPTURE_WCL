cd /Users/chenruiyan/2026-project/capture_wcl/bili2text

  # 转写 B 站视频
  uv run bili2text tx "https://www.bilibili.com/video/BV号"

  # 转写本地文件
  uv run bili2text tx ./my-video.mp4

  # 首次运行会弹出配置向导，也可手动运行
  uv run bili2text init

  按需安装额外引擎（当前只安装了核心依赖）：
  - uv sync --extra whisper — 本地 Whisper 模型
  - uv sync --extra sensevoice — 本地 SenseVoice 模型（中文效果好）
  - uv sync --extra volcengine — 火山引擎云端 API
  - uv sync --extra web — Web 界面

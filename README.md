# 大肥鱼桌宠

一个默认离线、轻量且注重隐私的 Windows 桌面宠物。它会散步、跟随鼠标、休息、冒泡说话，也能依据本机的前台应用、窗口标题、空闲时长与全屏状态给出低频的情境回应。

当前版本不接入云端模型，不截图，不读取浏览历史，也不会常驻录屏或监听语音。

## 预览

<p align="center">
  <img src="assets/previews/contact_sheet/runtime_states.png" alt="大肥鱼桌宠的状态动作总览" width="720">
</p>

<p align="center">
  <img src="assets/previews/gifs/walking.gif" alt="大肥鱼四帧侧向走路预览" width="260">
</p>

## 当前能力

- 透明、无边框、可置顶的 PySide6 桌宠窗口
- 统一角色图集：待机三视图、四帧侧面走路与十种互动/情绪姿势
- 数据驱动状态机：待机、发呆、走路、开心、说话、生气、被戳、吃东西、扫地、睡觉、抓取、落下、眩晕
- 帧播放器、动作优先级、无闪烁交叉淡化和轻量呼吸/反冲/弹跳等效果
- 单击、摸头、拖拽、双击喂食、托盘、鼠标穿透、开机自启
- 四种可配置的人格语气：标准、轻微毒舌、温和陪伴、社区梗
- 本地环境感知：前台进程名、窗口标题、用户空闲、全屏状态
- 本地规则识别 VS Code、GitHub、浏览器、B 站/YouTube、PDF/文档与 AI 对话页
- 15 秒停留去抖、全局与应用级台词冷却、全屏自动隐藏
- 默认隐私黑名单与自定义敏感进程；敏感窗口不会保留标题，也不会触发台词
- 轻量生命状态：心情、精力、无聊、亲密度、烦躁、眩晕与投喂次数

## 隐私边界

环境感知只在本机以低频方式读取当前前台窗口的元数据：

- 进程名
- 窗口标题（可关闭）
- 空闲时长（可关闭）
- 是否全屏

不会截图、不会读取网页正文、不会读取浏览历史、不会上传或持久化这些感知数据。密码管理器、支付/银行、远程桌面、聊天、邮件与无痕窗口默认被屏蔽；可在 config.json 的 privacy.custom_process_names 中继续添加进程名。

## 运行

推荐使用 Python 3.11 或更高版本。

    py -3.11 -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python main.py

双击 `启动大肥鱼桌宠.cmd` 可直接启动；重复点击会唤回已运行的同一只桌宠。右键桌宠会打开紧凑控制面板，可切换模式、大小、互动动作和环境感知选项。

## 动作素材状态

运行时采用一套统一的角色母版：待机保留干净三视图，开心、说话、吃东西、被戳、生气、扫地、睡觉、抓取、掉落和眩晕均使用同一角色身份的透明动作图。用户提供的付费姿势图保留为动作语义参考，不会在状态切换时混入另一套脸、服装细节或比例。

走路已是正式四帧侧视循环，不再是 `walk_side_placeholder`。原始帧为左向；向右走会在运行时逐帧镜像，因此两边的步态、服装和发型完全一致。预览见 `assets/previews/gifs/walking.gif` 与 `assets/previews/gifs/walk_side_candidate_a_8fps.gif`，素材状态说明见 `docs/WALK_ASSET_REQUEST.md`。

## 测试

    python -m unittest discover -s tests -v

这些测试覆盖应用分类、隐私规则、去抖事件、冷却策略、设置合并与生命状态持久化。它们不需要启动 GUI。

## 性能记录

可运行离屏渲染基准：

    python tools/measure_performance.py

结果会写入 `docs/PERFORMANCE_REPORT.md`，它只测量本地渲染与资源加载，不读取桌面内容。

启动桌宠后，可以用任务管理器查到对应 PID，再在另一个终端中记录空闲或移动状态下的 CPU 与内存：

    python tools/measure_runtime.py --pid 12345 --seconds 60 --output benchmarks/idle.json

这会只采样进程资源用量，不读取桌面内容。建议分别记录原地待着、自由散步、拖拽与全屏隐藏四种场景，作为后续功能迭代的性能门槛。

## 素材预处理

把 正面.png、侧面.png、背面.png 放入一个输入目录后：

    python preprocess.py path\to\raw-images
    python preprocess2.py sprites --output-dir sprites

两个脚本均使用相对项目路径和命令行参数，不再依赖作者机器上的绝对路径。

## 打包

安装 PyInstaller 后可执行：

    pyinstaller --noconfirm --onefile --windowed --name 大肥鱼桌宠 --add-data "sprites;sprites" --add-data "assets;assets" --icon icon.ico main.py

生成的程序位于 dist 目录。

## 目录概览

    app/          启动入口与运行时路径
    pet/          窗口、渲染、动画、移动、互动、生命状态
    awareness/    Windows 前台窗口、空闲、全屏与隐私过滤
    behavior/     应用分类、事件去抖、冷却与反应决策
    dialogue/     本地规则与人格调度
    assets/       分类、隐私和台词资源
    settings/     JSON 配置管理
    tests/        不依赖 GUI 的单元测试

## 开发路线

当前实现覆盖工程模块化与本地环境感知 MVP。后续可以在不破坏离线默认和隐私边界的前提下，继续完善抚摸/抛掷物理、设置窗口、浏览器扩展，以及用户明确授权后的可选 AI 页面理解。

## 协议与来源

本项目基于 1190fasheqi/dafeiyu-pet 的 MIT 许可桌宠底座进行模块化重构和增量开发。原始许可证保留在 LICENSE，具体来源见 CREDITS.md。

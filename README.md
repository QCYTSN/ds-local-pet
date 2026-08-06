# 大肥鱼桌宠

一个默认离线、轻量且注重隐私的 Windows 桌面宠物。它会散步、跟随鼠标、休息、冒泡说话，也能依据本机的前台应用、窗口标题、空闲时长与全屏状态给出低频的情境回应。

当前版本不接入云端模型，不截图，不读取浏览历史，也不会常驻录屏或监听语音。

## 当前能力

- 透明、无边框、可置顶的 PySide6 桌宠窗口
- 正面、侧面、背面三视图；散步、跟随鼠标、原地待着
- 呼吸、摇摆、蹦跳、进食与转向淡化动画
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

也可以双击 启动桌宠.bat。旧的 桌宠.py 保留为兼容入口，会转到新的 main.py。

右键桌宠可切换活动模式、大小与互动设置；环境感知菜单可单独关闭标题读取、空闲检测和全屏自动隐藏。

## 测试

    python -m unittest discover -s tests -v

这些测试覆盖应用分类、隐私规则、去抖事件、冷却策略、设置合并与生命状态持久化。它们不需要启动 GUI。

## 性能记录

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

# 动画系统架构

## 目标

动画、素材选择、状态转换和窗口移动分离。动作系统只加载预生成 PNG 与 PySide6 `QPixmap`，不运行图像模型、不截图；联网仅由独立、可关闭的版本检查器负责。

## 模块

- `animation.asset_registry`：读取 `actions.json`，按桌宠尺寸缓存 `QPixmap`。
- `animation.clip`：定义 clip、frame、锚点，以及 enter/body/exit 动作协议。
- `animation.player`：推进动作分段与帧时间、处理安全的同素材淡化，输出当前精灵图。
- `animation.effects`：参数化轻微呼吸、思考摇摆、真实行走帧播放、反冲、弹跳、进食、眩晕等效果。
- `animation.state_machine`：处理动作优先级、中断、有限动作超时返回与拖拽强制中断。
- `animation.transitions`：封装不闪烁的交叉淡化。
- `pet.physics`：独立处理抛掷速度、重力、屏幕/窗口表面碰撞、反弹、摩擦与落地判定。
- `pet.surfaces`：只读取窗口矩形，管理窗口顶部平台、落脚附着、窗口随动和表面行走边界。

## 状态

`IDLE`、`BLINK`、`GLANCE`、`THINKING`、`WALKING`、`HAPPY`、`HEAD_PAT`、`TALKING`、`ANGRY`、`POKE_REACT`、`TAIL_REACT`、`EATING`、`SWEEPING`、`SLEEPING`、`DRAGGING`、`FALLING`、`LANDING`、`DIZZY`。

`WALKING` 现为正式左右双套四帧侧面循环。每个方向都有接地/经过/反向接地/抬步帧，并在进入和退出时播放独立起步、刹停过渡；右向不再镜像左向，蝴蝶结、围裙图案和发饰保持解剖位置。

`BLINK`、`GLANCE` 由独立微动作调度器触发，不计作一次完整活动；`HEAD_PAT` 与 `POKE_REACT` 使用连续实帧表达互动过程。完整活动默认间隔显著拉长，主动说话另有长冷却，避免桌宠常驻时显得忙乱。

自动散步只改变水平坐标并保持当前表面脚底基线。拖拽释放后才转交给 `ThrowPhysics` 改变纵向坐标；轻落地播放压身恢复，重摔在落地动作后进入眩晕。普通窗口顶部会作为单向水平平台接住从上方落下的角色；落脚后按相对位置随窗口移动，窗口消失时重新交给重力。快速横甩会在工作区边缘减速反弹，速度和单帧积分均有限制。

## 锚点

站立状态以脚底中点为 ground anchor；睡眠、眩晕、拖拽与掉落均使用独立非地面锚点。渲染时会把这些状态置于精灵槽中央，因此抓取不会再只露出脑袋，睡姿也不会被强压到地面基线。

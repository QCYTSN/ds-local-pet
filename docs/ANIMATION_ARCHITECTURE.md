# 动画系统架构

## 目标

动画、素材选择、状态转换和窗口移动分离。运行时只加载预生成 PNG 与 PySide6 `QPixmap`，不运行图像模型、不截图、不访问网络。

## 模块

- `animation.asset_registry`：读取 `actions.json`，按桌宠尺寸缓存 `QPixmap`。
- `animation.clip`：定义 clip、frame、锚点与动作请求的数据结构。
- `animation.player`：推进帧时间、处理交叉淡化，输出当前与上一张精灵图。
- `animation.effects`：参数化轻微呼吸、思考摇摆、真实行走帧播放、反冲、弹跳、进食、眩晕等效果。
- `animation.state_machine`：处理动作优先级、中断、有限动作超时返回与拖拽强制中断。
- `animation.transitions`：封装不闪烁的交叉淡化。

## 状态

`IDLE`、`THINKING`、`WALKING`、`HAPPY`、`TALKING`、`ANGRY`、`POKE_REACT`、`EATING`、`SWEEPING`、`SLEEPING`、`DRAGGING`、`FALLING`、`DIZZY`。

`WALKING` 现为正式四帧侧面循环。它通过四张独立的接地/经过/反向接地/抬步帧在 8 FPS 左右循环，向右时由运行时镜像；程序化效果只做极轻微的重心补充，不再把整张侧面立绘平移冒充走路。

## 锚点

站立状态以脚底中点为 ground anchor；睡眠、眩晕、拖拽与掉落均使用独立非地面锚点。渲染时会把这些状态置于精灵槽中央，因此抓取不会再只露出脑袋，睡姿也不会被强压到地面基线。

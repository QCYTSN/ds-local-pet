# 素材处理报告

## 当前运行时美术策略

正式显示素材统一采用同一套生成角色母版。它以干净三视图为身份校准，并用统一绿幕动作表补齐表情、互动与走路。用户提供的付费状态图保留在原始素材目录，仅用于动作语义参考；没有被裁入、混入或覆盖到运行时图集中。

## 已处理的运行时资产

- `idle_front`：clean_base_view，1 帧，来源 `assets/processed/masters/front_base.png`
- `idle_think`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/idle_think.png`
- `idle_back`：clean_base_view，1 帧，来源 `assets/processed/masters/back_base.png`
- `walk_side`：formal_unified_generated_walk_frames，4 帧，来源 `assets/processed/masters/generated/walk_side_00.png, assets/processed/masters/generated/walk_side_01.png, assets/processed/masters/generated/walk_side_02.png, assets/processed/masters/generated/walk_side_03.png`
- `happy`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/happy.png`
- `talk`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/talk.png`
- `angry`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/angry.png`
- `poke_react`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/poke_react.png`
- `eat`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/eat.png`
- `sweep`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/sweep.png`
- `sleep`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/sleep.png`
- `dizzy`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/dizzy.png`
- `dragging`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/dragging.png`
- `falling`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/falling.png`

## 提取与规范化

- 绿色键控背景在资产制作阶段去除，输出为透明 PNG；运行时不加载图像模型。
- 走路四帧共享缩放比例、透明画布和脚底基线。
- 睡眠、眩晕、抓取和掉落使用各自的视觉尺度与锚点，不强行拉成站立高度。
- 单独悬浮的提示符号会在键控后作为非主体透明岛剔除；角色本体不做内容重绘。

# 素材处理报告

## 当前运行时美术策略

正式显示素材统一采用同一套生成角色母版。它以干净三视图为身份校准，并用统一绿幕动作表补齐表情、互动与走路。用户提供的付费状态图保留在原始素材目录，仅用于动作语义参考；没有被裁入、混入或覆盖到运行时图集中。

## 已处理的运行时资产

- `idle_front`：formal_unified_generated_idle_base，1 帧，来源 `assets/processed/masters/generated/idle_front.png`
- `idle_blink`：formal_unified_generated_micro_frames，5 帧，来源 `assets/processed/masters/generated/idle_blink_00.png, assets/processed/masters/generated/idle_blink_01.png, assets/processed/masters/generated/idle_blink_02.png, assets/processed/masters/generated/idle_blink_03.png, assets/processed/masters/generated/idle_blink_04.png`
- `idle_glance`：formal_unified_generated_micro_frames，7 帧，来源 `assets/processed/masters/generated/idle_glance_00.png, assets/processed/masters/generated/idle_glance_01.png, assets/processed/masters/generated/idle_glance_02.png, assets/processed/masters/generated/idle_glance_03.png, assets/processed/masters/generated/idle_glance_04.png, assets/processed/masters/generated/idle_glance_05.png, assets/processed/masters/generated/idle_glance_06.png`
- `idle_think`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/idle_think.png`
- `idle_back`：clean_base_view，1 帧，来源 `assets/processed/masters/back_base.png`
- `walk_side_stand`：clean_base_view，1 帧，来源 `assets/processed/masters/side_base.png`
- `walk_side`：formal_unified_generated_walk_frames，4 帧，来源 `assets/processed/masters/generated/walk_side_00.png, assets/processed/masters/generated/walk_side_01.png, assets/processed/masters/generated/walk_side_02.png, assets/processed/masters/generated/walk_side_03.png`
- `walk_side_right`：formal_unified_generated_walk_frames_directional，4 帧，来源 `assets/processed/masters/generated/walk_side_right_00.png, assets/processed/masters/generated/walk_side_right_01.png, assets/processed/masters/generated/walk_side_right_02.png, assets/processed/masters/generated/walk_side_right_03.png`
- `walk_start_left`：formal_unified_generated_locomotion_transition，2 帧，来源 `assets/processed/masters/generated/walk_start_left_00.png, assets/processed/masters/generated/walk_start_left_01.png`
- `walk_stop_left`：formal_unified_generated_locomotion_transition，2 帧，来源 `assets/processed/masters/generated/walk_stop_left_00.png, assets/processed/masters/generated/walk_stop_left_01.png`
- `walk_start_right`：formal_unified_generated_locomotion_transition，2 帧，来源 `assets/processed/masters/generated/walk_start_right_00.png, assets/processed/masters/generated/walk_start_right_01.png`
- `walk_stop_right`：formal_unified_generated_locomotion_transition，2 帧，来源 `assets/processed/masters/generated/walk_stop_right_00.png, assets/processed/masters/generated/walk_stop_right_01.png`
- `happy`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/happy.png`
- `head_pat`：formal_unified_generated_interaction_frames，6 帧，来源 `assets/processed/masters/generated/head_pat_00.png, assets/processed/masters/generated/head_pat_01.png, assets/processed/masters/generated/head_pat_02.png, assets/processed/masters/generated/head_pat_03.png, assets/processed/masters/generated/head_pat_04.png, assets/processed/masters/generated/head_pat_05.png`
- `talk`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/talk.png`
- `angry`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/angry.png`
- `poke_react`：formal_unified_generated_interaction_frames，4 帧，来源 `assets/processed/masters/generated/poke_react_00.png, assets/processed/masters/generated/poke_react_01.png, assets/processed/masters/generated/poke_react_02.png, assets/processed/masters/generated/poke_react_03.png`
- `tail_react`：formal_unified_generated_interaction_frames，4 帧，来源 `assets/processed/masters/generated/tail_react_00.png, assets/processed/masters/generated/tail_react_01.png, assets/processed/masters/generated/tail_react_02.png, assets/processed/masters/generated/tail_react_03.png`
- `eat`：formal_unified_generated_daily_frames，3 帧，来源 `assets/processed/masters/generated/eat_00.png, assets/processed/masters/generated/eat_01.png, assets/processed/masters/generated/eat_02.png`
- `sweep`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/sweep.png`
- `sleep`：formal_unified_generated_sleep_base，1 帧，来源 `assets/processed/masters/generated/sleep.png`
- `sleep_enter`：formal_unified_generated_sleep_transition，3 帧，来源 `assets/processed/masters/generated/sleep_enter_00.png, assets/processed/masters/generated/sleep_enter_01.png, assets/processed/masters/generated/sleep_enter_02.png`
- `sleep_wake`：formal_unified_generated_sleep_transition，3 帧，来源 `assets/processed/masters/generated/sleep_wake_00.png, assets/processed/masters/generated/sleep_wake_01.png, assets/processed/masters/generated/sleep_wake_02.png`
- `dizzy`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/dizzy.png`
- `dragging`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/dragging.png`
- `falling`：formal_unified_generated_action，1 帧，来源 `assets/processed/masters/generated/falling.png`
- `released_airborne`：formal_unified_generated_throw_transition，1 帧，来源 `assets/processed/masters/generated/released_airborne.png`
- `landing`：formal_unified_generated_landing_frames，3 帧，来源 `assets/processed/masters/generated/landing_00.png, assets/processed/masters/generated/landing_01.png, assets/processed/masters/generated/landing_02.png`

## 提取与规范化

- 绿色键控背景在资产制作阶段去除，输出为透明 PNG；运行时不加载图像模型。
- 走路四帧共享缩放比例、透明画布和脚底基线。
- 睡眠、眩晕、抓取和掉落使用各自的视觉尺度与锚点，不强行拉成站立高度。
- 单独悬浮的提示符号会在键控后作为非主体透明岛剔除；角色本体不做内容重绘。

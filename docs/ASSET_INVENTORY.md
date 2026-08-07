# 角色素材盘点

本报告来自逐图视觉核验与元数据扫描。原始图片均保留在 `sprites/`，没有被改名、移动或覆盖。

## 结论

- 三视图（正面、侧面、背面）是干净透明底，可作为正式资产管线的基础参考。
- 十张付费状态图已获用户授权；为避免状态切换时角色细节跳变，它们只用于学习动作语义，最终运行时改用统一角色图集。
- `抓取.png` 实际是受惊起跳，不适合作为被抓起或拖拽状态。
- 侧面图是静态站姿，不是走路帧；正式运行时已接入统一角色的四帧侧视走路循环。

## 逐图记录

| 文件 | 逻辑名 | 姿势 / 表情 | 建议状态 | 可直接使用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `sprites/icon.png` | `app_icon` | icon / na | None | False | 非角色状态资产。 |
| `sprites/侧面.png` | `side_base` | standing / neutral | walk_direction_reference | True | 干净透明底三视图主参考；不是实际走路帧，正式四帧走路另行接入。 |
| `sprites/侧面_187.png` | `legacy_runtime_侧面_187` | legacy_runtime / neutral | None | True | 保留兼容性，不作为新资产管线的源文件。 |
| `sprites/侧面_238.png` | `legacy_runtime_侧面_238` | legacy_runtime / neutral | None | True | 保留兼容性，不作为新资产管线的源文件。 |
| `sprites/侧面_306.png` | `legacy_runtime_侧面_306` | legacy_runtime / neutral | None | True | 保留兼容性，不作为新资产管线的源文件。 |
| `sprites/发呆.png` | `think_source_candidate` | standing / thinking | idle_think | False | 用户授权的思考姿势参考；为保持统一角色身份，仅学习动作语义，不直接作为运行时图。 |
| `sprites/吃东西.png` | `eat_source_candidate` | standing_with_prop / focused_happy | eat | False | 用户授权的进食姿势参考；仅学习动作语义，不直接作为运行时图。 |
| `sprites/开心.png` | `happy_source_candidate` | standing / happy | happy | False | 用户授权的开心姿势参考；仅学习动作语义，不直接作为运行时图。 |
| `sprites/扫地.png` | `sweep_source_candidate` | standing_with_prop / focused | sweep | False | 用户授权的扫地姿势参考；扫帚扩大画面边界，运行时改用统一角色图集。 |
| `sprites/抓取.png` | `surprised_jump_source_candidate` | jumping / surprised | poke_react | False | 文件名“抓取”与实际画面不一致，更接近受惊起跳；仅作为互动动作语义参考。 |
| `sprites/正面.png` | `front_base` | standing / neutral | idle_front | True | 干净透明底三视图主参考。 |
| `sprites/正面_187.png` | `legacy_runtime_正面_187` | legacy_runtime / neutral | None | True | 保留兼容性，不作为新资产管线的源文件。 |
| `sprites/正面_238.png` | `legacy_runtime_正面_238` | legacy_runtime / neutral | None | True | 保留兼容性，不作为新资产管线的源文件。 |
| `sprites/正面_306.png` | `legacy_runtime_正面_306` | legacy_runtime / neutral | None | True | 保留兼容性，不作为新资产管线的源文件。 |
| `sprites/生气.png` | `angry_source_candidate` | standing / angry | angry | False | 用户授权的生气姿势参考；仅学习动作语义，不直接作为运行时图。 |
| `sprites/眩晕.png` | `dizzy_source_candidate` | seated / dizzy | dizzy | False | 用户授权的眩晕姿势参考；坐姿不能按站立高度归一化，运行时改用统一角色图集。 |
| `sprites/睡觉.png` | `sleep_source_candidate` | sleeping / sleeping | sleep | False | 用户授权的睡姿参考；睡姿与站姿锚点不同，运行时改用统一角色图集。 |
| `sprites/背面.png` | `back_base` | standing / not_visible | idle_back | True | 干净透明底三视图主参考。 |
| `sprites/背面_187.png` | `legacy_runtime_背面_187` | legacy_runtime / neutral | None | True | 保留兼容性，不作为新资产管线的源文件。 |
| `sprites/背面_238.png` | `legacy_runtime_背面_238` | legacy_runtime / neutral | None | True | 保留兼容性，不作为新资产管线的源文件。 |
| `sprites/背面_306.png` | `legacy_runtime_背面_306` | legacy_runtime / neutral | None | True | 保留兼容性，不作为新资产管线的源文件。 |
| `sprites/被戳.png` | `poke_source_candidate` | standing / hurt_or_annoyed | poke_react | False | 用户授权的被戳姿势参考；仅学习动作语义，不直接作为运行时图。 |
| `sprites/说话.png` | `talk_source_candidate` | standing / talking | talk | False | 用户授权的说话姿势参考；仅学习动作语义，不直接作为运行时图。 |

完整机器可读记录见 `assets/manifests/source_inventory.json`。

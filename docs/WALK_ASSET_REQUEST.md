# 侧面走路素材状态

当前已接入左右独立的正式四帧侧视走路循环。左向来源为 `assets/candidates/walk_side/candidate_a/`，右向与起停过渡位于 `assets/candidates/state_actions/candidate_g_motion2/`。运行时文件位于 `assets/processed/runtime/states/walk_side*`。

四帧分别覆盖接地、经过、反向接地和抬步；所有帧在归一化时共享画布、比例和脚底基线。左右向各自保留固定配饰位置，并通过两帧起步与两帧刹停动作衔接待机。

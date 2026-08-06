# 侧面走路素材状态

当前已接入正式四帧侧视走路循环，来源为用户认可的统一绿幕角色图集：`assets/candidates/walk_side/candidate_a/`。运行时文件位于 `assets/processed/runtime/states/walk_side/`，8 FPS 预览位于 `assets/previews/gifs/walk_side_candidate_a_8fps.gif`。

四帧分别覆盖接地、经过、反向接地和抬步；所有帧在归一化时共享画布、比例和脚底基线。左向使用原始左向帧，右向由运行时镜像。后续若请画师精修，应保持这一组的角色身份和四帧节奏，不是当前版本的阻塞项。

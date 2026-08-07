# 来源与致谢

本项目以 1190fasheqi/dafeiyu-pet 为桌宠表现与基础交互底座。

## 上游代码

- 上游仓库：https://github.com/1190fasheqi/dafeiyu-pet
- 导入基线提交：2822f8f215e34f3177c00b1fb6c0d073eefdea31
- 上游许可证：MIT

上游的 LICENSE 已原样保留在本仓库根目录。

## 本项目新增部分（代码）

以下为本项目在上游基线之上新增或重写的代码，同样按 MIT 许可证发布：

- `app/`、`animation/`、`pet/`、`awareness/`、`behavior/`、`dialogue/`、`settings/` 的模块化架构
- 本地环境感知与隐私过滤
- 本地台词与人格调度（`assets/dialogue/*.json` 文本内容）
- 素材管线与校验工具（`tools/`）、单元测试（`tests/`）、发布打包脚本与 CI 配置

本项目不会复制 GPL 项目的实现代码；如参考其他桌宠项目，仅参考交互或架构思路并遵守其各自许可证。

## 视觉资产不在本文件的授权范围内

本文件只说明**代码**来源与代码许可证边界。

角色视觉素材（`sprites/`、`assets/processed/`、`assets/candidates/`、
`assets/previews/` 中的图像内容）**不适用**上游的 MIT 代码许可证，也不因经过
本项目管线处理而自动转为 MIT。其来源说明与授权条件统一见
[ASSET_LICENSE.md](ASSET_LICENSE.md)。

其中三视图基础角色图（`sprites/正面.png`、`sprites/侧面.png`、`sprites/背面.png`
及其缩放版本）随上游基线提交 `2822f8f` 一并导入，上游将其描述为二创角色美术。

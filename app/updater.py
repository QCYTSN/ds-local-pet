"""Small GitHub Releases updater with SHA-256 verification."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal


GITHUB_REPOSITORY = "QCYTSN/ds-local-pet"
GITHUB_API_VERSION = "2026-03-10"
INSTALLER_NAME_RE = re.compile(r"^DS-Local-Pet-Setup-v([0-9]+(?:\.[0-9]+){2})\.exe$")


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    version: str
    tag_name: str
    page_url: str
    download_url: str
    installer_name: str
    sha256: str
    size: int


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value).strip())
    if match is None:
        raise ValueError(f"invalid semantic version: {value}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def parse_release(payload: object, *, current_version: str) -> UpdateInfo | None:
    if not isinstance(payload, dict):
        raise UpdateError("GitHub 返回了无法识别的更新信息。")
    tag_name = str(payload.get("tag_name") or "")
    try:
        latest_version = version_tuple(tag_name)
        installed_version = version_tuple(current_version)
    except ValueError as error:
        raise UpdateError("发布版本号格式不正确。") from error
    if latest_version <= installed_version:
        return None

    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("新版本没有可下载的安装包。")
    candidates: list[dict[str, Any]] = []
    for raw in assets:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "")
        match = INSTALLER_NAME_RE.fullmatch(name)
        if match is not None and version_tuple(match.group(1)) == latest_version:
            candidates.append(raw)
    if len(candidates) != 1:
        raise UpdateError("新版本缺少唯一、可验证的 Windows 安装包。")

    asset = candidates[0]
    digest = str(asset.get("digest") or "")
    if not digest.lower().startswith("sha256:"):
        raise UpdateError("安装包缺少 GitHub 提供的 SHA-256 摘要，已停止更新。")
    sha256 = digest.split(":", 1)[1].strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise UpdateError("安装包的 SHA-256 摘要无效。")
    download_url = str(asset.get("browser_download_url") or "")
    if not download_url.startswith("https://github.com/"):
        raise UpdateError("安装包下载地址不受信任。")
    return UpdateInfo(
        version=".".join(str(part) for part in latest_version),
        tag_name=tag_name,
        page_url=str(payload.get("html_url") or ""),
        download_url=download_url,
        installer_name=str(asset["name"]),
        sha256=sha256,
        size=max(0, int(asset.get("size") or 0)),
    )


class UpdateClient:
    def __init__(
        self,
        *,
        current_version: str,
        updates_dir: Path,
        repository: str = GITHUB_REPOSITORY,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.current_version = current_version
        self.updates_dir = Path(updates_dir)
        self.repository = repository
        self.timeout_seconds = timeout_seconds

    def check_latest(self) -> UpdateInfo | None:
        url = f"https://api.github.com/repos/{self.repository}/releases/latest"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"DaFeiYu-Desktop-Pet/{self.current_version}",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise UpdateError(f"检查更新失败（HTTP {error.code}）。") from error
        except (OSError, ValueError, urllib.error.URLError) as error:
            raise UpdateError("暂时无法连接 GitHub 检查更新。") from error
        return parse_release(payload, current_version=self.current_version)

    def download(self, info: UpdateInfo) -> Path:
        self.updates_dir.mkdir(parents=True, exist_ok=True)
        target = self.updates_dir / info.installer_name
        partial = target.with_suffix(target.suffix + ".part")
        hasher = hashlib.sha256()
        request = urllib.request.Request(
            info.download_url,
            headers={"User-Agent": f"DaFeiYu-Desktop-Pet/{self.current_version}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30.0) as response, partial.open("wb") as out:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    out.write(chunk)
            if hasher.hexdigest().lower() != info.sha256:
                raise UpdateError("下载完成，但安装包校验失败，文件已丢弃。")
            partial.replace(target)
            return target
        except (OSError, urllib.error.URLError) as error:
            raise UpdateError("下载安装包失败，请稍后重试。") from error
        finally:
            if partial.exists():
                try:
                    partial.unlink()
                except OSError:
                    pass


class UpdateService(QObject):
    """Run network and hashing work away from the Qt UI thread."""

    checked = Signal(object, bool)
    check_failed = Signal(str, bool)
    downloaded = Signal(object, object)
    download_failed = Signal(str)

    def __init__(self, client: UpdateClient, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self._checking = False
        self._downloading = False

    def check_async(self, *, manual: bool = False) -> bool:
        if self._checking:
            return False
        self._checking = True

        def work() -> None:
            try:
                self.checked.emit(self.client.check_latest(), manual)
            except UpdateError as error:
                self.check_failed.emit(str(error), manual)
            finally:
                self._checking = False

        threading.Thread(target=work, name="dafeiyu-update-check", daemon=True).start()
        return True

    def download_async(self, info: UpdateInfo) -> bool:
        if self._downloading:
            return False
        self._downloading = True

        def work() -> None:
            try:
                self.downloaded.emit(info, self.client.download(info))
            except UpdateError as error:
                self.download_failed.emit(str(error))
            finally:
                self._downloading = False

        threading.Thread(target=work, name="dafeiyu-update-download", daemon=True).start()
        return True


def launch_installer(path: Path) -> None:
    if sys.platform != "win32":
        raise UpdateError("自动安装目前仅支持 Windows。")
    installer = Path(path).resolve()
    if not installer.is_file() or not INSTALLER_NAME_RE.fullmatch(installer.name):
        raise UpdateError("更新安装包不存在或文件名无效。")
    subprocess.Popen(
        [
            str(installer),
            "/SILENT",
            "/SP-",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
            "/RESTARTAPPLICATIONS",
        ],
        close_fds=True,
    )

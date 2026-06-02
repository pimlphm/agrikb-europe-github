# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = Path.home() / "Desktop"
PACKAGE_PARENT = DESKTOP / "AgriKB_TrustedPC_OneClick_20260525"
PACKAGE_ROOT = PACKAGE_PARENT / "AgriKB_TrustedPC_OneClick"
ZIP_PATH = DESKTOP / "AgriKB_TrustedPC_OneClick_20260525.zip"
PY_EMBED_ZIP = ROOT / "runtime" / "python-3.11.9-embed-amd64.zip"


ROOT_FILES = [
    ".env",
    ".env.example",
    "config.yaml",
    "requirements-runtime.txt",
    "README.md",
    "README_AGRIKB.md",
    "README_运行说明.md",
    "FINAL_DELIVERY_README.md",
    "RUN_AGRIKB.bat",
    "Start-TrustedPC.ps1",
    "Test-TrustedPC.ps1",
    "Start-Portable.ps1",
    "Start-Mobile-Test.ps1",
    "Setup-NewComputer.ps1",
    "Configure-ApiKey.ps1",
    "Uninstall-AgriKB.ps1",
    "Fix-Mobile-WiFi-Access.ps1",
    "一键启动AgriKB_可信电脑.bat",
    "一键卸载AgriKB.bat",
    "一键修复手机扫码访问.bat",
    "卸载说明.md",
    "手机扫码测试.bat",
    "配置API密钥.bat",
]

DIRS = [
    ".venv",
    "src",
    "web",
    "data",
    "knowledge",
    "models",
    "original_data",
    "docs",
    "deliverables",
    "tools",
    "core",
    "runtime",
]


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_rmtree(path: Path) -> None:
    if not path.exists():
        return
    if not is_within(path, DESKTOP) or "AgriKB_TrustedPC_OneClick_20260525" not in str(path):
        raise RuntimeError(f"Refusing to remove unexpected path: {path}")

    def handle_remove_error(func, target, exc_info):
        try:
            os.chmod(target, 0o700)
            func(target)
        except Exception:
            raise exc_info[1]

    shutil.rmtree(path, onerror=handle_remove_error)


def ignore_patterns(dir_name: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        lower = name.lower()
        if lower in {
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            "__pycache__",
            "chrome-profile",
            "chrome-record-profile",
            "release_packages",
        }:
            ignored.add(name)
        elif lower.endswith((".pyc", ".pyo", ".log", ".tmp")):
            ignored.add(name)
        elif lower in {"server.out.log", "server.err.log", "server-8010.out.log", "server-8010.err.log"}:
            ignored.add(name)
        elif lower in {"test-query-response.json", "voice_stt_test.wav", "voice_stt_test.webm"}:
            ignored.add(name)
    return ignored


def copy_tree(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copytree(src, dst, ignore=ignore_patterns, dirs_exist_ok=True)


def copy_root_files() -> list[str]:
    copied: list[str] = []
    for name in ROOT_FILES:
        src = ROOT / name
        if src.exists():
            dst = PACKAGE_ROOT / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(name)
    return copied


def extract_embedded_python() -> Path:
    if not PY_EMBED_ZIP.exists():
        raise FileNotFoundError(f"Missing Python embeddable runtime: {PY_EMBED_ZIP}")
    target = PACKAGE_ROOT / "runtime" / "python311"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PY_EMBED_ZIP) as zf:
        zf.extractall(target)
    pth_files = list(target.glob("python*._pth"))
    if pth_files:
        pth_files[0].write_text(
            "\n".join([
                "python311.zip",
                ".",
                "..\\..",
                "..\\..\\.venv\\Lib\\site-packages",
                "import site",
                "",
            ]),
            encoding="utf-8",
        )
    return target / "python.exe"


def write_release_notes(python_exe: Path) -> None:
    note = PACKAGE_ROOT / "README_可信电脑一键启动.md"
    note.write_text(
        "\n".join([
            "# AgriKB 可信电脑一键启动包",
            "",
            f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "- 使用方式：解压后双击 `一键启动AgriKB_可信电脑.bat`。",
            "- 自检方式：双击或运行 `Test-TrustedPC.ps1`，默认使用 8095 端口做健康检查。",
            "- 默认地址：`http://127.0.0.1:8010/ui/?v=20260525agri93`。",
            "- 本包包含 Windows embeddable Python 3.11.9、项目虚拟环境依赖、知识库、数据、PPT、视频和交付文档。",
            "- `.env` 内含本地模型与 API 配置，只能在可信电脑上使用，不要上传到公开仓库或外发给无关人员。",
            "- 手机扫码测试请先确认同一 Wi-Fi 未开启客户端隔离；如酒店网络阻断局域网访问，可改用手机热点或运行防火墙修复脚本。",
            "",
            "## 包内关键文件",
            "",
            "- `Start-TrustedPC.ps1`：正式启动。",
            "- `Test-TrustedPC.ps1`：解压后自检。",
            "- `Fix-Mobile-WiFi-Access.ps1`：以管理员权限添加局域网端口访问规则。",
            "- `deliverables/AgriKB_DualTrack_FirstPrize_Materials_20260523/`：路演 PPT、视频、产品说明、项目介绍、专利申请书和软著材料。",
            "- `runtime/python311/python.exe`：便携 Python 运行时。",
            "- `.venv/Lib/site-packages/`：运行依赖包。",
            "",
            "## 常见处理",
            "",
            "- 如果 8010 端口被占用，运行：`powershell -ExecutionPolicy Bypass -File .\\Start-TrustedPC.ps1 -Port 8020`。",
            "- 如果手机扫码打不开，确认手机和电脑在同一 Wi-Fi，并允许 Windows 防火墙访问本地网络。",
            "- 如果酒店 Wi-Fi 阻断设备互访，建议改用手机热点、路由器或局域网直连。",
            f"- 便携 Python 路径：`{python_exe.relative_to(PACKAGE_ROOT)}`。",
        ]),
        encoding="utf-8",
    )


def zip_package() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
        for path in PACKAGE_ROOT.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(PACKAGE_PARENT))


def main() -> None:
    safe_rmtree(PACKAGE_PARENT)
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    copied_root_files = copy_root_files()
    for dirname in DIRS:
        copy_tree(ROOT / dirname, PACKAGE_ROOT / dirname)
    python_exe = extract_embedded_python()
    write_release_notes(python_exe)
    manifest = {
        "package_root": str(PACKAGE_ROOT),
        "zip_path": str(ZIP_PATH),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "contains_private_env": (PACKAGE_ROOT / ".env").exists(),
        "python": str(python_exe),
        "ui_version": "20260525agri93",
        "copied_root_files": copied_root_files,
        "launchers": [
            "一键启动AgriKB_可信电脑.bat",
            "Start-TrustedPC.ps1",
            "Test-TrustedPC.ps1",
        ],
        "materials_dir": "deliverables/AgriKB_DualTrack_FirstPrize_Materials_20260523",
    }
    (PACKAGE_ROOT / "trusted_pc_package_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    zip_package()
    manifest["zip_size_mb"] = round(ZIP_PATH.stat().st_size / 1024 / 1024, 2)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


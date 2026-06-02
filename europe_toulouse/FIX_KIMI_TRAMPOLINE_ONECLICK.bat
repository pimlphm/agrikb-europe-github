@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Patch-Fix-KimiTrampoline.ps1"
pause

@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0NewPC-Preflight.ps1" -RealModel
pause

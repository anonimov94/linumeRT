@echo off
rem SPDX-License-Identifier: GPL-2.0-or-later
rem Model-Author: Codex
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0console.ps1" %*
exit /b %errorlevel%

@echo off
rem SPDX-License-Identifier: GPL-2.0-or-later
rem Model-Author: Codex
setlocal
set WT_SESSION=
"%SystemRoot%\System32\conhost.exe" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0console.ps1" %*
set "hd_exit=%errorlevel%"
endlocal & exit /b %hd_exit%

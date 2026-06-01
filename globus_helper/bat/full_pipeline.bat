@echo off
setlocal
set PYTHONPATH=%~dp0..\..;%PYTHONPATH%

echo [1/2] Starting Globus Sync...
call %~dp0sync.bat --dest-path "/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/ne-dump/Actigraph"

if %ERRORLEVEL% NEQ 0 (
    echo Sync failed. Aborting transfer.
    exit /b %ERRORLEVEL%
)

echo [2/2] Starting BIDS Transfer...
call %~dp0transfer.bat --base-path "Z:\Projects\BOOST\InterventionStudy\3-experiment\data"

echo Pipeline complete.
endlocal

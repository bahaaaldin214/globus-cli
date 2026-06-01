@echo off
set PYTHONPATH=%~dp0..\..;%PYTHONPATH%
set GLOBUS_SOURCE_ENDPOINT=f183d8f3-a966-49cd-b175-817a0a88cc3c
set GLOBUS_DEST_ENDPOINT=39dd0982-d784-11e6-9cd4-22000a1e3b52
python -m globus_helper.main sync %*

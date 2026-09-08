@echo off
set PYTHONPATH=%~dp0..\..;%PYTHONPATH%
set GLOBUS_DRY_RUN=true
set GLOBUS_SOURCE_ENDPOINT=f183d8f3-a966-49cd-b175-817a0a88cc3c
set GLOBUS_DEST_ENDPOINT=39dd0982-d784-11e6-9cd4-22000a1e3b52
set GLOBUS_DEST_PATH=/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/bmohammad-dump/Actigraph
if not defined GLOBUS_SOURCE_PATH set GLOBUS_SOURCE_PATH=/Actigraphy Data/
python -m globus_helper.main sync --source-path "%GLOBUS_SOURCE_PATH%" %*

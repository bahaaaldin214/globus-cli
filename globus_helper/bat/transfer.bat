@echo off
set PYTHONPATH=%~dp0..\..;%PYTHONPATH%
set BASE_PATH=Z:\Projects\BOOST\InterventionStudy\3-experiment\data
python -m globus_helper.transfer.main %*

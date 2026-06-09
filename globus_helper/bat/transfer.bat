@echo off
set PYTHONPATH=%~dp0..\..;%PYTHONPATH%
set BASE_PATH=Z:\Projects\BOOST\InterventionStudy\3-experiment
set RAW_FOLDER=data/bmohammad-dump/Actigraph
set DEST_FOLDER=inputs/act-int-ready
python -m globus_helper.transfer.main %*

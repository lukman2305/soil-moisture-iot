#!/bin/bash
cd ~/soil-moisture-iot || exit

# Check if plant_data.csv has any new data
if [[ -n $(git status -s plant_data.csv) ]]; then
    git add plant_data.csv
    git commit -m "Auto-update dataset: $(date +'%Y-%m-%d %H:%M')"
    git push origin main
fi

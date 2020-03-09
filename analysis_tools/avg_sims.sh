if [[$# -ne 1]]; then
    echo 'Usage: ./analysis_tools/avg_sims ######'
    exit
fi

CODE=$1
python3 analysis_tools/outer_loop.py --avg
cp app/data/${CODE}00_parameters.yaml app/data/${CODE}AV_parameters.yaml
python3 visualize.py ${CODE}AV --standard --heatmap
python3 visulaize.py ${CODE}AV --a345 --standard --heatmap
mkdir app/data/.storage/$CODE
mkdir app/data/.storage/$CODE/meta
mkdir app/data/.storage/$CODE/raw
mkdir app/data/.storage/$CODE/processed
mv app/data/*AV* app/data/${CODE}##_combined.csv app/data/.storage/${CODE}/processed
mv app/data/*param* app/data/*accessed* app/data/.storage/${CODE}/meta
mv app/data/*code app/data/.storage/${CODE}/raw


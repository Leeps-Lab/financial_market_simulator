if [[ $# -ne 1 ]]; then
    echo "usage: ./analysis_tools/avg_sims.sh ######"
    exit 1
fi

CODE=$1
python3 analysis_tools/outer_loop_analysis.py --avg
cp app/data/${CODE}00_parameters.yaml app/data/${CODE}AV_parameters.yaml
python3 visualize.py ${CODE}AV --standard --heatmap
python3 visualize.py ${CODE}AV --a345 --standard --heatmap
mkdir app/data/.storage/$CODE
mkdir app/data/.storage/$CODE/meta
mkdir app/data/.storage/$CODE/raw
mkdir app/data/.storage/$CODE/processed
mv app/data/*AV* app/data/${CODE}##_combined.csv app/data/.storage/${CODE}/processed
mv app/data/*param* app/data/*accessed* app/data/.storage/${CODE}/meta
mv app/data/${CODE}* app/data/sim_meta.pickle app/data/.storage/${CODE}/raw


if [[ $# -ne 1 ]]; then
    echo "usage: ./analysis_tools/organize_sim_results.sh ######"
    exit 1
fi

CODE=$1
mkdir app/data/.storage/$CODE
mkdir app/data/.storage/$CODE/meta
mkdir app/data/.storage/$CODE/raw
mkdir app/data/.storage/$CODE/processed
mv app/data/*outer_loop* app/data/${CODE}##_combined.csv app/data/.storage/${CODE}/processed
mv app/data/*param* app/data/*accessed* app/data/.storage/${CODE}/meta
mv app/data/${CODE}* app/data/sim_meta.pickle app/data/.storage/${CODE}/raw


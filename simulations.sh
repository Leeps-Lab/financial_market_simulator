#!/bin/bash
DBUSER=simulation_user
DBPASS=somepassword
FMSDIR=/home/leeps/financial_market_simulator
#if [[$# -gt 0]] && [[$1 == '--alt']]; then
#    $FMSDIR=/home/kvargha/alt_financial_market_simulator
#fi

HOMEDIR=/home/leeps

sim_loop() {
    for i in {1..50}; do
        python3 dbreset.py
        if [[$i -lt 10]]; then
            python3 simulate.py --session_code 50avgs0$i
        else
            python3 simulate.py --session_code 50avgs$i
        fi
    done
}

print_fname() {
    cd $FMSDIR/app/data && ls *00_agent0.csv && cd $HOMEDIR
}

extract_code() {
    CODE=$(print_fname)
    echo ${CODE:0:6}
}

runsmall() {
    cd $FMSDIR \
    && python3 dbreset.py \
    && mpirun python3 simulate.py --session_code ${1}fn
}

run() {
    cd $FMSDIR \
    && python3 dbreset.py \
    && python3 outer_loop.py
}

main() {
    cp $FMSDIR/app/parameters.yaml $FMSDIR/app/parameters.yaml.copy

    # runs outer loop of simulations    
    run
    # extracts the session code generated by outer loop
    CODE=$(extract_code)

    # averages, visualizes, and moves data into storage directory
    # zooms in, keeping other agents the same and updating the grid search params
    cd $FMSDIR \
    && ./analysis_tools/avg_sims.sh $CODE \
    && python3 zoom_in.py $CODE --fine \
    && cd $HOMEDIR

    run
    CODE=$(extract_code)
    # zooms in, resetting the grid search params to coarse and updating other
    # agents' params
    cd $FMSDIR \
    && ./analysis_tools/avg_sims.sh $CODE \
    && python3 zoom_in.py $CODE --update-others \
    && cd $HOMEDIR
    
    run
    CODE=$(extract_code)
    cd $FMSDIR \
    && ./analysis_tools/avg_sims.sh $CODE \
    && python3 zoom_in.py $CODE --fine \
    && cd $HOMEDIR

    run
    CODE=$(extract_code)
    cd $FMSDIR \
    && ./analysis_tools/avg_sims.sh $CODE \
    && python3 zoom_in.py $CODE --final-update \
    && cd $HOMEDIR

    runsmall ${CODE}
    cd $FMSDIR \
    && python3 visualize.py ${CODE}fn --standard --heatmap \
    && python3 visualize.py ${CODE}fn --a345 --standard \
    && mv app/data/${CODE}*.png app/data/.storage/${CODE}/processed \
    && mv app/data/${CODE}*param* app/data/${CODE}*accessed* app/data/.storage/${CODE}/meta \
    && mv app/data/${CODE}* app/data/.storage/${CODE}/raw \
    && cd $HOMEDIR
    
    sleep 5

    mv $FMSDIR/app/parameters.yaml.copy $FMSDIR/app/parameters.yaml
}

main
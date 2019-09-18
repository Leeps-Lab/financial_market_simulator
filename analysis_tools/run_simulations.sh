#!/bin/bash
# documentation
# a_x is signed volume, a_y is inventory, and w is external market

PARAMS_FILE="app/parameters.yaml"

usage() {
    echo "Usage: ./analyis_tools/run_simulations.sh <step_size>"
    echo -e "\t<step_size>: An integer in [1..100]."
    echo -e "\tParameters get incremented by <step_size> / 100 each iteration."
    echo -e "\tIf 1, simulations will run with parameters [0.00,0.01...0.99,1.0]."
    echo -e "\tIf 50, simulations will run with parameters [0.0,0.5,1.0]."
    echo -e "\tIf 100, simulations will run with parameters [0.0,1.0]."
    exit 1
}

start_server() {
    echo "Starting server..."
    python3 run_web_api.py > /dev/null 2>&1 &
}

stop_server() {
    echo "Stopping server..."
    kill %1
}

backup_param_file() {
    echo "Backing up parameters.yaml..."
    cp $PARAMS_FILE $PARAMS_FILE.copy
}

restore_param_file() {
    echo "Restoring parameters.yaml from backup..."
    mv $PARAMS_FILE.copy $PARAMS_FILE
}

update_params() {
    sed -E "s/[0-9]*\,[ \t]*[0-9]*\,[ \t]*[0-1]\,[ \t]*[0-1](\.[0-9]*)?\,[ \t]*[0-1](\.[0-9]*)?\,[ \t]*[0-1](\.[0-9]*)?.*A1/0\, 1\, 0\, $1\, $2\, $3\] #A1/" $PARAMS_FILE > $PARAMS_FILE.2
    mv $PARAMS_FILE.2 $PARAMS_FILE
    sed -E "s/[0-9]*\,[ \t]*[0-9]*\,[ \t]*[0-1]\,[ \t]*[0-1](\.[0-9]*)?\,[ \t]*[0-1](\.[0-9]*)?\,[ \t]*[0-1](\.[0-9]*)?.*A2/0\, 2\, 0\, $1\, $2\, $3\] #A2/" $PARAMS_FILE > $PARAMS_FILE.2
    mv $PARAMS_FILE.2 $PARAMS_FILE
    sed -E "s/[0-9]*\,[ \t]*[0-9]*\,[ \t]*[0-1]\,[ \t]*[0-1](\.[0-9]*)?\,[ \t]*[0-1](\.[0-9]*)?\,[ \t]*[0-1](\.[0-9]*)?.*A3/0\, 3\, 0\, $1\, $2\, $3\] #A3/g" $PARAMS_FILE > $PARAMS_FILE.2
    mv $PARAMS_FILE.2 $PARAMS_FILE
}

prep_for_sim() {
    python3 dbreset.py > /dev/null 2>&1
    update_params $1 $2 $3
}

run_sim() {
    CODE=$(curl "http://localhost:5000/v1/simulate" 2> /dev/null)
    CODE=${CODE:43:8}
    sleep 14
    echo $CODE
}

analyze_output() {
    PROFIT="$(python3 analysis_tools/analyze_profits.py $1)"
    echo $PROFIT
}

print_progress() {
    N=$(( 25 * $1 / $2 ))
    P=$(( 25 * ($1 - 1) / $2))
    if [[ ($N -gt $P) || ($1 -eq 1) ]]; then
        echo -ne "["
        for (( c=1; c<=25; c++ )); do
            if [[ $c -le $N ]]; then
                echo -ne "#"
            else
                echo -ne " "
            fi
        done
        if [[ $1 -eq $2 ]]; then
            echo -ne "]\n"
        else
            echo -ne "]\r"
        fi
    fi
}

main() {
    MAX_PROFIT=$((-1 * 2**32))
    MAX_CODE='########'
    COUNT=0
    TOTAL=$(( (100 / $1 + 1)**3 ))
    start_server
    sleep 2
    backup_param_file
    echo "Running simulations..."
    echo -ne "[                         ]\r"
    for (( i=0; i<=100; i+=$1 )); do
        for (( j=0; j<=100; j+=$1 )); do
            for (( k=0; k<=100; k+=$1 )); do
                A_X=$(echo "scale=2; $i / 100.0" | bc)
                A_Y=$(echo "scale=2; $j / 100.0" | bc)
                W=$(echo "scale=2; $k / 100.0" | bc) 
                prep_for_sim $A_X $A_Y $W
                CODE="$(run_sim)"
                PROFIT="$(analyze_output $CODE)"
                if [[ $PROFIT -gt $MAX_PROFIT ]]; then
                    MAX_PROFIT=$PROFIT
                    MAX_CODE=$CODE
                fi
                COUNT=$(( COUNT + 1 ))
                print_progress $COUNT $TOTAL
            done
        done
    done
    stop_server
    restore_param_file
    echo "Done."
    echo "MAX PROFIT... $MAX_PROFIT"
    echo "CODE......... $MAX_CODE"
}

if [[ $# -ne 1 ]]; then
    usage
else
    re='^[0-9]+$'
    if ! [[ $1 =~ $re ]]; then
        usage
    fi
    main $1
fi







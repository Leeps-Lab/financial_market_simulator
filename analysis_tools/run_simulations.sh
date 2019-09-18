# documentation
# a_x is signed volume, a_y is inventory, and w is external market

PARAMS_FILE="app/parameters.yaml"

start_server() {
    python3 run_web_api.py &
}

stop_server() {
    kill %1
}

backup_param_file() {
    cp $PARAMS_FILE $PARAMS_FILE.copy
}

restore_param_file() {
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
    python3 dbreset.py
    update_params $1 $2 $3
}

run_sim() {
    curl "http://localhost:5000/v1/simulate"
    sleep 15
}

main() {
    start_server
    sleep 5
    backup_param_file
    for i in {1..100..10}; do
        for j in {1..100..10}; do
            for k in {1..100..10}; do
                A_X=$(echo "scale=2; $i / 100.0" | bc)
                A_Y=$(echo "scale=2; $j / 100.0" | bc)
                W=$(echo "scale=2; $k / 100.0" | bc) 
                prep_for_sim $A_X $A_Y $W
                run_sim
            done
        done
    done
    stop_server
    restore_param_file
}

main


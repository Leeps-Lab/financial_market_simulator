#!/bin/bash
#SBATCH --time=76:00:00
#SBATCH --job-name financial_market_simulation
#SBATCH -p 128x24
#SBATCH --mail-user=epandolf@ucsc.edu
#SBATCH --mail-type=ALL
#SBATCH -o logs/simulation-%j.log
#SBATCH -e logs/simulation-%j.log
#SBATCH -n 1
#SBATCH -N 1
#SBATCH -c 24
#SBATCH --mem=64G

module load python-3.6.2

DBUSER='simulation_user'
DBPASS='slugtree'
DBPORT='5433'
export DBPORT
HOMEDIR='/hb/home/epandolf/fba_fms'
FMSDIR="$HOMEDIR/financial_market_simulator"
PGDIR="$HOMEDIR/postgres-built"

print_fname() {
    cd $FMSDIR/app/data
    ls *00_agent0.csv
    cd $HOMEDIR
}

extract_code() {
    CODE=$(print_fname)
    echo ${CODE:0:6}
}

runsmall() {
    cd $FMSDIR
    python3 dbreset.py
    mpirun python3 simulate.py --session_code ${1}fn
    cd $HOMEDIR
}

run() {
    cd $FMSDIR
    python3 dbreset.py
    mpirun python3 outer_loop.py "$@"
    cd $HOMEDIR
}

organize_sims_results() {
    cd $FMSDIR
    ./analysis_tools/organize_sims_results.sh "$1"
    cd $HOMEDIR
}

outer_loop_analysis() {
    cd $FMSDIR
    python3 analysis_tools/outer_loop_analysis.py
    python3 analysis_tools/process_outerloop.py
    cd $HOMEDIR
}

outerloop_with_zoom_in() {
    run
    code=$(extract_code)
    organize_sims_results "$code"
    
    run --zoom_method "fine" --code "$code"
    code=$(extract_code)
    organize_sims_results "$code"
    
    run --zoom_method "update_others" --code "$code"
    code=$(extract_code)
    organize_sims_results "$code"
    
    run --zoom_method "fine" --code "$code"
    code=$(extract_code)
    organize_sims_results "$code"
    
    run --zoom_method "final_update" --code "$code"
    code=$(extract_code)
    outer_loop_analysis
    organize_sims_results "$code"
}

main() {
    # copy params file as backup
    cp $FMSDIR/app/parameters.yaml $FMSDIR/app/parameters.yaml.backup
    
    # start postgres and wait 5s to spin up
    $PGDIR/bin/pg_ctl -D $PGDIR/data/ -o "-p $DBPORT" start
    sleep 5

    # run some simulations
    outerloop_with_zoom_in

    # stop postgres and wait 5s to spin down
    $PGDIR/bin/pg_ctl -D $PGDIR/data/ -o "-p $DBPORT" stop
    sleep 5

    # restore param file from backup
    mv $FMSDIR/app/parameters.yaml.backup $FMSDIR/app/parameters.yaml
}

main


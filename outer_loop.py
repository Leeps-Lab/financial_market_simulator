import yaml
from time import sleep
from sys import executable, argv
import subprocess
import settings
from utility import (
    random_chars, get_interactive_agent_count, 
    get_simulation_parameters, copy_params_to_logs)
import atexit

def run_sim():
    cmd = [
        executable,
        'simulate.py',
    ]
    proc = subprocess.Popen(cmd)
    # make sure this process is eventually killed
    atexit.register(proc.terminate)
    return proc

def write_sim_params(sp):
    with open(settings.custom_config_path, 'w') as f:
        yaml.dump(sp, f);    

def update(sp, **kwargs):
    for k, v in kwargs.items():
        sp[k] = v
    return sp

def bigloop(sp):
    processes = []
    formats = ['CDA', 'FBA']
    lambdaj = [0.5, 2, 5]
    lambdai = [[0.1, 0.05], [0.2, 0.1], [0.5, 0.25]]
    speed = [1000, 10000]
    time_in_force = [0.5, 2]
    n = 1

    for f in formats:
        for j in lambdaj:
            for i in lambdai:
                for s in speed:
                    for t in time_in_force:
                        sp = update(sp,
                            focal_market_format=f,
                            lambdaJ=j,
                            lambdaI=i,
                            speed_unit_cost=s,
                            time_in_force=t
                        )
                        write_sim_params(sp)
                        print(f'Starting process {n}')
                        n += 1
                        processes.append(run_sim())
                        sleep(5)

    return processes

def smallloop(sp):
    processes = []
    formats = ['CDA', 'FBA']
    lambdaj = [0.5, 2]
    n = 1

    for f in formats:
        for j in lambdaj:
            sp = update(sp,
                focal_market_format=f,
                lambdaJ=j
            )
            write_sim_params(sp)
            print(f'Starting process {n}')
            n += 1
            processes.append(run_sim())
            sleep(10)
    return processes
    

def main():
    sp = get_simulation_parameters()
    method = 'small'
    if len(argv) > 1 and argv[1] == '--big':
        method = 'big'
    if method == 'big':
        processes = bigloop(sp)
    else:
        processes = smallloop(sp)
    
    n = 1
    for p in processes:
        p.wait()
        print(f'Finished process {n}')
        n += 1

if __name__ == '__main__':
    main()

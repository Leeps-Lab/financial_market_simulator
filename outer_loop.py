import pickle
import yaml
from time import sleep
from sys import executable, argv
import subprocess
import settings
from utility import (
    random_chars, get_interactive_agent_count, 
    get_simulation_parameters, copy_params_to_logs)
import atexit
import numpy as np
from itertools import product
from functools import reduce

def dump_pickle(d):
    with open(f'app/data/sim_meta.pickle', 'wb') as f:
        pickle.dump(d, f)

def run_sim(code=None):
    if code != None:
        cmd = [
            executable,
            'simulate.py',
            '--session_code',
            code,
        ]
    else:
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

def create_imap(args):
    imap = []
    for arg in args:
        imap.append(list(range(arg)))
    imap = product(*imap)
    return imap

def bigloop(sp):
    num_agents = 6
    processes = []
    formats = ['FBA']
    lambdaj = [.5]
    lambdai = [(0.1, 0.07), (0.5, 0.25)]
    speed = [500, 1000, 3000]
    time_in_force = [1]
    inventory_multiplier = [3]

    paramslist = [formats, lambdaj, lambdai, speed, time_in_force, inventory_multiplier]
    paramslens = [len(p) for o in paramslist]

    params = {
        'Format': formats,
        'Lambda J': lambdaj,
        'Lambda I': lambdai,
        'Speed Cost': speed,
        'Time in Force': time_in_force,
        'Inventory Multiplier': inventory_multiplier,
    }
    count = reduce(lambda x,y: x*y, paramslens)
    code = random_chars(6)
    imap = create_imap(paramslens)
    d = dict(code=code, params=params, imap=imap, count=count)
    dump_pickle(d)

    paramsproduct = product(*paramslist)
    for index, f, j, i, s, t, m in enumerate(paramsproduct):
        sp = update(sp,
            focal_market_format=f,
            lambdaJ=j,
            lambdaI=i,
            speed_unit_cost=s,
            time_in_force=t,
            a_y_multiplier=m
        )
        write_sim_params(sp)
        print(f'Starting process {n}')
        sn = str(index)
        if len(sn) == 1:
            sn = f'0{sn}'
        session_code = f'{code}{sn}'
        processes.append(run_sim(session_code))
        sleep(90)
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
    method = 'big'
    if len(argv) > 1 and argv[1] == '--small':
        method = 'small'
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

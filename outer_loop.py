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

def dump_pickle(d):
    with open('app/data/sim_meta.pickle', 'wb') as f:
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

def create_imap(ff, jj, ii, ss, tt, mm):
    imap = {}
    for f in range(ff):
        for j in range(jj):
            for i in range(ii):
                for s in range(ss):
                    for t in range(tt):
                        for m in range(mm):
                            key = f*jj*ii*ss*tt*mm + j*ii*ss*tt*mm + i*ss*tt*mm + s*tt*mm + t*mm + m
                            val = (f, j, i, s, t, m)
                            imap[key] = val
    return imap

def bigloop(sp):
    num_agents = 3
    processes = []
    formats = ['FBA']
    lambdaj = [2, 2, 2, 2, 2, 2]
    lambdai = [[0.1, 0.07]]#, [0.2, 0.1], [0.5, 0.25]]
    speed = [3000]
    time_in_force = [1, 1, 1, 1, 1]#, 2]
    inventory_multiplier = [3]

    ff = len(formats)
    jj = len(lambdaj)
    ii = len(lambdai)
    ss = len(speed)
    tt = len(time_in_force)
    mm = len(inventory_multiplier)
    params = {
        'Format': formats,
        'Lambda J': lambdaj,
        'Lambda I': lambdai,
        'Speed Cost': speed,
        'Time in Force': time_in_force,
        'Inventory Multiplier': inventory_multiplier,
    }
    count = ff * jj * ii * ss * tt * mm
    code = random_chars(6)
    imap = create_imap(ff, jj, ii, ss, tt, mm)
    d = dict(code=code, params=params, imap=imap, count=count)
    dump_pickle(d)

    n = 0
    for f in formats:
        for j in lambdaj:
            for i in lambdai:
                for s in speed:
                    for t in time_in_force:
                        for m in inventory_multiplier:
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
                            sn = str(n)
                            if len(sn) == 1:
                                sn = f'0{sn}'
                            session_code = f'{code}{sn}'
                            processes.append(run_sim(session_code))
                            n += 1
                            sleep(180)

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

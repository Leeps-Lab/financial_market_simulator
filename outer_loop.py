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
import argparse
from os.path import join
import zoom_in

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
    imap = list(product(*imap))
    return imap

def bigloop(sp, args=None):
    if args:
        if args.code:
            datadir = join('app', 'data', '.storage', args.code, 'raw')
        
    num_agents = 6
    processes = []
    formats = ['CDA']
    lambdaj = [.5]#, 2]
    lambdai = [[0.1, 0.07]]#, [0.5, 0.25]]
    speed = [500, 1000]#, 3000]
    #time_in_force = [1]
    #inventory_multiplier = [3]
    agent_state_configs = [[
        [0, 1, 0, 0, 0, 0],
        [0, 2, 0, 0, 0.25, 0.25],
        [0, 3, 0, 0, 0.25, 0.25],
        [0, 4, 0, 0, 0.25, 0.25],
        [0, 5, 0, 0, 0.25, 0.75],
        [0, 6, 0, 0, 0.25, 0.75],
    ]]

    paramslist = [formats, lambdaj, lambdai, speed] #time_in_force, inventory_multiplier]
    paramslens = [len(p) for p in paramslist]

    params = {
        'Format': formats,
        'Lambda J': lambdaj,
        'Lambda I': lambdai,
        'Speed Cost': speed,
        #'Time in Force': time_in_force,
        #'Inventory Multiplier': inventory_multiplier,
    }
    count = reduce(lambda x,y: x*y, paramslens)
    code = random_chars(6)
    imap = create_imap(paramslens)
    d = dict(code=code, params=params, imap=imap, count=count)
    dump_pickle(d)

    paramsproduct = product(*paramslist)
    for index, (f, j, i, s) in enumerate(paramsproduct): 
        
        sn = str(index)
        if len(sn) == 1:
            sn = f'0{sn}'
        retdict = {'agent_state_configs': agent_state_configs}
        if args and args.code and args.zoom_method:
            fname = f'{args.code}{sn}_agent0.csv'
            fname = join(datadir, fname)
            inv, ext, speed = zoom_in.parse_csv(fname)
            if args.zoom_method == 'fine':
                retdict = zoom_in.do_fine(inv, ext)
            elif args.zoom_method == 'update_others':
                retdict = zoom_in.do_others(inv, ext, speed)
            elif args.zoom_method == 'final_update':
                retdict = zoom_in.do_final(inv, ext, speed)
        
        sp = update(sp,
            focal_market_format=f,
            lambdaJ=j,
            lambdaI=i,
            speed_unit_cost=s,
            #time_in_force=t,
            #a_y_multiplier=m,
            **retdict
        )
        write_sim_params(sp)
        print(f'Starting process {index}')
        session_code = f'{code}{sn}'
        processes.append(run_sim(session_code))
        if not args or args.zoom_method != 'final_update':
            sleep(sp['session_duration'] / 2 + 50)
        elif args and args.zoom_method == 'final_update':
            sleep(150)
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
            sleep(20)
    return processes
    

def main():
    sp = get_simulation_parameters()
    parser = argparse.ArgumentParser(description='Outer Loop')
    parser.add_argument('--method', type=str, action='store', default='big')
    parser.add_argument('--zoom_method', action='store', type=str)
    parser.add_argument('--code', action='store', type=str)
    args = parser.parse_args()

    if args.method == 'big':
        processes = bigloop(sp, args=args)
    else:
        processes = smallloop(sp, args=args)
    
    n = 1
    for p in processes:
        p.wait()
        print(f'Finished process {n}')
        n += 1

if __name__ == '__main__':
    main()

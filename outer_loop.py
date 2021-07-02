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

def get_current_strats(current_inv, current_ext, current_speed):
    sp = get_simulation_parameters()
    agents = sp['agent_state_configs'] # get current agent states
    agents = [(a[2], a[4], a[5]) for a in agents] # convert to tuples with speed, inv, ext
    #agents = set(agents) # turn into set
    current_params = (current_speed, current_inv, current_ext)
    if current_params in agents: # this should always be true
        agents.remove(current_params)
    if agents[0][1] > agents[1][1]: # sniper is whichever has higher external
        sniper = agents[0]
        mm = agents[1]
    else:
        sniper = agents[1]
        mm = agents[0]
    return (sniper[1], sniper[2], mm[1], mm[2])

def determine_strat(ext, speed, current_strat):
    current_sniper_ext = current_strat[0]
    current_sniper_speed = current_strat[1]
    current_mm_ext = current_strat[2]
    current_mm_speed = current_strat[3]

    # assume sniper ext is biggern than mm ext
    mean_ext = (current_sniper_ext + current_mm_ext) / 2
    if ext > mean_ext and speed == 1:
        strat = 'sniper'
    elif ext < mean_ext and speed == 0:
        strat = 'market maker'
    elif ext < mean_ext and speed == 1:
        if ext < 0.5:
            strat = 'market maker'
        else:
            strat = 'sniper'
    elif ext > mean_ext and speed == 0:
        if ext < 0.5:
            strat = 'market maker'
        else:
            strat = 'sniper'
    return strat

def bigloop(sp, args=None):
    if args:
        if args.code:
            datadir = join('app', 'data', '.storage', args.code, 'raw')
        
    processes = []
    formats = ['CDA']
    lambdaj = [.5]#, 2]
    lambdai = [[0.1, 0.07]]#, [0.5, 0.25]]
    speed = [500]#, 1000]#, 3000]

    #  arrival_time, agent_num, speed, a_x, a_y, a_z
    agent_state_configs = [
        [0, 1, 0, 0, 0, 0],
        [0, 2, 0, 0, 0.25, 0.25],
        [0, 3, 0, 0, 0.25, 0.25],
        [0, 4, 0, 0, 0.25, 0.25],
        [0, 5, 0, 0, 0.25, 0.75],
        [0, 6, 0, 0, 0.25, 0.75],
    ]

    paramslist = [formats, lambdaj, lambdai, speed]
    paramslens = [len(p) for p in paramslist]

    params = {
        'Format': formats,
        'Lambda J': lambdaj,
        'Lambda I': lambdai,
        'Speed Cost': speed,
    }
    count = reduce(lambda x,y: x*y, paramslens)
    code = random_chars(6)
    imap = create_imap(paramslens)
    d = dict(code=code, params=params, imap=imap, count=count)
    dump_pickle(d)

    paramsproduct = product(*paramslist)
    num = 0
    for index, (f, j, i, s) in enumerate(paramsproduct): 
        sn = str(num)
        if len(sn) == 1:
            sn = f'0{sn}'
        
        retdict = {}

        if args and args.code and args.zoom_method:
            fname = f'{args.code}{sn}_agent0.csv'
            fname = join(datadir, fname)
            inv, ext, speed = zoom_in.parse_csv(fname)                
            
            if args.zoom_method == 'fine':
                retdict = zoom_in.do_fine(inv, ext)
            elif args.zoom_method == 'update_others':
                retdict = zoom_in.do_others(inv, ext, speed, agent_state_configs)
            elif args.zoom_method == 'final_update':
                retdict = zoom_in.do_final(inv, ext, speed, agent_state_configs)
            elif args.zoom_method == 'update_other_strats':
                current_strats = get_current_strats(inv, ext, speed, agent_state_configs)
                print(current_strats)
                my_strat = determine_strat(ext, speed, current_strats, agent_state_configs)
                print(my_strat)
                if my_strat == 'sniper':
                    retdict = zoom_in.add_sniper_and_update(current_strats, ext, speed)
                elif my_strat == 'market maker':
                    retdict = zoom_in.add_mm_and_update(current_strats, ext, speed)
                print(retdict)

        print('-----------------------------------')
        print(args.zoom_method)
        print('-----------------------------------')

        # Calculate the time a simulation is run
        num_moves = sp['num_moves']
        move_interval = sp['move_interval']
        num_repeats = sp['num_repeats']

        if args.zoom_method != 'final_update':
            retdict['session_duration'] = int(num_moves * move_interval * num_repeats)
        else:
            retdict['session_duration'] = int(move_interval * num_repeats + 10)
        '''
        # If update others has been run previously, ensure that the init vals are correct
        if sp['init_y'] != False and (args.zoom_method != 'update_others' and args.zoom_method != 'final_update'):
            fname = f'{args.code}{sn}_agent1.csv'
            fname = join(datadir, fname)
            inv, ext, speed = zoom_in.parse_csv(fname)
            sp['init_y'] = inv
            sp['init_z'] = ext
            sp['init_speed'] = speed
        '''   
        sp = update(sp,
            focal_market_format=f,
            lambdaJ=j,
            lambdaI=i,
            speed_unit_cost=s,
            **retdict
        )

        

        print(sp)

        write_sim_params(sp)
        print(f'Starting process {index}')
        session_code = f'{code}{sn}'
        processes.append(run_sim(session_code))
        if not args or args.zoom_method != 'final_update':
            sleep(sp['session_duration'] / 2 + 50)
        elif args and args.zoom_method == 'final_update':
            sleep(150)
        num += 1
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

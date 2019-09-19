import sys
import pandas as pd
import shutil
import subprocess
import atexit
import configargparse
import logging
from time import sleep
import yaml
import analyze_profits 
import numpy as np
import pickle as pkl
from datetime import datetime as dt

log = logging.getLogger(__name__)

def initialize_logger(debug):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(asctime)s.%(msecs)03d %(levelname)s]  %(message)s",
        datefmt='%H:%M:%S') 

def start_server():
    log.info('Starting server') 
    cmd = [
        sys.executable,
        'run_web_api.py'
    ]
    proc = subprocess.Popen(cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    # make sure this process is eventually killed
    atexit.register(proc.terminate)

def backup_param_file(path):
    log.info('Backing up param file')
    shutil.copy(path, f'{path}.copy')

def restore_param_file_from_backup(path):
    log.info('Restoring param file from backup')
    shutil.move(f'{path}.copy', path)

def read_param_file(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def write_param_file(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f)

def update_params(path, **kwargs):
    params = read_param_file(path)
    for k, v in kwargs.items():
        params[k] = v
    write_param_file(path, params)

def prep_for_sim(path, **kwargs):
    cmd = [
        sys.executable,
        'dbreset.py',
    ]
    proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
    update_params(path, **kwargs)
    proc.wait()

def run_sim(endpoint, session_duration):
    cmd = [
        'curl', endpoint,
    ]
    metadata = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    metadata = metadata.decode('utf-8')
    search = 'code --> '
    i = metadata.index(search) + len(search)
    session_code = metadata[i: i + 8] # session code is always 8 digits
    sleep(session_duration + 4) # 4 seconds of server-side overhead per simulation
    return session_code

def analyze_output(session_code, trader_code=None):
    df = analyze_profits.read_csv(session_code)
    profits, traders = analyze_profits.extract_profits(df)
    return sum(profits)
    # trader code used to get profit for single trader

def print_progress(count, total, curr):
    percent = 100.0 * count / total
    if percent > curr + 10:
        curr = percent
        percent = int(percent)
        print(f'{percent}%', end='', flush=True)
        if percent != 100.0:
            print('..', end='', flush=True)
        else:
            print('', flush=True)
    return curr

# ignoring speed for now since agents are symmetric
def explore_static(x, y, w, path, endpoint, **kwargs):
    x_range = int((x['high'] - x['low']) / x['step'] + 1)
    y_range = int((y['high'] - y['low']) / y['step'] + 1)
    w_range = int((w['high'] - w['low']) / w['step'] + 1)
    surface = np.zeros((x_range, y_range, w_range))
    # total, count, and curr used for logging
    total = x_range * y_range * w_range
    count = 0
    curr = 0
    speed = 0
    print('0%..', end='', flush=True)
    for i, A_X_ in enumerate(range(x['low'], x['high'] + 1, x['step'])):
        for j, A_Y_ in enumerate(range(y['low'], y['high'] + 1, y['step'])):
            for k, W_ in enumerate(range(w['low'], w['high'] + 1, w['step'])):
                A_X = A_X_ / 100.0
                A_Y = A_Y_ / 100.0
                W = W_ / 100.0
                agent_state_configs = [
                    #arrive time, index, speed, signed vol, inventory, external
                    [0,           1,     speed, A_X,        A_Y,       W],
                    [0,           2,     speed, A_X,        A_Y,       W],
                    [0,           3,     speed, A_X,        A_Y,       W],
                ]
                prep_for_sim(
                    path,
                    agent_state_configs=agent_state_configs,
                    **kwargs
                )
                session_code = run_sim(endpoint, kwargs['session_duration'])
                profit = analyze_output(session_code)
                surface[i][j][k] = profit
                count += 1
                curr = print_progress(count, total, curr)
    return surface

def generate_surface(res, path, endpoint, save=False, **kwargs):
    low = 0
    high = 100
    res = float(res)
    step = int(res * high)
    log.info(f'Generating global surface with resolution {res}')
    x = {'low': low, 'high': high, 'step': step}
    y = {'low': low, 'high': high, 'step': step}
    w = {'low': low, 'high': high, 'step': step}
    
    surface = explore_static(x, y, w, path, endpoint, **kwargs)
    log.info('Done generating surface...')
    if save:
        t = dt.now().strftime('%Y-%m-%d_%H:%M:%S')
        with open(f'global_surface_{res}_{t}.pkl', 'wb') as f:
            pkl.dump(surface, f)
    return surface

# for now we default to generating surface and have no args
def main():
    p = configargparse.getArgParser()
    p.add('-d', '--debug', action='store_true')
    p.add('--save_surface', action='store_true')
    options, args = p.parse_known_args()
    initialize_logger(options.debug)
    param_filepath = 'app/parameters.yaml'
    endpoint = 'http://localhost:5000/v1/simulate'
    
    params = {
        'session_duration': 5,
        'read_fundamental_values_from_array': False,
        'fundamental_value_noise_std': 10000,
        'focal_market_format': 'CDA',
    }
    log.debug(params)

    backup_param_file(param_filepath)
    try:
        start_server()
        sleep(2) # time for the server to spin up

        surface = generate_surface(
            1.01,
            param_filepath,
            endpoint,
            save=options.save_surface,
            **params
        )
        print(surface)
        
        # explore_dynamic()
        restore_param_file_from_backup(param_filepath)
    except:
        restore_param_file_from_backup(param_filepath)
        e = sys.exc_info()[0]
        raise e

if __name__ == '__main__':
    main()


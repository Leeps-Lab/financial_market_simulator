import shutil
import subprocess
import atexit
import configargparse
import logging
from time import sleep
import yaml
import analyze_profits 
import numpy as np

def start_server():
    cmd = [
        sys.executable,
        'run_web_api.py',
        '>', '/dev/null',
        '2>&1',
    ]
    proc = subprocess.Popen(cmd)
    # make sure this process is eventually killed
    atexit.register(proc.terminate)

def backup_param_file(path):
    shutil.copy(path, f'{path}.copy')

def restore_param_file_from_backup(path):
    shutil.move(f'{path}.copy', path)

def read_param_file(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def write_param_file(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f)

def update_params(path, **kwargs):
    params = read_param_file(path)
    for k, v in kwargs.iteritems():
        params[k] = v
    write_param_file(path, params)

def prep_for_sim(path, **kwargs):
    cmd = [
        sys.executable,
        'dbreset.py',
        '>', '/dev/null',
        '2>&1',
    ]
    proc = subprocess.Popen(cmd)
    update_params(path, **kwargs)
    proc.wait()

def run_sim(endpoint, session_duration):
    cmd = [
        'curl', endpoint,
        '2>', '/dev/null',
    ]
    metadata = subprocess.check_output(cmd)
    search = 'session code --> '
    i = metadata.index(s) + len(s)
    session_code = metadata[i: i + 8]
    sleep(session_duration + 2) #NOTE: this may need to be +3, or +4
    return session_code

def analyze_output(session_code, trader_code=None):
    df = analyze_profits.read_csv(session_code)
    profits, traders = analyze_profits.extract_profits(df)
    return sum(profits)
    # trader code used to get profit for single trader

def print_progress():
    pass

# ignoring speed for now since agents are symmetric
def explore_local_maxima(x, y, w, path, endpoint, **kwargs):
    x_range = (x['high'] - x['low']) / x['step']
    y_range = (y['high'] - y['low']) / y['step']
    w_range = (w['high'] - w['low']) / w['step']
    surface = np.zeroes([x_range, y_range, w_range])
    speed = 0
    for i, A_X in enumerate(range(x['low'], x['high'], x['step'])):
        for j, A_Y in enumerate(range(y['low'], y['high'], y['step'])):
            for k, W in enumerate(range(w['low'], w['high'], w['step'])):
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
    return surface

def generate_surface(path, endpoint, **kwargs):
    low = 0.0
    high = 1.0
    step = 0.1
    x = {'low': low, 'high': high, 'step': step}
    y = {'low': low, 'high': high, 'step': step}
    w = {'low': low, 'high': high, 'step': step}
    
    surface = explore_local_maxima(x, y, w, path, endpoint, **kwargs)
    # intermediate processing?
    return surface

# for now we default to generating surface and have no args
def main():
    params_filepath = 'app/parameters.yaml'
    endpoint = 'http://localhost:5000/v1/simulate'
    
    params = {
        'session_duration': 5,
        'read_fundamental_values_from_array': False,
        'fundamental_value_noise_std': 10000,
        'focal_market_format': 'CDA',
    }

    start_server()
    backup_params_file(params_filepath)
    sleep(2) # time for the server to spin up

    #generate_surface(
    #   params_filepath,
    #    endpoint,
    #    **params
    #)
    
    # explore_local_maxima()

    restore_param_file_from_backup(params_filepath)

if __name__ == '__main__':
    main()





















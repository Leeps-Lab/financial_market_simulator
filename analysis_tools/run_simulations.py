import sys
from os import listdir, remove
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

'''
Description:
    Multi-functional client for the simulator. In a nutshell, it runs
    multiple simulations, changing parameters every time, with the goal
    of finding parameters that maximize profits.

Caveats:
    This is a work in progress and many features are not yet implemented.
    Things that are right now but will change later:
    - all agents change the same parameters at the same time. This will change
    so that each agent can be independent from others.
    - the metric analyzed is the sum of all agents' profits. This will change
    so that we only look at 1 agent's profits.
        
Usage:
    `python3 run_simulations.py -h` to see help options.

Examples:
    `python3 run_simulations.py --generate_global 0.1 --save_global --clean --analyze_global`
    `python3 run_simulations.py -r global_surface_1.0_2019-09-19_17:58:18.pkl -a`

    The first one generates a global surface with a resolution of 0.1. This means
    it tries all combinations of all values in [0.0, 0.1, 0.2 ... 1.0] for 
    parameters a_x, a_y, w, running a total of 11^3 simulations. After each
    simulation, the sum profits of all automated agents are stored, and the
    market csv, agent csv, and session param yaml are deleted (the --clean option).
    The profits are stored for each simulation and saved at the end in a file
    that is called 'global_surface_{date_time}.pkl'. Then, the program analyzes
    that output to find the highest 20% of data points, and prints out a list
    with elements of the form (A_X, A_Y, W, $$$).

    The second one reads in an example pickle file that doesnt actually exist,
    and analyzes it like before.

Next steps:
    Now that we can generate a global surface and find some local maxima on it,
    we are going to:
        for each maxima, generate a smaller surface about that maxima with higher
        resolution. This could be done statically/brute force, meaning try every
        combination of parameters in (for example) [0.10, 0.11 ... 0.19] for
        A_X, [0.65, 0.66... 0.74] for A_Y, etc. Note that the functionality
        already exists to make the different sliders have different value
        ranges. This could also be done dynamically, where we try random
        parameter updates, and follow ones that are beneficial and ignore ones
        that are detrimental. This could be done in a q-learning environment,
        or in some simpler implementation.

    We are also going to enable the functionality in CAVEATS above.

Estimated times:
    generate global surface:
        ~9 seconds per simulation * (1.0 / resolution + 1)^3 different simulations.
        resolution = 1.0:  75 seconds
        resolution = 0.2:  33 minutes
        resolution = 0.1:  3.4 hours
        resolution = 0.05: 23.1 hours
        resolution = 0.01: 107 days
    analyzing maxima:
        O(nlogn), where n is the number of simulations.
        Should be no more than a couple of seconds even for resolutions
        on the order of 0.05.
'''

log = logging.getLogger(__name__)

# initializes logger settings
def initialize_logger(debug):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(asctime)s.%(msecs)02d %(levelname)s]\t%(message)s",
        datefmt='%H:%M:%S') 

# starts the simulator http server
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

# backs up param file so no lasting changes from running this script
def backup_param_file(path):
    log.info('Backing up param file')
    shutil.copy(path, f'{path}.copy')

# restores param file automatically so no lasting changes from running this script
def restore_param_file_from_backup(path):
    log.info('Restoring param file from backup')
    shutil.move(f'{path}.copy', path)

# reads parameters.yaml into dict
def read_param_file(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

# writes dict to parameters.yaml
def write_param_file(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f)

# updates parameters.yaml with data for current simulation
def update_params(path, **kwargs):
    params = read_param_file(path)
    for k, v in kwargs.items():
        params[k] = v
    write_param_file(path, params)

# resets database, and updates parameters directly before current sim runs
def prep_for_sim(path, **kwargs):
    cmd = [
        sys.executable,
        'dbreset.py',
    ]
    proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
    update_params(path, **kwargs)
    proc.wait()

# hits the simulate endpoint on the server and stores the session code
def run_sim(endpoint, session_duration):
    cmd = [
        'curl', endpoint,
    ]
    metadata = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    metadata = metadata.decode('utf-8')
    search = 'code --> '
    i = metadata.index(search) + len(search)
    session_code = metadata[i: i + 8] # session code is always 8 digits
    sleep(session_duration + 4) # 4 seconds of server-side overhead per simulation,
                                 # more if your cpu is being used heavily
    return session_code

# extracts the profits from the current simulation agent csv
def analyze_output(session_code, trader_code=None):
    df = analyze_profits.read_csv(session_code)
    profits, traders = analyze_profits.extract_profits(df)
    return sum(profits)
    # trader code used to get profit for single trader

# prints progress so user knows roughly what proportion of simulations
# have been finished so far
def print_progress(count, total, curr):
    percent = 100.0 * count / total
    if percent > curr + 10:
        curr = percent
        percent = int(percent)
        log.info(f'{percent}%')
    return curr

# uses session code to delete market, agent, and param files for current sim
def find_and_delete_files(code):
    fpaths = []
    prefix = f'{code}'
    dirpath = 'app/data/'
    for f in listdir(dirpath):
        if f.startswith(prefix):
            fpaths.append(f'{dirpath}{f}')
    if len(fpaths) != 3:
        log.warning(f'Files with session code {code} not found')
    else:
        for f in fpaths:
            remove(f)

# tries all combinations of parameters for a_x, a_y, w (each separately
# configurable), and returns a 3D numpy array.
# ignores speed for now
def explore_static(x, y, w, path, endpoint, clean=False, **kwargs):
    x_range = int((x['high'] - x['low']) / x['step'] + 1)
    y_range = int((y['high'] - y['low']) / y['step'] + 1)
    w_range = int((w['high'] - w['low']) / w['step'] + 1)
    surface = np.zeros((x_range, y_range, w_range))
    # total, count, and curr used for logging
    total = x_range * y_range * w_range
    count = 0
    curr = 0
    speed = 0
    log.info('0%')
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
                if clean:
                    find_and_delete_files(session_code)
    return surface

# generates a 3D numpy array w some metadata for the global parameter space
# (0.0, 1.0], with specified resolution. More explanation in Examples.
def generate_global_surface(res, path, endpoint, save=False, clean=False,
    **kwargs):
    low = 0
    high = 100
    res = float(res)
    step = int(res * high)
    log.info(f'Generating global surface with resolution {res}')
    x = {'low': low, 'high': high, 'step': step}
    y = {'low': low, 'high': high, 'step': step}
    w = {'low': low, 'high': high, 'step': step}
    
    surface = explore_static(x, y, w, path, endpoint, clean, **kwargs)
    struct = {
        'low': low,
        'high': high,
        'res': res,
        'step': step,
        'surface': surface,
    }
    if save:
        log.info('Dumping surface to pkl file')
        t = dt.now().strftime('%Y-%m-%d_%H:%M:%S')
        with open(f'global_surface_{res}_{t}.pkl', 'wb') as f:
            pkl.dump(struct, f)
    return struct

# reads a pickled surface array + metadata from a file
def read_global_surface(path):
    log.info('Loading surface from pkl file')
    with open(path, 'rb') as f:
        struct = pkl.load(f)
    return struct

# finds local maxima w/ parameters for a global surface
# for now we say highest 20% of data points are local maxima.
def analyze_global_surface(surface, high, low, step, res):
    size = int(((high - low) / step + 1))**3
    maxima = []
    num_maxima = round(0.2 * size + 1)
    
    for i, x in enumerate(range(low, high + 1, step)):
        for j, y in enumerate(range(low, high + 1, step)):
            for k, w in enumerate(range(low, high + 1, step)):
                maxima.append((x, y, w, surface[i][j][k]))
    maxima = sorted(maxima, key=lambda x: -x[3])
    maxima = maxima[0: num_maxima]
    return maxima

# parses args, logs a couple things, does some error checking,
# then runs simulations or analyzes surface based on input arguments.
def main():
    exit_status = 0
    p = configargparse.getArgParser()
    p.add('-d', '--debug', action='store_true',
        help='Prints more verbose debug messages')
    p.add('-s', '--save_global', action='store_true',
        help='Pickles the generated global surface')
    p.add('-c', '--clean', action='store_true',
        help='Removes output files each session to avoid buildup')
    p.add('-g', '--generate_global',
        help='Generates a global surface with specified resolution in (0.0, 1.01]')
    p.add('-r', '--read_global',
        help='Loads a pkl file that contains a global surface')
    p.add('-a', '--analyze_global', action='store_true',
        help='Analyze global surface for local maxima')
    options, args = p.parse_known_args()
    initialize_logger(options.debug)
    log.debug('Debug mode on')
    
    param_filepath = 'app/parameters.yaml'
    endpoint = 'http://localhost:5000/v1/simulate'
    params = {
        'session_duration': 5,
        'read_fundamental_values_from_array': False,
        'fundamental_value_noise_std': 10000,
        'focal_market_format': 'CDA',
    }
    log.debug(params)

    if options.read_global and options.generate_global:
        log.error('--read_global and --generate_global flags are mutually exclusive')
        exit(1)
    if options.save_global and not options.generate_global:
        log.error('--save_global option requires --generate_global option')
        exit(1)
    if options.analyze_global and not (options.generate_global or options.read_global):
        log.error('--analyze_global option requires either generate_global option or read_global option')

    backup_param_file(param_filepath)
    try:
        start_server()
        sleep(2) # time for the server to spin up
        
        surface = None
        if options.generate_global:
            if not 0.0 < float(options.generate_global) <= 1.01:
                log.error('--generate_global arg must be real number in range (0.0, 1.01]')
                exit(1)
            surface = generate_global_surface(
                float(options.generate_global),
                param_filepath,
                endpoint,
                save=options.save_global,
                clean=options.clean,
                **params
            )
        if options.read_global:
            surface = read_global_surface(options.read_global)
        if options.analyze_global:
            maxima = analyze_global_surface(**surface)
            print(maxima)
        '''
        for each local maxima, explore_dynamic / explore_static with higher (lower) resolution
        '''
        
        restore_param_file_from_backup(param_filepath)
    except Exception as e:
        restore_param_file_from_backup(param_filepath)
        exit_status = 1
        log.error(e)
    finally:
        log.info('Exiting')
        exit(exit_status)

if __name__ == '__main__':
    main()


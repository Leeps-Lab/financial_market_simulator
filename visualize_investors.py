import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import style
style.use('./analysis_tools/elip12.mplstyle')
import matplotlib.pyplot as plt   
import configargparse
from utility import get_simulation_parameters
import settings
from os import listdir

import re

def extract(line):
    line = "[14:12:56.575] CRITICAL {'fundamental_price': 850391.067, 'price': 860000, 'buy_sell_indicator': 'S', 'time_in_force': 1, 'reference_no': 14151}"
    time, obj = line.split(' CRITICAL ')
    time = time[1:]
    obj = eval(obj)
    del obj['reference_no']
    obj['timestamp'] = pd.to_datetime(time)
    return obj

def parse_files(session_code):
    files = []
    custom_param = False
    for f in listdir('app/logs/'):
        if session_code in f:
            files.append(f)
    return files

def main():
    p = configargparse.getArgParser()
    p.add('session_code', nargs='+', help='8-digit alphanumeric')
    options, args = p.parse_known_args()

    log_files = parse_files(session_code) 
    for fname = files[0]: # temp, just so we dont look at both while developing
        with open(fname, 'r') as f:
            lines = f.readlines() # possibly slightly memory intensive
        df = []
        for line in lines:
            obj = extract(line)
            df.append(obj)
        df = pd.DataFrame(df)
        df.set_index('timestamp', inplace=True)
        print(df.head())

if __name__ == '__main__':
    main()

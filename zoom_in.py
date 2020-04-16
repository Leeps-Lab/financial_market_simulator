import pandas as pd                                                                  
from sys import argv                                                                 
from utility import get_simulation_parameters                                        
import yaml
import settings

def parse_csv(fname):
    df = pd.read_csv(fname)
    df = df[df['Profit'] == df['Profit'].max()]
    if len(df) == 0:
        return 0, 0, 0
    inv = round(float(df['Inventory'].values[0]), 2)
    ext = round(float(df['External'].values[0]), 2)
    speed = round(float(df['Speed'].values[0]), 2)
    return inv, ext, speed

def do_fine(inv, ext):
    if inv == 0:
        invlist = [0.0, 0.06, 0.12, 0.18, 0.24]
    elif inv == 1:
        invlist = [0.76, 0.82, 0.88, 0.94, 1.0]
    else:
        invlist = [inv - 0.24, inv - 0.12, inv, inv + 0.12, inv + 0.24]
    if ext == 0:
        extlist = [0.0, 0.06, 0.12, 0.18, 0.24]
    elif ext == 1:
        extlist = [0.76, 0.82, 0.88, 0.94, 1.0]
    else:
        extlist = [ext - 0.24, ext - 0.12, ext, ext + 0.12, ext + 0.24]
    retdict = {
        'ys': invlist,
        'zs': extlist,
    }
    return retdict

def do_others(inv, ext, speed):
    invlist = [0, 0.25, 0.5, 0.75, 1]
    extlist = [0, 0.25, 0.5, 0.75, 1]
    retdict = {
        'init_y': inv,
        'init_z': ext,
        'init_speed': speed,
        'ys': invlist,
        'zs': extlist,
    }
    return retdict

def do_final(inv, ext, speed):
    sp = get_simulation_parameters()
    invlist = [inv]
    extlist = [ext]
    speedlist = [speed]
    num_repeats = 50
    session_duration = sp['move_interval'] * 51 + 1
    retdict = {
        'init_y': inv,
        'init_z': ext,
        'init_speed': speed,
        'ys': invlist,
        'zs': extlist,
        'speeds': speedlist,
        'num_repeats': num_repeats,
        'session_duration': session_duration,
    }
    return retdict


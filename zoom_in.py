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
    num_repeats = 20
    session_duration = int(sp['move_interval'] * (num_repeats) + 10)
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

def add_sniper(sniper_ext, mm_ext, sniper_speed=1, mm_speed=0):
    sp = get_simulation_parameters()
    agents = sp['agent_state_configs']
    for i in range(len(agents)):
        if agents[i][5] == mm_ext:
            agents[i][5] = sniper_ext
            agents[i][2] = sniper_speed
            break
    retdict = dict(agent_state_configs=agents)
    return retdict

def add_mm(sniper_ext, mm_ext, sniper_speed=1, mm_speed=0):
    sp = get_simulation_parameters()
    agents = sp['agent_state_configs']
    for i in range(len(agents)):
        if agents[i][5] == sniper_ext:
            agents[i][5] = mm_ext
            agents[i][2] = mm_speed
            break
    retdict = dict(agent_state_configs=agents)
    return retdict

def update_strat(old_ext, old_speed, new_ext, new_speed, agents=None):
    if agents == None:
        sp = get_simulation_parameters()
        agents = sp['agent_state_configs']
    for i in range(len(agents)):
        if agents[i][5] == old_ext and agents[i][2] == old_speed:
            agents[i][5] = new_ext
            agents[i][2] = new_speed
    retdict = dict(agent_state_configs=agents)
    return retdict

def add_sniper_and_update(current_strats, ext, speed):
    retdict = add_sniper(*current_strats)
    agents = retdict['agent_state_configs']
    retdict = update_strat(current_strats[0], current_strats[1], ext, speed, agents)
    return retdict

def add_mm_and_update(current_strats, ext, speed):
    retdict = add_sniper(*current_strats)
    agents = retdict['agent_state_configs']
    retdict = update_strat(current_strats[2], current_strats[3], ext, speed, agents)
    return retdict

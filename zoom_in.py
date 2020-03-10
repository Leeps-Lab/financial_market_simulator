import pandas as pd                                                                  
from sys import argv                                                                 
from utility import get_simulation_parameters                                        
import yaml
import settings

def write_sim_params(sp):
    with open(settings.custom_config_path, 'w') as f:
        yaml.dump(sp, f);    

def update(sp, **kwargs):
    for k, v in kwargs.items():
        sp[k] = v
    return sp

def update_fine(inv, ext):
    sp = get_simulation_parameters()
    update(sp, ys=inv, zs=ext)
    write_sim_params(sp)

def update_others(initinv, initext, speed, invlist, extlist):
    sp = get_simulation_parameters()
    update(sp, init_y=initinv, init_z=initext, init_speed=speed, ys=invlist, zs=extlist)
    write_sim_params(sp)

def update_final(inv, ext, speed):
    sp = get_simulation_parameters()
    update(sp, init_y=inv, init_z=ext, init_speed=speed)
    write_sim_params(sp)

code = argv[1]
mode = argv[2]

datadir = f'app/data/.storage/{code}'
fname = f'{datadir}/processed/{code}AV_agent0.csv'

df = pd.read_csv(fname)
df = df[df['Profit'] == df['Profit'].max()]
inv = round(float(df['Inventory'].values[0]), 2)
ext = round(float(df['External'].values[0]), 2)
speed = round(float(df['Speed'].values[0]), 2)
print(inv)
print(ext)
print(speed)

if mode == '--fine':
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
    update_fine(invlist, extlist)

elif mode == '--update-others':
    invlist = [0, 0.25, 0.5, 0.75, 1]
    extlist = [0, 0.25, 0.5, 0.75, 1]
    update_others(inv, ext, speed, invlist, extlist)

elif mode == '--final-update':
    update_final(inv, ext, speed)

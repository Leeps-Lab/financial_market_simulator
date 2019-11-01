import yaml
import shutil
import sys
import subprocess
import settings
from utility import (
    random_chars, get_interactive_agent_count, 
    get_simulation_parameters, copy_params_to_logs)
import atexit

def run_sim():
    cmd = [
        sys.executable,
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

def main():
    try:
        processes = []
        copy = settings.custom_config_path + '.copy'
        shutil.copyfile(settings.custom_config_path, copy)
        sp = get_simulation_parameters()
        formats = ['CDA', 'FBA']
        lambdaj = [0.5, 2, 5]
        lambdai = [[0.1, 0.05], [0.2, 0.1], [0.5, 0.25]]
        speed = [1000, 10000]
        time_in_force = [0.5, 2]

        for f in formats:
            for j in lambdaj:
                for i in lambdai:
                    for s in speed:
                        for t in time_in_force:
                            sp = update(sp,
                                focal_market_format=f,
                                lambdaJ=j,
                                lambdaI=i,
                                speed_unit_cost=s,
                                time_in_force=t
                            )
                            write_sim_params(sp)
                            processes.append(run_sim())
        for p in processes:
            p.wait()
    except:
        shutil.move(copy, settings.custom_config_path)
        e = sys.exc_info()[0]
        raise(e)

if __name__ == '__main__':
    main()

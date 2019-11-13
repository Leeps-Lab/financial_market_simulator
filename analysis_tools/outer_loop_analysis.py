from os import walk
import numpy as np
import pickle

''' Description

- outer_loop.py feeds session_codes to simulate.py of the form:
    RRRRRR##, where RRRRRR is a randomly generated 6-character alphanumeric
    code, and ## is sequential in 00 ... 71. This way, it is easy to link
    session codes with specific parameters.
- outer_loop.py creates an ndarray when it kicks off a simulation, then pickles
    it. This file loads that pickled data, then runs the following algorithm:

        for each session RRRRRR{00...71}:
            for each csv in RRRRRR##_agent{0, 1, 2}:
                agent_final = (csv[-1]{profit, a_y, a_z, speed})
                ndarray[f1(##)][f2(##)]...[fn(##)][agent_num] = agent_final

- convert ndarray to a multiindexed dataframe for ease of processing?

'''

def load_pickle():
    with open('app/data/sim_meta.pickle', 'rb') as f:
        return pickle.load(f)

def dump_pickle(a):
    with open('app/data/sim_results.pickle', 'wb') as f:
        pickle.dump(a, f)

def parse_files(session_code, nums):
    a0, a1, a2 = None, None, None
    for f in listdir('app/data/'):
        if f.startswith(session_code):
            if f.endswith(f'agent{nums[0]}.csv'):
                a0 = f'app/data/{f}'
            elif f.endswith(f'agent{nums[1]}.csv'):
                a1 = f'app/data/{f}'
            elif f.endswith(f'agent{nums[2]}.csv'):
                a2 = f'app/data/{f}'
    if not a0 and a1 and a2:
        print('Error: could not find agent csv files')
        print('Exiting')
        exit(1)
    return a0, a1, a2

def fill_array(code, array, imap, n):
    for i in range(n):
        i = str(i)
        if len(i) == 1:
            i = f'0{i}'
        session = f'{code}{i}'
        nums = (0, 1, 2)
        files = parse_files(session, nums)
        for i, fname in enumerate(files):
            with open(fname, 'r') as f:
                lines = f.readlines()
            profit_line = lines[-1]
            params_line = lines[-2]
            profit = profit_line.split(',')[-1]
            params = profit_line.split(',')
            y = params[1]
            z = params[2]
            speed = params[3]
            val = (y, z, speed, profit)
            indices = tuple(imap[n].append(i))
            array.itemset(indices, val)
    return array

def main():
    m = load_pickle()
    a = fill_array(**m)
    dump_pickle(a)

if __name__ == '__main__':
    main()

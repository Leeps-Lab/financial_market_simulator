from os import walk
import pandas as pd
import numpy as np
import pickle
from os import listdir
from sys import argv


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
    return [a0, a1, a2]

def build_df(code, params, imap, count):
    cols = ['Session Code', 'Agent ID', 'Tick']
    param_cols = list(params.keys())
    cols.extend(param_cols)
    cols.extend(['Inventory', 'External', 'Speed', 'Profit', 'Orders Executed', 'Reference Price'])
    df = pd.DataFrame(columns=cols)
    for j in range(count):
        i = str(j)
        if len(i) == 1:
            i = f'0{i}'
        session = f'{code}{i}'
        nums = (0, 1, 2)
        files = parse_files(session, nums)
        nums = (3, 4, 5)
        files += parse_files(session, nums)
        tup = imap[j]
        cparams = {k: v[tup[i]] for i, (k, v) in enumerate(params.items())}
        for c, fname in enumerate(files):
            if fname == None:
                continue
            agent_df = pd.read_csv(fname)
            for k, v in cparams.items():
                agent_df[k] = np.full(agent_df.shape[0], str(v))
            agent_df['Session Code'] = np.full(agent_df.shape[0], session)
            agent_df['Agent ID'] = np.full(agent_df.shape[0], c)
            agent_df['Tick'] = agent_df.index
            df = pd.concat([df, agent_df], ignore_index=True)
    df = df[cols]
    df.to_csv(f'app/data/{code}##_combined.csv')
    return df

def avg_profits(df, code):
    num_agents = len(df['Agent ID'].unique())
    agents = [df[df['Agent ID'] == i] for i in range(num_agents)] 
    
    # create a new empty df for each agent
    dfs = [pd.DataFrame(columns=df[['Inventory', 'External', 'Speed', 'Profit', 'Orders Executed', 'Reference Price']].columns) for _ in range(num_agents)]

    # avg across ticks
    for tick in df['Tick'].unique():
        # this will get the mean across all rows. For everything except profit,
        # each row will be the same (since it is corresponding ticks.
        # short and easy way to get this
        
        avgs = [agent_df[agent_df['Tick'] == tick][['Inventory','External','Speed','Profit', 'Orders Executed', 'Reference Price']].mean(axis=0) for agent_df in agents]

        for i, dfi in enumerate(dfs):
            dfi.loc[tick] = avgs[i]
    for i, dfi in enumerate(dfs):
        dfi.to_csv(f'app/data/{code}AV_agent{i}.csv')


# there wil lbe a different sim meta for each run.
"""
need a script that reads all sim metas fo
"""
def avg_profits_alt(df, code):
    num_agents = len(df['Agent ID'].unique())
    agents = [df[df['Agent ID'] == i] for i in range(num_agents)] 
    
    # create a new empty df for each agent
    dfs = [pd.DataFrame(columns=df[['Inventory', 'External', 'Speed', 'Profit', 'Orders Executed', 'Reference Price']].columns) for _ in range(num_agents)]

    # avg across ticks
    for tick in df['Tick'].unique():
        # this will get the mean across all rows. For everything except profit,
        # each row will be the same (since it is corresponding ticks.
        # short and easy way to get this
        
        avgs = [agent_df[agent_df['Tick'] == tick][['Inventory','External','Speed','Profit', 'Orders Executed', 'Reference Price']].mean(axis=0) for agent_df in agents]

        for i, dfi in enumerate(dfs):
            dfi.loc[tick] = avgs[i]
    for i, dfi in enumerate(dfs):
        dfi.to_csv(f'app/data/{code}AV_agent{i}.csv')

def main():
    m = load_pickle()
    df = build_df(**m)
    if len(argv) > 1 and argv[1] == '--avg':
        avg_profits(df, m['code'])

if __name__ == '__main__':
    main()

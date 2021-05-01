import pandas as pd
from os import listdir
from os.path import join
from itertools import product
"""
read all combined files in app/data
average each corresponding simulation file

"""
def dfwhere(df, params, values):
    dfslice = df
    for p, v in zip(params, values):
        dfslice = dfslice[dfslice[p] == v]
    return dfslice

inpath = join('app', 'data')
df_sorted_file = join(inpath, 'highest_outer_loop_profits.csv')
df_avg_ol_file = join(inpath, 'mean_outer_loop_combo.csv')
df_best_ol_file = join(inpath, 'best_outer_loop_combo.csv')

# read df for each group of sims
df = None
for fname in listdir(inpath):
    if fname.endswith('##_combined.csv'):
        fullpath = join(inpath, fname)
        df = pd.read_csv(fullpath, index_col=0)

assert(df is not None)
code = df['Session Code'].iloc[0]
numeric_cols = ['Inventory', 'External', 'Speed',
    'Profit', 'Orders Executed', 'Reference Price']

# remove session code and just keep session number
df['Session Code'] = df['Session Code'].map(lambda x: x[-2:])
# sort by profit and keep highest 30

df_sorted = df.nlargest(30, 'Profit')
# average all profits for each outer loop combo
params = ['Format', 'Lambda J', 'Lambda I', 'Speed Cost']#, 'Time in Force', 'Inventory Multiplier']
param_values = [list(df[e].unique()) for e in params]
param_values = list(product(*param_values))

df_avg_ol = pd.DataFrame(columns=df.columns)
df_best_ol = pd.DataFrame(columns=df.columns)
for i, combo in enumerate(param_values):
    dfslice = df[df['Agent ID'] == 0]
    dfslice = dfwhere(dfslice, params, combo)
    if len(dfslice) == 0:
        continue
    mean = dfslice.iloc[0].copy()
    mean[numeric_cols] = dfslice[numeric_cols].mean(axis=0)
    df_avg_ol.loc[i] = mean
    best = dfslice[dfslice['Profit'] == dfslice['Profit'].max()]
    df_best_ol.loc[i] = best.iloc[0]

df_sorted.to_csv(df_sorted_file)
df_avg_ol.to_csv(df_avg_ol_file)
df_best_ol.to_csv(df_best_ol_file)


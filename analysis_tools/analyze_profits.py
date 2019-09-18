import pandas as pd
from sys import argv
from os import listdir
'''
Description:
    Given a session code, looks in app/data for the trader CSV file,
    reads it into a dataframe, and extracts the final net worth of each trader
    at market end.

Usage:
    python3 analyze_profits.py <session_code>
'''

def read_csv(code):
    fpath = None
    prefix = f'{code}_agent'
    dirpath = 'app/data/'
    for f in listdir(dirpath):
        if f.startswith(prefix):
            fpath = f'{dirpath}{f}'
            break
    if not fpath:
        print(f'ERROR: agent file with session code {code} not found')
        exit(1)
    df = pd.read_csv(fpath)
    return df

# for now, we are just going to sum the total profits for trading firms
def extract_profits(df):
    df = df[['trigger_msg_type', 'trader_model_name', 'net_worth']]
    rows = df.loc[(df['trigger_msg_type'] == 'market_end') \
        & (df['trader_model_name'] == 'automated')]
    return sum(rows['net_worth'])

def main():
    if len(argv) != 2:
        usage()
    df = read_csv(argv[1])
    profits = extract_profits(df)
    print(profits)

if __name__ == '__main__':
    main()


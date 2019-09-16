import pandas as pd
from sys import argv
from os.path import splitext, split
import pickle

'''
Description:
    This program converts CSV files to dataframes and dictionaries.
    It can also pickle dataframes to a .pkl file or write a dict to a .txt file
    for ease of importing later.
    Functions can be run from the command line or from other python files.

Examples:
    - command line
        python3 transform_output.py str example.csv
        python3 transform_output.py pkl example.csv
    - in another .py file
        import transform_output
        mydf = transform_output.csv_to_df(<input_csv>)
        mydict = transform_output.csv_to_dict(<input_csv>)

Command line usage:
    python3 transform_output.py <output_type> <input_csv>
    <output_type>: one of str or pkl
        str:    converts csv to dict of form {col: {index: value}} and saves
                as input csv filename (w/o path) with extension .txt
        pkl:    converts csv to dataframe, then pickles it, saving it as
                input csv filename (w/o path) with extension .pkl
    <input_csv>: any csv
'''

def usage():
    print('Usage: python3 transform_output.py <output> <input>\n \
    <output>: one of \'pkl\' or \'str\'\n \
    <intput>: a CSV file')
    exit(1)

def csv_to_df(path):
    return pd.read_csv(path)

def csv_to_dict(path):
    return csv_to_df(path).to_dict()

def csv_to_string(path):
    d = csv_to_dict(path)
    _, fname = split(path)
    name, _ = splitext(fname)
    with open(f'{name}.txt', 'w') as outfile:
        outfile.write(str(d))

def csv_to_pickle(path):
    _, fname = split(path)
    name, _ = splitext(fname)
    csv_to_df(path).to_pickle(f'{name}.pkl')

def main():
    if argv[1] not in ['pkl', 'str'] or len(argv) != 3:
        usage()
    elif argv[1] == 'pkl':
        csv_to_pickle(argv[2])
    elif argv[1] == 'str':
        csv_to_string(argv[2])

if __name__ == '__main__':
    main()


from os import listdir
from sys import argv
from shutil import copyfile

code = argv[1]

othercodes = set()
for f in listdir('app/data/'):
    if f.endswith('csv') and not f.startswith(code):
        othercodes.add(f[:6])

othercodes = sorted(list(othercodes))

for f in listdir('app/data/'):
    if f.endswith('csv') and not f.startswith(code):
        i = othercodes.index(f[:6]) + 1
        newcode = f'{code}{i}{f[7]}{f[8:]}'
        copyfile(f'app/data/{f}', f'app/data/{newcode}')

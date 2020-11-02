from sys import argv

fname = argv[1]
with open(fname, 'r') as f:
    lines = f.readlines()
lines = [line.split() for line in lines]
# matrix takes form
# buy_pegged    buy_lit
# sell_pegged       sell_lit
# i0 is buy v sell, i1 is pegged v lit
m = [[0,0],[0,0]]
for line in lines:
    i0 = 0 if line[0] == 'buy' else 1
    i1 = 0 if line[1] == 'True' else 1
    m[i0][i1] += 1

pegged = m[0][0] + m[1][0]
lit = m[0][1] + m[1][1]
buy = m[0][0] + m[0][1]
sell = m[1][0] + m[1][1]

print('peg proportion:', pegged / (pegged + lit))
print('buy proportion:', buy / (buy + sell))
for mm in m:
    print(mm)


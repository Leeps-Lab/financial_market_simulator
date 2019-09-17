from termcolor import colored as c
from math import ceil
import argparse

'''
Author: Eli Pandolfo (github elip12)
Description:
    This script ensures that the exchange is calculating the
    clearing price correctly. It reads the logs from the simulator
    run with debug mode on, and parses the order books and market
    clearing price for each batch auction.

    It then performs an alternate algorithm for calculating clearing price,
    and checks that the two clearing prices match.

Usage:
    In one shell:
        `cd financial_market_simulator`
        `python3 dbreset.py`
        `python3 run_web_api.py 2> debug_output.out`
    In another shell:
        `curl http://localhost:5000/v1/simulate?debug=true`
        or hit that endpoint in your browser
    Wait for the simulation to run (usually about 10 more seconds than
    session_duration specified in parameters.yaml). You know it ended
    if you do `tail debug_output.out` and see a psycopg2 warning at the
    end of the file.
    In the first shell:
        ctl-C the simulator
        `cd analysis_tools`
        `python3 check_clearing_price.py ../debug_output.out`

    You can optionally turn on debug mode with the -d flag when you run
    this program.
    This program prints its output to stdout (even debug output)
'''
# TODO: make debug messages print to stderr

DEBUG = False

def perr(*args):
    s = ''.join(['{} ' for arg in args])
    s = s.format(*args)
    print(c(s, 'red'))

def pwarn(*args):
    s = ''.join(['{} ' for arg in args])
    s = s.format(*args)
    print(c(s, 'magenta'))

def printd(*args):
    if DEBUG:
        print(*args)

def pinfo(*args):
    if DEBUG:
        s = ''.join(['{} ' for arg in args])
        s = s.format(*args)
        print(c(s, 'yellow'))

def pgrn(*args):
    s = ''.join(['{} ' for arg in args])
    s = s.format(*args)
    print(c(s, 'green'))

'''
ai: ask index
ca: current ask
qa: quantity at current ask
bi: bid index
cb: current bid
qb: quantity at current bid
'''
def check_clearing_price(asks, bids, expected):
    if not asks or not bids:
        if expected != 'None':
            return False
        return True
    ai = 0
    bi = 0
    ca = asks[ai][0]
    qa = asks[ai][1]
    cb = bids[bi][0]
    qb = bids[bi][1]
    p = 0
    q = 0
    if ca > cb:
        if expected != 'None':
            return False
    elif ca == cb:
        p = ca
        printd('  calculated clearing price:', p)
        if p != int(expected):
            return False
    else:
        while ca < cb:
            qa -= 1
            if qa == 0:
                ai += 1
                ca = asks[ai][0]
                qa = asks[ai][1]
            qb -= 1
            if qb == 0:
                bi += 1
                cb = bids[bi][0]
                qb = bids[bi][1]
        if ca == cb:
            p = ca
        elif qa == asks[ai][1] and qb == bids[bi][1]:
            prior_ask = asks[ai - 1][0]
            prior_bid = bids[bi - 1][0]
            h = min(prior_bid, ca)
            l = max(prior_ask, cb)
            p = ceil((h + l) / 2)
        else:
            p = min(ca, cb)
        printd('  calculated clearing price:', p)
        if p != int(expected):
            return False
    return True
        

def parse_logs(path):
    success = True
    with open(path, 'r') as f:
        line = True
        count = 0
        while line:
            i = -1
            while i == -1:
                line = f.readline()
                if not line:
                    return success
                count += 1
                i = line.find('ask prices=')
            pinfo('processing line', count)
            l_ask = count
            ask_prices = line[i + len('ask prices='):]
            ask_prices = ask_prices[:ask_prices.index(':')]
            ask_prices = eval(ask_prices)
            printd('  ask prices:', ask_prices)
            i = -1
            while i == -1:
                line = f.readline()
                count += 1
                i = line.find('bid prices=')
            pinfo('processing line', count)
            l_bid = count
            if l_bid - l_ask > 10:
                pwarn('Warn: bid line is too far from ask line, skipping')
                continue
            bid_prices = line[i + len('bid prices='):]
            bid_prices = bid_prices[:bid_prices.index(':')]
            bid_prices = eval(bid_prices)
            printd('  bid prices:', bid_prices)
            i = -1
            while i == -1:
                line = f.readline()
                count += 1
                i = line.find('market clears @ ')
            pinfo('processing line', count)
            l_clear = count
            if l_clear - l_bid > 50:
                pwarn('Warning: clear line is too far from bid line, skipping')
                continue
            clearing_price = line[i + len('market clears @ '):].strip()
            printd('  clearing price:', clearing_price)
            valid = check_clearing_price(ask_prices, bid_prices, clearing_price)
            if not valid:
                perr('Clearing prices do not match')
                success = False

def main():
    parser = argparse.ArgumentParser(description='Check exchange clearing \
    prices are calculated correctly.')
    parser.add_argument('path', metavar='<logfile>', type=str,
                        help='a simulation log file to scan')
    parser.add_argument('-d', dest='debug', action='store_true',
                        default=False,
                        help='debug mode on')

    args = parser.parse_args()
    global DEBUG
    DEBUG = args.debug
    if DEBUG:
        printd('debug mode on')
    
    success = parse_logs(args.path)
    if success:
        pgrn('All clearing prices match')

if __name__ == '__main__':
    main()


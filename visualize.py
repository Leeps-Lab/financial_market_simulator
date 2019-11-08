import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import style
style.use('./analysis_tools/elip12.mplstyle')
import matplotlib.pyplot as plt   
import configargparse
from utility import get_simulation_parameters
import settings
from os import listdir

TEXT = '#848484'
plt.rcParams.update({'font.size': 6})
A2_color = '#d22b10'
A1_color = '#eb860d'
A0_color = '#e0cc05'
inventory_color = '#60d515'
speed_color = '#b113ef'
external_color = '#1fa8e4'

def bar(a):
    xs = [i for i, x in enumerate(a['Speed']) \
        if i > 0 and x == 1 and a['Speed'][i - 1] == 0]
    num = 0
    widths = []
    for i, x in enumerate(a['Speed']):
        if i > 0 and a['Speed'][i - 1] == 1 \
            and (x == 0 or i == len(a['Speed']) - 1):
            widths.append(num)
            num = 0
        elif i > 0 and x == 1:
            num += 1
    assert(len(xs) == len(widths))
    if not xs and not widths:
        xs.append(0)
        widths.append(0)
    return xs, widths

def plot(a0, a1, a2, session_code, nums):
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, sharex=True)
    
    # profit graph
    ax1.plot(a0['Profit'], label=f'A{nums[0]}', linewidth=.75, color=A0_color)
    ax1.plot(a1['Profit'], label=f'A{nums[1]}', linewidth=.75, color=A1_color)
    ax1.plot(a2['Profit'], label=f'A{nums[2]}', linewidth=.75, color=A2_color)
    ax1.set_ylabel('Profit', color=TEXT)
    ax1.set_title(f'{session_code} Agents {nums[0]}, {nums[1]}, {nums[2]} Optimization Parameters')
    ax1.legend(loc='upper left', bbox_to_anchor=(-0.255, 0.75))
    ax1.set_yscale('log')

    # agent 0
    ax2.plot(a0['Inventory'], zorder=3, linewidth=.5, color=inventory_color)
    ax2.plot(a0['External'], zorder=3, linewidth=.5, color=external_color)
    xs, widths = bar(a0)
    ax2.bar(xs, 1, width=widths, align='edge', color=speed_color, zorder=2,
        alpha=0.25)
    
    ax2.set_ylabel(f'Agent {nums[0]} (A{nums[0]})', color=A0_color)
    params = get_simulation_parameters()
    ax2.text(-0.25, -2.6, '\n'.join([
        'Parameters:',
        f'- duration: {params["session_duration"]}',
        f'- fund noise $\mu$: {params["fundamental_value_noise_mean"]}',
        f'- fund noise $\sigma$: {params["fundamental_value_noise_std"]}',
        f'- exo noise $\mu$: {params["exogenous_order_price_noise_mean"]}',
        f'- exo noise $\sigma$: {params["exogenous_order_price_noise_std"]}',
        f'- init price: {params["initial_price"]}',
        f'- time in force: {params["time_in_force"]}',
        f'- bid-ask offset: {params["bid_ask_offset"]}',
        f'- focal format: {params["focal_market_format"]}',
        f'- FBA interval: {params["focal_market_fba_interval"] if params["focal_market_format"] == "FBA" else "N/A"}',
        f'- $\lambda$ J: {params["lambdaJ"]}',
        f'- $\lambda$ I: {params["lambdaI"]}',
        f'- tax rate: {params["tax_rate"]}',
        f'- k ref price: {params["k_reference_price"]}',
        f'- k signed vol: {params["k_signed_volume"]}',
        f'- a_x mult: {params["a_x_multiplier"]}',
        f'- a_y mult: {params["a_y_multiplier"]}',
        f'- speed cost: {params["speed_unit_cost"]}',
        f'- init y: {params["init_y"]}',
        f'- init z: {params["init_z"]}',
        f'- step: {params["step"]}',
        f'- symmetric: {params["symmetric"]}',
        f'- num moves: {params["num_moves"]}',
        f'- move interval: {params["move_interval"]}',
        ]),
        fontsize=5, transform=ax2.transAxes, horizontalalignment='left',
        verticalalignment='bottom'
    )
    # agent 1
    ax3.plot(a1['Inventory'], zorder=3, linewidth=.5, color=inventory_color)
    ax3.plot(a1['External'], zorder=3, linewidth=.5, color=external_color)
    xs, widths = bar(a1)
    ax3.bar(xs, 1, width=widths, align='edge', color=speed_color, zorder=2,
        alpha=0.25)
    ax3.set_ylabel(f'Agent {nums[1]} (A{nums[1]})', color=A1_color)
    # agent 2
    ax4.plot(a2['Inventory'], zorder=3, linewidth=.5, label='Inventory',
        color=inventory_color)
    ax4.plot(a2['External'], zorder=3, linewidth=.5, label='External',
        color=external_color)
    xs, widths = bar(a2)
    ax4.bar(xs, 1, width=widths, align='edge', color=speed_color, zorder=2,
        alpha=0.25, label='Speed')
    ax4.set_ylabel(f'Agent {nums[2]} (A{nums[2]})', color=A2_color)
    ax4.legend(loc='upper center', bbox_to_anchor=(-0.175, 3.15))
    #ax4.tick_params(labelbottom=False) 
    plt.subplots_adjust(left=0.20, right=0.98, top=0.95, bottom=0.05)
    plt.savefig(f'app/data/{session_code}_agents{nums[0]}{nums[1]}{nums[2]}.png', dpi=350)

def read_csvs(a0, a1, a2):
    a0 = pd.read_csv(a0)
    a1 = pd.read_csv(a1)
    a2 = pd.read_csv(a2)
    return a0, a1, a2


def parse_files(session_code, nums):
    a0, a1, a2 = None, None, None
    custom_param = False
    for f in listdir('app/data/'):
        if f.startswith(session_code):
            if f.endswith('parameters.yaml'):
                settings.custom_config_path = f'app/data/{f}'
                custom_param = True
            elif f.endswith(f'agent{nums[0]}.csv'):
                a0 = f'app/data/{f}'
            elif f.endswith(f'agent{nums[1]}.csv'):
                a1 = f'app/data/{f}'
            elif f.endswith(f'agent{nums[2]}.csv'):
                a2 = f'app/data/{f}'
    if not a0 and a1 and a2:
        print('Error: could not find agent csv files')
        print('Exiting')
        exit(1)
    if not custom_param:
        print('Warning: could not find session parameters file')
        print('Continuing using \'parameters.yaml\'')
    return a0, a1, a2

def main():
    p = configargparse.getArgParser()
    p.add('session_code', nargs='+', help='8-digit alphanumeric')
    options, args = p.parse_known_args()
    nums = (0, 1, 2)
    for code in options.session_code:
        csvs = parse_files(code, nums)
        a0, a1, a2 = read_csvs(*csvs)
        plot(a0, a1, a2, code, nums)

if __name__ == '__main__':
    main()

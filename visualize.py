import numpy as np
import pandas as pd
import matplotlib
#matplotlib.use('Agg')
from matplotlib import style
style.use('./analysis_tools/elip12.mplstyle')
import matplotlib.pyplot as plt   
import configargparse
from utility import get_simulation_parameters
import settings
from os import listdir
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.lines import Line2D

TEXT = '#848484'
plt.rcParams.update({'font.size': 6})
A2_color = '#d22b10'
A1_color = '#eb860d'
A0_color = '#e0cc05'
inventory_color = '#60d515'
speed_color = '#b113ef'
gray_color = '#222222'
external_color = '#1fa8e4'

def bar(a):
    xs = [i - 1 for i, x in enumerate(a['Speed']) \
        if i > 0 and x == 1 and (a['Speed'][i - 1] == 0 or i == 1)]
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

def scatter3d(a0, session_code):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    colors = [speed_color if s == 1 else TEXT for s in a0['Speed']]
    ax.scatter(a0['Inventory'], a0['External'], zs=a0['Profit'], c=colors)
   
    props = {'color': TEXT}
    ax.set_xlabel('Inventory', **props)
    ax.set_ylabel('External', **props)
    ax.set_zlabel('Profit', **props)
    custom2 = [
        Line2D([0], [0], color=speed_color, lw=3),
        Line2D([0], [0], color=TEXT, lw=3),
    ]
    ax.legend(custom2, ['Speed On', 'Speed Off'])
    ax.xaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor(TEXT)
    ax.yaxis.pane.fill = False
    ax.yaxis.pane.set_edgecolor(TEXT)
    ax.zaxis.pane.fill = False
    ax.zaxis.pane.set_edgecolor(TEXT)

    plt.title(f'{session_code} Agent 0 profit vs parameters')
    
    plt.show()

def heatmap(a0, session_code):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.5), tight_layout=True)
    
    props = {'color': TEXT}
    # speed off
    speed_off = a0[a0['Speed'] == 0]
    min_profit, max_profit = speed_off['Profit'].min(), speed_off['Profit'].max()
    normalize = lambda x: (x - min_profit) / (max_profit - min_profit)
    normalized_profits = [normalize(x) for x in speed_off['Profit']]
    s1 = ax1.scatter(speed_off['Inventory'], speed_off['External'], c=speed_off['Profit'],
    cmap='plasma', s=10)
    ax1.set_xlabel('Inventory', **props)
    ax1.set_ylabel('External', **props)
    ax1.set_title('Speed OFF')
    cb = fig.colorbar(s1)
    cb.set_label('Profit', **props)
    
    # speed on
    speed_on = a0[a0['Speed'] == 1]
    min_profit, max_profit = speed_on['Profit'].min(), speed_on['Profit'].max()
    normalized_profits2 = [normalize(x) for x in speed_on['Profit']]
    s = ax2.scatter(speed_on['Inventory'], speed_on['External'], c=speed_on['Profit'],
    cmap='plasma', s=10)
    ax2.set_xlabel('Inventory', **props)
    ax2.set_ylabel('External', **props)
    ax2.set_title('Speed ON')
    cb = fig.colorbar(s)
    cb.set_label('Profit', **props)

    plt.show()

def plot(a0, a1, a2, session_code, nums):
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, sharex=True)
    
    # profit graph
    ax1.plot(a1['Profit'], label=f'A{nums[1]}', linewidth=.75, marker='o', markersize='1', linestyle=':', color=A1_color)
    ax1.plot(a2['Profit'], label=f'A{nums[2]}', linewidth=.75, marker='o', markersize='1', linestyle=':', color=A2_color)
    ax1.plot(a0['Profit'], label=f'A{nums[0]}', linewidth=.75, marker='o', markersize='1', linestyle=':', color=A0_color)
    ax1.set_ylabel('Profit', color=TEXT)
    ax1.set_title(f'{session_code} Agents {nums[0]}, {nums[1]}, {nums[2]} Optimization Parameters')
    ax1.legend(loc='upper left', bbox_to_anchor=(-0.255, 0.75))
    #ax1.set_yscale('log')

    # agent 
    ax2.plot(a0['Inventory'], zorder=3, linewidth=.5, color=inventory_color)
    ax2.plot(a0['External'], zorder=3, linewidth=.5, color=external_color)
    #ax2.fill_between(a0['Speed'], np.zeros(len(a1['Speed'])), zorder=2, drawstyle='steps-post', color=speed_color,
    #    alpha=0.25)
    
    xs, widths = bar(a0)
    ax2.bar(xs, np.ones(len(xs)), width=widths, align='edge', color=speed_color, zorder=2, alpha=0.25)
    
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
        f'- explore all: {params["explore_all"]}',
        f'- submoves: {params["explore_all_num_submoves"]}',
        ]),
        fontsize=5, transform=ax2.transAxes, horizontalalignment='left',
        verticalalignment='bottom'
    )
    # agent 1
    ax3.plot(a1['Inventory'], zorder=3, linewidth=.5, color=inventory_color)
    ax3.plot(a1['External'], zorder=3, linewidth=.5, color=external_color)
    #ax3.fill_between(a1['Speed'], np.zeros(len(a1['Speed'])), zorder=2, drawstyle='steps-post', color=speed_color,
    #    alpha=0.25)
    xs, widths = bar(a1)
    ax3.bar(xs, np.ones(len(xs)), width=widths, align='edge', color=speed_color, zorder=2,
        alpha=0.25)
    ax3.set_ylabel(f'Agent {nums[1]} (A{nums[1]})', color=A1_color)
    # agent 2
    ax4.plot(a2['Inventory'], zorder=3, linewidth=.5, label='Inventory',
        color=inventory_color)
    ax4.plot(a2['External'], zorder=3, linewidth=.5, label='External',
        color=external_color)
    #ax4.fill_between(a2['Speed'], np.zeros(len(a2['Speed'])),  zorder=2, drawstyle='steps-post', color=speed_color,
    #    alpha=0.25)
    xs, widths = bar(a2)
    ax4.bar(xs, np.ones(len(xs)), width=widths, align='edge', color=speed_color, zorder=2,
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
    p.add('--scatter3d', action='store_true', 
    help='create and display (interactive mode) a 3d scatter plot for agent 0')
    p.add('--heatmap', action='store_true',
    help='display 2d heat maps for agent 0 for speed on/off')
    options, args = p.parse_known_args()
    nums = (0, 1, 2)
    a0 = None
    for code in options.session_code:
        csvs = parse_files(code, nums)
        a0, a1, a2 = read_csvs(*csvs)
        plot(a0, a1, a2, code, nums)
    if options.scatter3d is True:
        scatter3d(a0, options.session_code)
    if options.heatmap is True:
        heatmap(a0, options.session_code)

if __name__ == '__main__':
    main()

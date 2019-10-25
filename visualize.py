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

def plot(a0, a1, a2, session_code):
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, sharex=True)
    
    # profit graph
    ax1.plot(a0['Profit'], label='A0', linewidth=.75, color=A0_color)
    ax1.plot(a1['Profit'], label='A1', linewidth=.75, color=A1_color)
    ax1.plot(a2['Profit'], label='A2', linewidth=.75, color=A2_color)
    ax1.set_ylabel('Profit', color=TEXT)
    ax1.set_title(f'{session_code} Agent Optimization Parameters')
    ax1.legend(loc='upper left', bbox_to_anchor=(-0.255, 0.75))

    # agent 0
    ax2.plot(a0['Inventory'], zorder=3, linewidth=.5, color=inventory_color)
    ax2.plot(a0['External'], zorder=3, linewidth=.5, color=external_color)
    ax2.fill_between(np.arange(len(a0['Speed'])), a0['Speed'], linestyle='None',
	zorder=2, color=speed_color, alpha=.2)
    ax2.set_ylabel('Agent 0 (A0)', color=A0_color)
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
    ax3.fill_between(np.arange(len(a1['Speed'])), a1['Speed'], linestyle='None',
	zorder=2, color=speed_color, alpha=.2)
    ax3.set_ylabel('Agent 1 (A1)', color=A1_color)
    # agent 0
    ax4.plot(a2['Inventory'], zorder=3, linewidth=.5, label='Inventory',
        color=inventory_color)
    ax4.plot(a2['External'], zorder=3, linewidth=.5, label='External',
        color=external_color)
    ax4.fill_between(np.arange(len(a2['Speed'])), a2['Speed'], linestyle='None',
	zorder=2, color=speed_color, alpha=.2, label='Speed')
    ax4.set_ylabel('Agent 2 (A2)', color=A2_color)
    ax4.legend(loc='upper center', bbox_to_anchor=(-0.175, 3.15))
    #ax4.tick_params(labelbottom=False)
    
    plt.subplots_adjust(left=0.20, right=0.98, top=0.95, bottom=0.05)
    plt.savefig(f'app/data/{session_code}_agents.png', dpi=350)

def read_csvs(a0, a1, a2):
    a0 = pd.read_csv(a0)
    a1 = pd.read_csv(a1)
    a2 = pd.read_csv(a2)
    return a0, a1, a2


def parse_files(session_code):
    a0, a1, a2 = None, None, None
    custom_param = False
    for f in listdir('app/data/'):
        if f.startswith(session_code):
            if f.endswith('parameters.yaml'):
                settings.custom_config_path = f'app/data/{f}'
                custom_param = True
            elif f.endswith('agent0.csv'):
                a0 = f'app/data/{f}'
            elif f.endswith('agent1.csv'):
                a1 = f'app/data/{f}'
            elif f.endswith('agent2.csv'):
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
    p.add('session_code', help='8-digit alphanumeric')
    options, args = p.parse_known_args()
    csvs = parse_files(options.session_code)
    a0, a1, a2 = read_csvs(*csvs)
    plot(a0, a1, a2, options.session_code)

if __name__ == '__main__':
    main()

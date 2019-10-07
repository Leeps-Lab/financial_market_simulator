# This class tunes an agent's parameters in order to optimize profits. The
# on_tick method gets called every 3 seconds for each agent.

from high_frequency_trading.hft.incoming_message import IncomingMessage
import random
import time
from utility import get_interactive_agent_count, get_simulation_parameters
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import style
style.use('./analysis_tools/elip12.mplstyle')
import matplotlib.pyplot as plt   
import itertools

INIT_Y = 0.5
INIT_Z = 0.5
TICK = 0.05
NUM_MOVES = 8
MOVE_INTERVAL = 3.0

class AgentSupervisor():
    def __init__(self, session_code, config_num, agent):
        self.session_code = session_code
        self.config_num = config_num
        self.agent = agent
        self.num_agents = get_interactive_agent_count(
            get_simulation_parameters()['agent_state_configs'])
        self.elapsed_turns = -1
        self.market_id = agent.model.market_id
        self.subsession_id = agent.model.subsession_id
        self.prev_params = {
            'a_x': 0.0,
            'a_y': INIT_Y,
            'a_z': INIT_Z,
            'speed': 0,
        }
        self.curr_params = {
            'a_x': 0.0,
            'a_y': INIT_Y,
            'a_z': INIT_Z, 
            'speed': 0,
        }
        self.current = 'a_y'
        self.current_profits = 0.0
        self.previous_profits = 0.0
        self.tick = TICK
        self.y_array = []
        self.z_array = []
        self.profit_array = []
        self.speed_array = []

    def get_profits(self):
        self.current_profits = self.agent.model.net_worth
        if self.curr_params['speed'] == 1:
            penalty = get_simulation_parameters()['speed_unit_cost'] * MOVE_INTERVAL
            self.current_profits -= penalty

    def bounds_check(self):
        if self.curr_params[self.current] > 1.0:
            self.curr_params[self.current] = 1.0
        elif self.curr_params[self.current] < 0.0:
            self.curr_params[self.current] = 0.0

    def random_direction(self):
        if random.random() < 0.5:
            self.curr_params[self.current] += self.tick
            self.bounds_check()
        else:
            self.curr_params[self.current] -= self.tick
            self.bounds_check()

    def same_direction(self):
        if self.curr_params[self.current] > self.prev_params[self.current]:
            self.curr_params[self.current] += self.tick
            self.bounds_check()
        elif self.curr_params[self.current] < self.prev_params[self.current]:
            self.curr_params[self.current] -= self.tick
            self.bounds_check()
        else:
            self.random_direction()

    def opposite_direction(self):
        if self.curr_params[self.current] > self.prev_params[self.current]:
            self.curr_params[self.current] -= 2 * self.tick
            self.bounds_check()
        elif self.curr_params[self.current] < self.prev_params[self.current]:
            self.curr_params[self.current] += 2 * self.tick
            self.bounds_check()
        else:
            self.random_direction()

    def get_next_param(self): # add speed later
        if self.current == 'a_y':
            self.current = 'a_z'
        elif self.current == 'a_z':
            self.current = 'speed'
        elif self.current == 'speed':
            self.current = 'a_y'

    def switch_speed(self):
        if self.curr_params['speed'] == 0:
            self.curr_params['speed'] = 1
        elif self.curr_params['speed'] == 1:
            self.curr_params['speed'] = 0
    
    @staticmethod
    def gel(cur, prev, tolerance=9999):
        if cur - prev > tolerance:
            return 1
        elif cur - prev < -tolerance:
            return -1
        else:
            return 0

    # NOTE: WIP
    def compute_inventory_param(b):
        a = 0.01
        t = self.elapsed_turns
        b = 100
        tau = get_simulation_parameters()['session_duration']


    def update_params(self):
        if self.gel(self.current_profits, self.previous_profits) == 1:
            if self.current != 'speed':
                self.same_direction()
        elif self.gel(self.current_profits, self.previous_profits) == -1:
            if self.current != 'speed':
                self.opposite_direction()
            else:
                self.switch_speed()
        else:
            self.get_next_param()
            if self.current != 'speed':
                self.same_direction()
        
        # update previous
        self.previous_profits = self.current_profits
        self.prev_params = self.curr_params.copy()

    def send_message(self):
        if self.current != 'speed':
            message = {
                'type': 'slider',
                'subsession_id': self.subsession_id,
                'market_id': self.market_id,
                'a_x': self.curr_params['a_x'],
                'a_y': self.curr_params['a_y'],
                'a_z': self.curr_params['a_z'],
            }
            message = IncomingMessage(message) 
            event = self.agent.event_cls('agent', message) 
            self.agent.model.user_slider_change(event)
        else:
            s = self.agent.model.technology_subscription
            if self.curr_params['speed'] == 1 and not s.is_active:
                s.activate()
            elif self.curr_params['speed'] == 0 and s.is_active:
                s.deactivate()

    def print_status(self, msg=''):
        print(msg, self.config_num, 'profits:', self.agent.model.net_worth,
            'speed', self.curr_params['speed'],
            'a_y:', round(self.curr_params['a_y'], 2),
            'a_z:', round(self.curr_params['a_z'], 2))
    
    @property
    def my_turn(self):
        m = int(self.elapsed_turns / NUM_MOVES) % self.num_agents
        if m == self.config_num:
            return True
        else:
            return False

    def on_tick(self, is_dynamic):
        self.elapsed_turns += 1
        if not is_dynamic:
            return
        self.get_profits()
        if self.my_turn:
            self.update_params()
            self.send_message()
        #    self.print_status()

        # update arrays for graphing
        self.y_array.append(self.curr_params['a_y'])
        self.z_array.append(self.curr_params['a_z'])
        self.profit_array.append(self.current_profits)
        self.speed_array.append(self.curr_params['speed'])

        print(self.curr_params['speed'], self.agent.model.technology_subscription.is_active)

    def at_start(self, is_dynamic):
        self.send_message()

    def at_end(self, is_dynamic):
        if is_dynamic:
            self.print_status('FINAL')
            df = pd.DataFrame(list(itertools.zip_longest(
                self.y_array, self.z_array, self.speed_array, self.profit_array)),
                columns=['Inventory', 'External', 'Speed', 'Profit'])
            df.to_csv(f'app/data/{self.session_code}_agent{self.config_num}.csv')


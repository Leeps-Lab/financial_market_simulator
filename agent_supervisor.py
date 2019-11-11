# agent_supervisor.py
# Author: Eli Pandolfo <epandolf@ucsc.edu>

from math import expm1, ceil
import random
import time
import itertools
import redis
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import style
style.use('./analysis_tools/elip12.mplstyle')
import matplotlib.pyplot as plt   
from high_frequency_trading.hft.incoming_message import IncomingMessage
from utility import get_interactive_agent_count, get_simulation_parameters
import draw
from discrete_event_emitter import RandomOrderEmitter
from shutil import copyfile
''' 
DESCRIPTION
    This file defines a class called AgentSupervisor.
    An AgentSupervisor acts as a puppetmaster for a DynamicAgent, and attempts
    to optimize the agent's optimizable parameters (explained below) in order
    to maximize that agent's profit.
    One AgentSupervisor instance is invoked for each DynamicAgent per
    simulation. The instantiation occurs in run_agent.py.

    Note: when I say agent in the following sections, I am conflating
    an agent with an AgentSupervisor, since they can be thought of
    as interchangable in that they combine to become a sort of single supervised
    agent entity.

    A simulation is broken up into turns. Agents alternate turns. So,
    agent0 takes a turn, then agent1 takes a turn, then agent2 takes a turn,
    then agent0 takes a turn, and so on. ALL AGENTS ARE SUBMITTING ORDERS AT
    ALL TIMES, NOT JUST ON THEIR TURN. Turns are broken up into moves.
    Relevant parameters are num_moves and move_interval. So, if num_moves is
    8, and move_interval is 3, each agent on its turn
    makes 1 move every 3 seconds for 8 moves. Then their turn is over, and the
    next agent takes 8 3-second moves.

    "Taking a move" means adjusting a single parameter available for
    optimization. Right now, those parameters are
        - sensitivity to inventory: A_Y, a value in range [0,1]
        - sensitivity to external market: A_Z, a value in range [0,1]
        - speed: on/off (1/0)
    Note that sensetivity to inventory is scaled by a multiplier, specified
    in parameters.yaml.

    An agent may only change one parameter per move. Speed is a boolean,
    so it gets toggled from off to on or vice versa. A_Y and A_Z are continuous
    values, but they are discretized into ranges with interval 'step'. Step
    is defined in parameters.yaml. So, if step=0.05, on an agent's turn, it could
    turn speed on, then change A_Y from 0.50 to 0.55, then change A_Y from 0.55
    to 0.60, then change A_Z from 0.50 to 0.45, etc.

    When switching to a new parameter, the order is always
        A_Y -> A_Z -> speed -> A_Y... This is arbitrary.

    A brief description of strategy:
        if your profit immediately before this move is greater than your profit
        immediately before the previous move (not necessarily your previous move)
        by some threshhold:
            whatever you changed previously was beneficial, so keep changing it
            in the same direction
        if your profit immediately before this move is less than your profit
        immediately before the previous move (not necessarily your previous move)
        by some threshhold:
            whatever you changed previously was detrimental, so change it in
            the opposite direction
        if your profit immediately before this move is about the same as your profit
        immediately before the previous move (not necessarily your previous move)
        by some threshhold:
            whatever you changed previously had little effect, so switch
            parameters (eg if you were changing A_Y, switch to A_Z) and update
            the new parameter.

SYMMETRIC MODE
    One modification of this is symmetric mode. You can define it to be on
    in parameters.yaml (symmetric: true).
    In this mode, at the beginning of an agent's turn, it adjusts its parameters
    to match the parameters of the agent with the highest profits. We use redis
    to accomplish this, because
        (1) it's faster than writing to a file,
        (2) it's easier than using websockets,
        (3) the simulation already uses it so no new dependencies are needed.
    
    This is exciting because now that we have this feature, we can easily extend
    it so that agents can analyze each other and learn from each other.

TERMINOLOGY
    agent:  a DynamicAgent object
    tick:   every <move_interval> seconds, a tick occurs. On a tick, each agent
            stores its current profits and params in redis, and, if it is that
            agent's turn, takes a move.
    move:   an opportunity for a single agent to adjust a single parameter.
    turn:   <num_moves> consecutive moves makes up an agent's turn. They spend
            their turn attempting to optimize their params to maximize profit.
    profit: an agent's net worth, calculated at the most recent tick.
    A_Y:    sensitivity to inventory, float in [0,1]
    A_Z:    sensitivity to external, float in [0,1]
    speed:  toggle whether agent is currently subscribed to speed technology
    step:   the amount by which A_Y or A_Z can change on a move
'''
class AgentSupervisor():
    def __init__(self, session_code, config_num, agent):
        # agent metadata, does not change during simulation
        self.session_code = session_code # used for naming files
        self.config_num = config_num # this agent's id in {0,1,2}
        self.agent = agent # this agent object (isntanceof DynamicAgent)
        self.sp = get_simulation_parameters() # sim params (from parameters.yaml)
        self.num_agents = get_interactive_agent_count( # num DynamicAgents in sim
            self.sp['agent_state_configs'])
        self.market_id = agent.model.market_id # necessary for sending messages
        self.subsession_id = agent.model.subsession_id # ""
        self.step = self.sp['step'] # step size, described above
        if self.sp['symmetric']: # redis connection
            self.r = redis.Redis(
                host='localhost',
                port=6379,
            )
        else:
            self.r = None
        self.prev_random_orders = None
        
        # agent optimization data, changes during simulation
        self.elapsed_seconds = 0
        self.elapsed_ticks = -1 # number of elapsed ticks 
        self.prev_params = { # params before most recent update
            'a_x': 0.0,
            'a_y': self.sp['init_y'],
            'a_z': self.sp['init_z'],
            'speed': 0,
        }
        self.curr_params = { # current parameters
            'a_x': 0.0,
            'a_y': self.sp['init_y'],
            'a_z': self.sp['init_z'], 
            'speed': 0,
        }
        self.current = 'a_y' # current parameter being adjusted
        self.current_profits = 0.0 # current profits
        self.previous_profits = 0.0 # profits before most recent tick
        self.y_array = [] # appended to each tick, used for creating graphs
        self.z_array = []
        self.profit_array = []
        self.speed_array = []
        self.event_log = f'app/logs/{self.session_code}_agent{self.config_num}.log'
        self.current_log_row = ''

    # compares cur and prev given tolerance
    @staticmethod
    def gel(cur, prev, tolerance=9999):
        if cur - prev > tolerance:
            return 1
        elif cur - prev < -tolerance:
            return -1
        else:
            return 0
    
    # switches self.current_param to a the next param in the cycle
    def get_next_param(self): # add speed later
        if self.current == 'a_y':
            self.current = 'a_z'
        elif self.current == 'a_z':
            self.current = 'speed'
        elif self.current == 'speed':
            self.current = 'a_y'
    
    # ensures params cannot go below 0 or above 1
    def bounds_check(self):
        if self.curr_params[self.current] > 1.0:
            self.curr_params[self.current] = 1.0
        elif self.curr_params[self.current] < 0.0:
            self.curr_params[self.current] = 0.0

    # adjust current parameter in random direction by 1 step
    def random_direction(self):
        if random.random() < 0.5:
            self.curr_params[self.current] += self.step
            self.bounds_check()
        else:
            self.curr_params[self.current] -= self.step
            self.bounds_check()

    # adjusts parameter in same direction it was adusted previously, by 1 tick
    def same_direction(self):
        temp = self.curr_params[self.current]
        if self.curr_params[self.current] > self.prev_params[self.current]:
            self.curr_params[self.current] += self.step
            self.bounds_check()
        elif self.curr_params[self.current] < self.prev_params[self.current]:
            self.curr_params[self.current] -= self.step
            self.bounds_check()
        else:
            self.random_direction()
        self.current_log_row += f'Adjusting {self.current} from {temp} ' +\
            f'to {self.curr_params[self.current]}. '

    # adjust parameter in opposite direction it was ajusted previously, by 2 ticks
    def opposite_direction(self):
        temp = self.curr_params[self.current]
        if self.curr_params[self.current] > self.prev_params[self.current]:
            self.curr_params[self.current] -= 2 * self.step
            self.bounds_check()
        elif self.curr_params[self.current] < self.prev_params[self.current]:
            self.curr_params[self.current] += 2 * self.step
            self.bounds_check()
        else:
            self.random_direction()
        self.current_log_row += f'Adjusting {self.current} from {temp} ' +\
            f'to {self.curr_params[self.current]}. '

    # toggles speed
    def switch_speed(self):
        if self.curr_params['speed'] == 0:
            self.curr_params['speed'] = 1
            self.current_log_row += 'Switching speed from 0 to 1. '
        elif self.curr_params['speed'] == 1:
            self.curr_params['speed'] = 0
            self.current_log_row += 'Switching speed from 1 to 0. '
    
    # computes value for current inventory.
    # this method actually needs to be moved somewhere else
    @property
    def inventory_value(self):
        b = self.sp['a_y_multiplier']
        x = self.curr_params['a_y']
        t = self.elapsed_seconds % self.sp['move_interval']
        tau = self.sp['move_interval']
        return expm1(b * x * t / tau)

    # prints current profit and params
    def print_status(self, msg=''):
        print(msg, self.config_num, 'profits:', self.agent.model.net_worth,
            'speed', self.curr_params['speed'],
            'a_y:', round(self.curr_params['a_y'], 2),
            'a_z:', round(self.curr_params['a_z'], 2))
    
    # whether or not this tick falls on my turn
    @property
    def my_turn(self):
        m = int(self.elapsed_ticks / self.sp['num_moves']) % self.num_agents
        if m == self.config_num:
            return True
        else:
            return False
    # whether or not this tick falls on the first move of my turn
    @property
    def first_move(self):
        m = float(self.elapsed_ticks / self.sp['num_moves']) % self.num_agents
        if m == self.config_num:
            return True
        else:
            return False

    # called every tick
    # get current net worth and store it in self.current_profits
    def get_profits(self):
        m = self.agent.model
        invoice = m.technology_subscription.invoice_without_deactivating()
        m.cash -= invoice
        m.net_worth -= invoice
        self.current_profits = m.net_worth
        self.current_log_row += f'Invoiced {invoice} for speed tech. '
        
    # called every tick. agent stores its current profit and parameters in redis
    def store_profit_and_params(self):
        self.r.set(f'{self.session_code}_{self.config_num}_profit',
            str(self.current_profits))
        self.r.set(f'{self.session_code}_{self.config_num}_params',
            str(self.curr_params))
    
    # this method gets called when it becomes an agent's turn
    # it updates its params to match the agent with the highest profit
    def update_symmetric(self):
        other_agents = ['0', '1', '2']
        other_agents.remove(str(self.config_num))
        other0_profit = self.r.get(f'{self.session_code}_{other_agents[0]}_profit')
        other1_profit = self.r.get(f'{self.session_code}_{other_agents[1]}_profit')
        if not (other0_profit and other1_profit): # possible on the first turn
            return
        other0_profit = float(other0_profit)
        other1_profit = float(other1_profit)
        if other0_profit > other1_profit:
            del other_agents[1]
        else:
            del other_agents[0]
            other0_profit = other1_profit
        if other0_profit > self.current_profits:
            param_string = self.r.get(f'{self.session_code}_{other_agents[0]}_params')
            self.curr_params = eval(param_string)
    
    # updates A_Y or A_Z given current profits
    def update_params(self):
        self.current_log_row += f'Previous profits: {self.previous_profits}. '
        if self.gel(self.current_profits, self.previous_profits) == 1:
            if self.current != 'speed':
                self.same_direction()
            else:
                self.switch_speed()
        elif self.gel(self.current_profits, self.previous_profits) == -1:
            if self.current != 'speed':
                self.opposite_direction()
            else:
                self.switch_speed()
        else:
            self.get_next_param()
            if self.current != 'speed':
                self.same_direction()
            else:
                self.switch_speed()
        
        # round to 2 decimal places
        self.curr_params[self.current] = round(self.curr_params[self.current], 2)
        # update previous
        self.prev_params = self.curr_params.copy()

    # send message to DynamicAgent model to update params
    def send_message(self, isDynamic):
        if not isDynamic:
            self.elapsed_seconds += 1
            return
        if self.current != 'speed':
            message = {
                'type': 'slider',
                'subsession_id': self.subsession_id,
                'market_id': self.market_id,
                'a_x': self.curr_params['a_x'],
                'a_y': self.inventory_value,
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
        self.elapsed_seconds += 1

    def liquidate(self):
        model = self.agent.model
        mf = model.market_facts
        size = model.inventory.position
        ref = mf['reference_price']
        model.inventory.liquidify(
            ref, 
            discount_rate=mf['tax_rate'])
        cash = model.inventory.cash
        model.cash += cash
        tax_paid = model.inventory.cost
        model.cost += tax_paid
        model.tax_paid += tax_paid
        self.current_log_row += f'Liquidated {size} shares at ' +\
            f'{ref} per share for {cash}' +\
            f', including {tax_paid} tax. '

    def cancel_outstanding_orders(self):
        trader = self.agent.model
        trader_state = trader.trader_role
        message = {
            'type': 'C',
            'subsession_id': self.subsession_id,
            'market_id': self.market_id,
        }
        event = self.agent.event_cls('agent', IncomingMessage(message))
        trader_state.cancel_all_orders(trader, event)
    
    def reset_fundamentals(self):
        random_orders = draw.elo_draw(
            self.sp['move_interval'], self.sp,
            seed=self.sp['random_seed'], config_num=self.config_num)
        event_emitters = [RandomOrderEmitter(source_data=random_orders)]
        if isinstance(self.prev_random_orders, list):
            assert(str(random_orders) == str(self.prev_random_orders))
        else:
            self.prev_random_orders = random_orders
        self.agent.event_emitters = event_emitters
        for em in self.agent.event_emitters:
            em.owner = self.agent
            em.register_events()

    # entry point into the instance, called every tick
    def on_tick(self, is_dynamic):
        self.elapsed_ticks += 1
        self.current_log_row = ''
        # pacemaker agent resets fundamental values
        if not is_dynamic:
            self.reset_fundamentals()
            self.cancel_outstanding_orders()
            return
        #liquidate inventory and cancel all orders at end of session
        self.liquidate()
        self.cancel_outstanding_orders()
        self.get_profits()
        self.current_log_row += f'Current profits: {self.current_profits}. '
        self.current_log_row += f'Current params: {str(self.curr_params)}. '
        # if symmetric mode, store and update to maintain symmetry
        if self.r:
            self.store_profit_and_params()
            if self.elapsed_ticks % 2 == 1:
                self.update_symmetric()
        # if this agent's turn, update their params
        if self.my_turn:
            self.update_params()
        # update arrays for graphing
        self.y_array.append(self.curr_params['a_y'])
        self.z_array.append(self.curr_params['a_z'])
        self.profit_array.append(self.current_profits)
        self.speed_array.append(self.curr_params['speed'])

        if self.elapsed_ticks % 11 == 0:
            df = pd.DataFrame(list(itertools.zip_longest(
                self.y_array, self.z_array, self.speed_array, self.profit_array)),
                columns=['Inventory', 'External', 'Speed', 'Profit'])
            df.to_csv(f'app/data/{self.session_code}_agent{self.config_num}.csv')
        
        with open(self.event_log, 'a+') as f:
            f.write(self.current_log_row + '\n')

        self.previous_profits = self.current_profits
    # initializes agent params at start of sim
    def at_start(self, is_dynamic):
        if self.config_num == 0:
            copyfile('app/parameters.yaml',
                f'app/data/{self.session_code}_parameters.yaml')
        if self.r:
            self.store_profit_and_params()

    # stores csv files at end of sim
    def at_end(self, is_dynamic):
        if is_dynamic:
            self.get_profits()
            self.profit_array.append(self.current_profits)
            self.print_status('FINAL')
            df = pd.DataFrame(list(itertools.zip_longest(
                self.y_array, self.z_array, self.speed_array, self.profit_array)),
                columns=['Inventory', 'External', 'Speed', 'Profit'])
            df.to_csv(f'app/data/{self.session_code}_agent{self.config_num}.csv')


# This class tunes an agent's parameters in order to optimize profits. The
# on_tick method gets called every 2 seconds for each agent.

from high_frequency_trading.hft.incoming_message import IncomingMessage
import random

class AgentSupervisor():
    def __init__(self, account_id, agent):
        self.account_id = account_id
        self.agent = agent
        self.market_id = agent.model.market_id
        self.subsession_id = agent.model.subsession_id
        self.prev_params = {
            'a_x': 0.0,
            'a_y': 1.0,
            'a_z': 0.5,
            'speed': 0,
        }
        self.curr_params = {
            'a_x': 0.0,
            'a_y': 1.0,
            'a_z': 0.5,
            'speed': 0,
        }
        self.current = 'a_y'
        self.current_profits = 0.0
        self.previous_profits = 0.0
        self.tick = 0.04

    def get_profits(self):
        self.current_profits = self.agent.model.net_worth

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
            self.current = 'a_y'

    def update_params(self):
        '''
        A_X is being held constant at 0.
        A_Y and A_Z/W are being manipulated.

        - How should we change speed? It seems obvious that when one agent turns on speed,
        it will get an advantage that goes away when all agents have speed on. I guess we
        can start with it off, then turn it on like normal and see if it ends up turned off
        again.
        - When do we switch the parameters we optimize?
            - After a set number of iterations?
            - When a change in param doesnt result in a large
              change in profit?
        - Should only one agent change at a time?
            - Yes
            - Is previous profit the one from last tick, or the last tick
            that I updated in?

        Strategy:
            if current profit > previous profit:
                keep doing the thing you were doing
            if current profit < previous profit
                do the opposite of the thing you were doing
            if current profit = previous profit:
                the thing you just did had no effect,
                change a different var in a random direction
        '''
        if self.current_profits > self.previous_profits:
            self.same_direction()
        elif self.current_profits < self.previous_profits:
            self.opposite_direction()
        else:
            self.get_next_param()
            # since this param was the same as previously,                     
            # it will automatically do a random direction
            self.same_direction() 
        
        # update previous
        self.previous_profits = self.current_profits
        self.prev_params = self.curr_params.copy()

    def send_message(self):
        message = {
            'type': 'slider',
            'subsession_id': self.subsession_id,
            'market_id': self.market_id,
            'a_x': self.curr_params['a_x'],
            'a_y': self.curr_params['a_y'],
            'a_z': self.curr_params['a_z'],
            'speed': self.curr_params['speed']
        }
        message = IncomingMessage(message) 
        event = self.agent.event_cls('agent', message) 
        self.agent.model.user_slider_change(event)

    def print_status(self):
        print(self.account_id, 'profits:', self.agent.model.net_worth,
            'a_x:', round(self.curr_params['a_x'], 2),
            'a_y:', round(self.curr_params['a_y'], 2),
            'a_z:', round(self.curr_params['a_z'], 2))
    
    def on_tick(self, is_dynamic):
        if not is_dynamic:
            return
        self.get_profits()
        self.update_params()
        self.send_message()
        self.print_status()

    def at_start(self, is_dynamic):
        self.send_message()

    def at_end(self, is_dynamic):
        if is_dynamic:
            self.print_status()

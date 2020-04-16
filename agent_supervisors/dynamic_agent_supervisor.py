from .agent_supervisor import AgentSupervisor
import redis
import random

class DynamicAgentSupervisor(AgentSupervisor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prev_params = { # params before most recent update
            'a_x': 0.0,
            'a_y': self.sp['init_y'],
            'a_z': self.sp['init_z'],
            'speed': self.sp['init_speed'],
        }
        self.step = self.sp['step'] # step size, described above
        if self.sp['symmetric']: # redis connection
            self.r = redis.Redis(
                host='localhost',
                port=6379,
            )
        else:
            self.r = None
        self.current = 'a_y' # current parameter being adjusted
        self.previous_profits = 0.0 # profits before most recent tick


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
    
    def copy_and_update(self, inc):
        prev = self.curr_params[self.current] 
        if inc == True:
            self.curr_params[self.current] += self.step
        else:
            self.curr_params[self.current] -= self.step
        self.bounds_check()
        curr = self.curr_params[self.current]
        return prev, curr

    def _update_params_inner(self, m):
        if m == 0:
            self.current = 'a_y'
            prev, curr = self.copy_and_update(True)
        elif m == 1:
            self.current = 'a_y'
            prev, curr = self.copy_and_update(False)
        elif m == 2:
            self.current = 'a_z'
            prev, curr = self.copy_and_update(True)
        elif m == 3:
            self.current = 'a_z'
            prev, curr = self.copy_and_update(False)
        elif m == 4:
            self.current = 'speed'
            self.curr_params = self.curr_params_copy.copy()
            prev = self.curr_params['speed'] 
            self.curr_params['speed'] = 0
            curr = self.curr_params['speed']
        elif m == 5:
            self.current = 'speed'
            self.curr_params = self.curr_params_copy.copy()
            prev = self.curr_params['speed'] 
            self.curr_params['speed'] = 1
            curr = self.curr_params['speed']
        self.current_log_row += f'Adjusting {self.current} from {prev} ' +\
            f'to {curr}. '
    
    def update_params_explore_all(self):
        m = self.current_submove
        n = self.sp['explore_all_num_submoves']
        assert(m is not None and m >= 0 and m < n)
        self.current_log_row += f'Current submove: {m}.'
        if m == 0:
            self.curr_params_copy = self.curr_params.copy()
            self.submove_profits = {m: {} for m in range(n)}
            self.co = random.sample(list(range(n)), k=n-1)
        else:
            self.submove_profits[self.co[m - 1]]['final'] = self.current_profits
        if m != n:
            self._update_params_inner(self.co[m])
            self.submove_profits[self.co[m]]['initial'] = self.current_profits
        else:
            self.curr_params = self.curr_params_copy.copy()
            best = max(self.submove_profits,
                key=lambda x: self.submove_profits[x]['final'] \
                    - self.submove_profits[x]['initial'])
            self._update_params_inner(self.co[best])             

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
    
    # whether or not this tick falls on the first move of my turn
    @property
    def current_submove(self):
        if not (self.sp['explore_all'] and self.my_turn):
            return None
        return self.elapsed_ticks % self.sp['explore_all_num_submoves']

# entry point into the instance, called every tick
    def on_tick(self, is_dynamic):
        # pacemaker agent resets fundamental values
        if not is_dynamic:
            self.reset_fundamentals()
            return
        #liquidate inventory and cancel all orders at end of session
        self.liquidate()
        if self.elapsed_seconds <= 0:
            self.reset_profits()
            return
        if self.elapsed_seconds % (
                self.sp['num_repeats'] * self.sp['move_interval']) != 0:
            # get profits and other metrics
            self.get_profits()
            self.update_repeat_metrics(avg=False)
            self.reset_profits()
            return

        self.elapsed_ticks += 1
        self.current_log_row = ''
        self.get_profits()
        rp, ro, rr = self.update_repeat_metrics(avg=True)
        # update data and log for this tick
        self.update_arrays(rp, ro, rr)
        self.update_log_row(rp)
        
        # if symmetric mode, store and update to maintain symmetry
        if self.r:
            self.store_profit_and_params()
            if self.elapsed_ticks % 2 == 1:
                self.update_symmetric()
        # if this agent's turn, update their params
        if self.my_turn and self.sp['explore_all']:
            self.update_params_explore_all()
        elif self.my_turn:
                self.update_params()
        
        # write data to files each tick
        self.log_data()
        self.write_logfile()
        
        # reset profits
        self.reset_profits()
    
    # initializes agent params at start of sim
    def at_start(self, is_dynamic):
        super().at_start(is_dynamic)
        if self.r:
            self.store_profit_and_params()


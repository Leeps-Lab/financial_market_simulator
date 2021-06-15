from math import exp
from high_frequency_trading.hft.incoming_message import IncomingMessage
from high_frequency_trading.hft.exchange_message import ResetMessage
from utility import get_interactive_agent_count, get_simulation_parameters
import draw
from discrete_event_emitter import RandomOrderEmitter
from shutil import copyfile
from high_frequency_trading.hft.market_elements.inventory import Inventory
# agent_supervisor.py
# Author: Eli Pandolfo <epandolf@ucsc.edu>

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
        self.prev_random_orders = None
        
        # agent optimization data, changes during simulation
        self.elapsed_seconds = -10
        self.elapsed_ticks = 0 # number of elapsed ticks 
        #print(self.sp)
        try:
            self.curr_params = { # current parameters
                'a_x': 0.0,
                'a_y': self.sp['init_y'] or self.sp['agent_state_configs'][self.config_num][4],
                'a_z': self.sp['init_z'] or self.sp['agent_state_configs'][self.config_num][5],
                'speed': self.sp['init_speed'] or self.sp['agent_state_configs'][self.config_num][2],
            }
        except:
            print('---------------------------------------')
            print("Ignore this warning")
            print('---------------------------------------')
            self.curr_params = { # current parameters
                'a_x': 0.0,
                'a_y': self.sp['init_y'] or self.sp['agent_state_configs'][4],
                'a_z': self.sp['init_z'] or self.sp['agent_state_configs'][5],
                'speed': self.sp['init_speed'] or self.sp['agent_state_configs'][2],
            }
        self.current_profits = 0.0 # current profits
        self.y_array = [] # appended to each tick, used for creating graphs
        self.z_array = []
        self.profit_array = []
        self.speed_array = []
        self.orders_array = []
        self.ref_array = []
        self.event_log = f'app/logs/{self.session_code}_agent{self.config_num}.log'
        self.running_profits = 0
        self.running_orders_executed = 0
        self.running_ref_price = 0
        self.current_log_row = ''

    
    # computes value for current inventory.
    # this method actually needs to be moved somewhere else
    @property
    def inventory_value(self):
        b = self.sp['a_y_multiplier']
        x = self.curr_params['a_y']
        t = self.elapsed_seconds % self.sp['move_interval']
        tau = self.sp['move_interval']
        #return b * exp(-10*(1-x)*(tau / (t + 0.001) - 1))
        return b / ( 1 + exp( 2 * (tau + 4) * (1 - x) - (2 * (t + 2)) ) )

    # prints current profit and params
    def print_status(self, msg=''):
        print(msg, self.config_num, 'profits:', self.agent.model.net_worth,
            'speed', self.curr_params['speed'],
            'a_y:', round(self.curr_params['a_y'], 2),
            'a_z:', round(self.curr_params['a_z'], 2))
    
    # whether or not this tick falls on my turn
    @property
    def my_turn(self):
        mvs = self.sp['num_moves']
        if self.sp['explore_all']:
            mvs *= self.sp['explore_all_num_submoves']
        m = int(self.elapsed_ticks / mvs) % self.num_agents
        if m == self.config_num \
                and self.elapsed_seconds < self.sp['session_duration'] - 10:
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
        
    def update_speed(self):
        trader = self.agent.model
        trader_state = trader.trader_role
        message = {
            'type': 'speed_change',
            'subsession_id': self.subsession_id,
            'market_id': self.market_id,
        }
        s = self.agent.model.technology_subscription
        if self.curr_params['speed'] == 1 and not s.is_active:
            message['value'] = True
            message = IncomingMessage(message)
            event = self.agent.event_cls('agent', message)
            trader_state.speed_technology_change(trader, event)
        elif self.curr_params['speed'] == 0 and s.is_active:
            message['value'] = False
            message = IncomingMessage(message)
            event = self.agent.event_cls('agent', message)
            trader_state.speed_technology_change(trader, event)

    # send message to DynamicAgent model to update params
    def send_message(self, is_dynamic):
        self.elapsed_seconds += 1
        if self.elapsed_seconds % self.sp['move_interval'] == 0:
            self.on_tick(is_dynamic)
        if not is_dynamic:
            return
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
        trader = self.agent.model
        trader.user_slider_change(event)
        self.update_speed()
       

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
        ticker = model.inventory.ticker
        model.inventory = Inventory(ticker=ticker) # reset inventory so that tax paid and cost dont translate over to the next tick
        self.current_log_row += f'Liquidated {size} shares at ' +\
            f'{ref} per share for {cash}' +\
            f', including {tax_paid} tax. '

    
    # only gets called by pacemaker agent
    def reset_exchange(self): 
        msg = ResetMessage.create(
            'reset_exchange', exchange_host='', 
            exchange_port=0, delay=0.1, 
            event_code='S', timestamp=0, subsession_id=0)
        if self.agent.exchange_connection is not None:
            self.agent.exchange_connection.sendMessage(msg.translate(), msg.delay)
        else:
            self.agent.outgoing_msg.append((msg.translate(), msg.delay))
    

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

    def reset_profits(self):
        self.agent.model.cash = 0
        self.agent.model.net_worth = 0
        self.agent.model.cost = 0
        self.agent.model.tax_paid = 0
        self.current_profits = 0

    def update_repeat_metrics(self, avg=False): 
        self.running_profits += self.current_profits
        self.running_orders_executed += self.agent.model.orders_executed
        self.running_ref_price += self.agent.model.market_facts['reference_price']
        if avg == False:
            rp = None
            ro = None
            rr = None
        else:
            rp = self.running_profits / self.sp['num_repeats']
            ro = self.running_orders_executed / self.sp['num_repeats']
            rr = self.running_ref_price / self.sp['num_repeats']
            self.running_profits = 0
            self.running_orders_executed = 0
            self.running_ref_price = 0
        self.agent.model.orders_executed = 0
        roundif = lambda x: round(x, 2) if x is not None else None
        return roundif(rp), roundif(ro), roundif(rr)
    
    def update_arrays(self, profit, orders, ref):
        self.profit_array.append(profit)
        self.orders_array.append(orders)
        self.ref_array.append(ref)
        self.y_array.append(self.curr_params['a_y'])
        self.z_array.append(self.curr_params['a_z'])
        self.speed_array.append(self.curr_params['speed'])
   
    def update_log_row(self, profit): 
        self.current_log_row += f'Current profits: {profit}. '
        self.current_log_row += f'Current params: {str(self.curr_params)}. '

    def log_data(self):
        i = self.elapsed_ticks - 1
        slist = [self.y_array[i], self.z_array[i],
                self.speed_array[i], self.profit_array[i],
                self.orders_array[i], self.ref_array[i]]
        slist = [str(round(e, 2)) for e in slist]
        s = ','.join(slist) + '\n'
        with open(f'app/data/{self.session_code}_agent{self.config_num}.csv', 'a') as f:
            f.write(s)
        
    def write_logfile(self): 
        with open(self.event_log, 'a+') as f:
            f.write(self.current_log_row + '\n')

    def cancel_outstanding_orders(self):
        trader = self.agent.model
        trader.reset_orderstore()
        #trader_state = trader.trader_role
        #message = {
        #    'type': 'X',
        #    'subsession_id': 0,
        #    'market_id': 0,
        #}
        #event = self.agent.event_cls('agent', IncomingMessage(message))
        #trader_state.cancel_all_orders(trader, event)
        #while event.exchange_msgs:
        #    msg = event.exchange_msgs.pop()
        #    msg.data['shares'] = 0
        #    msg.data['delay'] = 0
        #    if self.agent.exchange_connection is not None:
        #        self.agent.exchange_connection.sendMessage(msg.translate(), msg.delay)
        #    else:
        #        self.agent.outgoing_msg.append((msg.translate(), msg.delay))
  
    def reset_state(self):
        self.change_state('out')
        self.change_state('automated')
        self.update_speed()

    def change_state(self, new_state):
        message = {
            'type': 'role_change',
            'subsession_id': self.subsession_id,
            'market_id': self.market_id,
            'state': new_state,
        }
        message = IncomingMessage(message) 
        event = self.agent.event_cls('agent', message) 
        trader = self.agent.model
        trader_role = trader.trader_role
        trader_role.state_change(trader, event)
        trader.state_change(event)
        
    def on_tick(self):
        raise NotImplementedError()

    # initializes agent params at start of sim
    def at_start(self, is_dynamic):
        if self.config_num == 0:
            copyfile('app/parameters.yaml',
                f'app/data/{self.session_code}_parameters.yaml')
        columns = ['Inventory', 'External', 'Speed', 'Profit', 'Orders Executed', 'Reference Price']
        s = ','.join(columns) + '\n'
        with open(f'app/data/{self.session_code}_agent{self.config_num}.csv', 'w') as f:
            f.write(s)

    # stores csv files at end of sim
    def at_end(self, is_dynamic):
        if is_dynamic:
            self.print_status('FINAL')


from agent_supervisor import AgentSupervisor

class DynamicAgentSupervisor(AgentSupervisor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running_profits = 0
        self.running_orders_executed = 0
        self.running_ref_price = 0


    def update_params_from_grid(self):
        y, z, speed = self.get_current_grid_params()
        self.prev_params = self.curr_params.copy()
        self.curr_params['a_y'] = y
        self.curr_params['a_z'] = z
        self.curr_params['speed'] = speed

    def get_current_grid_params(self):
        flatlist = []
        for y in self.sp['ys']:
            for z in self.sp['zs']:
                for speed in self.sp['speeds']:
                    flatlist.append((y, z, speed))
        if self.elapsed_ticks < 0:
            return flatlist[0]
        return flatlist[self.elapsed_ticks]
    
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
    # entry point into the instance, called every tick
    def on_tick(self, is_dynamic):
        # pacemaker agent resets fundamental values
        if not is_dynamic:
            self.reset_fundamentals()
            return
        #print('code', self.session_code, 'agent', self.config_num, 'elapsed_seconds', self.elapsed_seconds, 'elapsed_ticks', self.elapsed_ticks)
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
        self.current_log_row += f'Current profits: {rp}. '
        self.current_log_row += f'Current params: {str(self.curr_params)}. '
        self.orders_array.append(ro)
        self.ref_array.append(rr)
        # update arrays for graphing
        self.y_array.append(self.curr_params['a_y'])
        self.z_array.append(self.curr_params['a_z'])
        self.profit_array.append(rp)
        self.speed_array.append(self.curr_params['speed'])
        
        # if symmetric mode, store and update to maintain symmetry
        if self.r:
            self.store_profit_and_params()
            if self.elapsed_ticks % 2 == 1:
                self.update_symmetric()
        # if this agent's turn, update their params
        if self.my_turn and self.sp['explore_all']:
            self.update_params_explore_all()
        elif self.my_turn:
            if self.sp['grid_search']:
                self.update_params_from_grid()
            else:
                self.update_params()
        elif self.sp['grid_search_symmetric']:
            self.update_params_from_grid()

        if self.elapsed_ticks % 1 == 0:
            df = pd.DataFrame(list(itertools.zip_longest(
                self.y_array, self.z_array, self.speed_array, self.profit_array, self.orders_array, self.ref_array)),
                columns=['Inventory', 'External', 'Speed', 'Profit', 'Orders Executed', 'Reference Price'])
            df.to_csv(f'app/data/{self.session_code}_agent{self.config_num}.csv')
        
        with open(self.event_log, 'a+') as f:
            f.write(self.current_log_row + '\n')

        self.previous_profits = self.current_profits
        if self.sp['grid_search']:
            self.reset_profits()
    # initializes agent params at start of sim
    def at_start(self, is_dynamic):
        super().at_start(is_dynamic)
        if self.sp['grid_search'] and (self.config_num == 0 \
            or self.sp['grid_search_symmetric']):
            self.update_params_from_grid()

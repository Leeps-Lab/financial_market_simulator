from .agent_supervisor import AgentSupervisor

class GridSearchAgentSupervisor(AgentSupervisor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
    
    # entry point into the instance, called every tick
    def on_tick(self, is_dynamic):
        # pacemaker agent resets fundamental values
        if not is_dynamic:
            self.reset_fundamentals()
            return
        
        #print('code', self.session_code, 'agent', self.config_num, 'elapsed_seconds', self.elapsed_seconds, 'elapsed_ticks', self.elapsed_ticks)
        
        #liquidate inventory and cancel all orders at end of session
        self.liquidate()
        self.cancel_outstanding_orders()
        
        #print('elapsed_seconds', self.elapsed_seconds)
        if self.elapsed_seconds <= 0:
            self.reset_profits()
            return
        
        # store data for averaging then return
        if self.elapsed_seconds % (
                self.sp['num_repeats'] * self.sp['move_interval']) != 0:
            self.get_profits()
            self.update_repeat_metrics(avg=False)
            self.reset_profits()
            return
        
        # update elapsed ticks
        self.elapsed_ticks += 1
        self.current_log_row = ''
        #print('elapsed_ticks', self.elapsed_ticks)

        # get profits
        self.get_profits()
        rp, ro, rr = self.update_repeat_metrics(avg=True)
        
        # update data and log for this tick
        self.update_arrays(rp, ro, rr)
        self.update_log_row(rp)

        #print('size of y array:', len(self.y_array))

        # if this agent's turn, update its parameters
        if self.my_turn:
            self.update_params_from_grid()

        # write data to files each tick
        self.log_data()
        self.write_logfile()
        
        # reset profits
        self.reset_profits()
    
    # initializes agent params at start of sim
    def at_start(self, is_dynamic):
        super().at_start(is_dynamic)
        if self.sp['grid_search'] and (self.config_num == 0 \
            or self.sp['grid_search_symmetric']):
            self.update_params_from_grid()

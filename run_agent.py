import configargparse
from twisted.internet import reactor, task
import draw
import settings
from discrete_event_emitter import *
from agents.pacemaker_agent import PaceMakerAgent
from agents.dynamic_agent import DynamicAgent 
from agent_supervisors.grid_search_agent_supervisor import GridSearchAgentSupervisor
from agent_supervisors.dynamic_agent_supervisor import DynamicAgentSupervisor
from protocols.ouch_trade_client_protocol import OUCHClientFactory
from protocols.json_line_protocol import JSONLineClientFactory
from utility import (
    random_chars, generate_account_id, get_simulation_parameters)
import logging as log


p = configargparse.getArgParser()
p.add('--session_duration', required=True, type=int, 
    help='required: session duration in seconds')
p.add('--debug', action='store_true')
p.add('--session_code', default=random_chars(8))
p.add('--exchange_host', default='127.0.0.1', help='Address of matching engine')
p.add('--exchange_ouch_port', required=True, type=int)
p.add('--exchange_json_port', type=int)
p.add('--external_exchange_host')
p.add('--external_exchange_json_port', type=int)
p.add('--agent_type', choices=['rabbit', 'elo'], required=True)
p.add('--config_num', default=0, type=int, help='The configuration number, \
       index in the list of discrete event configurations')
p.add('--random_seed', type=int)
options, args = p.parse_known_args()

def at_end():
    pass
        
def main(account_id):
    agent_type = options.agent_type
    session_duration = options.session_duration
    conf = get_simulation_parameters()
    agent_parameters = {'market_format': conf['focal_market_format']}
    if agent_type == 'rabbit':
        random_orders = draw.elo_draw(
            conf['move_interval'], conf,
            seed=options.random_seed, config_num=options.config_num)
        # Useful for testing to ensure pegged orders get executed correctly
       # if options.config_num == 1: #external
       #     random_orders = [
       #         ['0.2', '950000', '910000', 'B', '15', 'False'],
       #         ['0.2', '950000', '1000000', 'S', '15', 'False'],
       #         ['2.4', '950000', '940000', 'B', '10', 'False'],
       #         ['2.4', '950000', '960000', 'S', '10', 'False'],
       #     ]
       # else: # focal
       #     random_orders = [
       #         ['0.2', '950000', '910000', 'B', '10', 'False'],
       #         ['0.2', '950000', '1000000', 'S', '10', 'False'],
       #         ['0.3', '950000', '930000', 'B', '10', 'True'],
       #         ['0.4', '950000', '970000', 'S', '10', 'False'],
       #     ]
        #print(random_orders)
        event_emitters = [RandomOrderEmitter(source_data=random_orders), ]
        agent_cls = PaceMakerAgent

    elif agent_type == 'elo':
        events = utility.transform_agent_events_array(conf['agent_state_configs'], options.config_num)
        event_emitters = [ELOSliderChangeEmitter(source_data=events['slider']), 
            ELOSpeedChangeEmitter(source_data=events['speed'])]
        agent_cls = DynamicAgent
        agent_parameters.update(utility.get_elo_agent_parameters())
 
    agent = agent_cls(options.session_code, options.exchange_host, 
        options.exchange_ouch_port, event_emitters=event_emitters, 
        account_id=account_id, config_num=options.config_num, **agent_parameters)

    reactor.connectTCP(options.exchange_host, options.exchange_ouch_port,
        OUCHClientFactory(agent))
   
    if options.exchange_json_port:
        reactor.connectTCP(options.exchange_host, options.exchange_json_port,
            JSONLineClientFactory('focal', agent))
    
    if options.external_exchange_host:
        reactor.connectTCP(options.external_exchange_host, 
            options.external_exchange_json_port,  
            JSONLineClientFactory('external', agent))

    agent.ready()

    d = task.deferLater(reactor, session_duration, agent.close_session)
    d.addCallback(lambda _ : reactor.stop())
    
    ############################################################################
    # This is code for optimizing agents' slider params during simulations.
    # If you want to run simulations normally, MAKE SURE THIS CODE DOES NOT RUN
    if conf['grid_search']:
        supervisor = GridSearchAgentSupervisor(options.session_code, options.config_num, agent)
    else:
        supervisor = DynamicAgentSupervisor(options.session_code, options.config_num, agent)
    supervisor.at_start(isinstance(agent, DynamicAgent))
    d.addCallback(lambda _ : supervisor.at_end(isinstance(agent, DynamicAgent)))
    looper = task.LoopingCall(supervisor.send_message, isinstance(agent, DynamicAgent))
    looper.clock = reactor
    looper.start(1.0, now=True)
    d.addCallback(lambda _ : looper.stop())
    ############################################################################
    
    reactor.run()


if __name__ == '__main__':
    account_id = generate_account_id()
    log.basicConfig(
        level=log.ERROR, 
        #filename=settings.logs_dir + 'session_%s_trader_%s.log' % (
        #options.session_code, account_id),
        format = "[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s",
        datefmt = '%H:%M:%S')
    if options.random_seed:
        log.debug('%s agent started using random seed %d', options.agent_type, options.random_seed)
    main(account_id)
    

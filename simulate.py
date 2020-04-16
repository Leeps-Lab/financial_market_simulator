# elo simulation
import sys
import subprocess
import shlex
import settings
import configargparse
from utility import (
    random_chars, get_interactive_agent_count, 
    get_simulation_parameters, copy_params_to_logs)
import numpy as np
from db.db import session_results_ready
from db.db_commands import export_session
import logging
from contextlib import closing
import socket
from time import sleep
import atexit
import random

log = logging.getLogger(__name__)

p = configargparse.getArgParser()
p.add('--debug', action='store_true')
p.add('--session_code', default=random_chars(8), type=str)
p.add('--note', type=str)
options, args = p.parse_known_args()

# gets a list of `num_ports` of available ports between 9000 and 10000
def get_available_ports(num_ports):
    ports = []
    ports_to_try = list(range(9000, 10000))
    random.shuffle(ports_to_try)
    for port in ports_to_try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            res = sock.connect_ex(('localhost', port))
            if res != 0:
                ports.append(port)
                if len(ports) == num_ports:
                    return ports
    raise RuntimeError('no available ports')

def start_exchange(port, exchange_format, fba_interval, iex_delay):
    cmd = [
        sys.executable,
        'exchange_server/run_exchange_server.py',
        '--host', 'localhost',
        '--port', str(port),
        '--mechanism', exchange_format.lower(),
    ]
    if exchange_format.lower() == 'fba':
        cmd.extend([
            '--interval', str(fba_interval),
        ])
    # delay in seconds. defaults to 350us, or 0.035s
    if exchange_format.lower() == 'iex':
        cmd.extend([
            '--delay', str(iex_delay),
        ])
    if options.debug:
        cmd.append('--debug')
    proc = subprocess.Popen(cmd)
    # make sure this process is eventually killed
    atexit.register(proc.terminate)
    return proc

def run_elo_simulation(session_code):
    """
    given a session code
    runs a a simulation of ELO type
    blocks until the all agents write a market_end event
    to db otherwise timeouts
    returns session data as two csv formatted files
    one for markets, one for agents
    """
    logging.basicConfig(
        level=logging.CRITICAL,
        filename=settings.logs_dir + 'session_%s_manager.log' % (session_code),
        format="[%(asctime)s.%(msecs)03d] %(levelname)s \
        [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt='%H:%M:%S')
    # commands to run each process
    # one proxy per exchange
    # one pacemaker agent per proxy

    # start exchanges
    params = get_simulation_parameters()
    focal_exchange_port, external_exchange_port = get_available_ports(2)
    print('focal exchange port:', focal_exchange_port)
    print('external exchange port:', external_exchange_port)
    focal_exchange_proc = start_exchange(
        focal_exchange_port,
        params['focal_market_format'],
        params['focal_market_fba_interval'],
        params['iex_delay'],
    )
    external_exchange_proc = start_exchange(
        external_exchange_port,
        params['external_market_format'],
        params['external_market_fba_interval'],
        params['iex_delay'],
    )
    # sleep for a second after making the exchanges to ensure they don't buffer messages
    # when the experiment starts. not sure this is necessary, but just being safe
    sleep(2)

    p = settings.ports # we overwrite this
    p1, p2, p3, p4 = get_available_ports(4)
    print('proxy ports:', p1, p2, p3, p4)
    p['focal_proxy_ouch_port'] = p1
    p['focal_proxy_json_port'] = p2
    p['external_proxy_ouch_port'] = p3
    p['external_proxy_json_port'] = p4

    session_dur = params['session_duration']
    if params['random_seed']:
        random_seed = int(params['random_seed'])
    else:
        random_seed = np.random.randint(0, 99)

    # (cmd, process_name)
    focal_proxy = """ run_proxy.py --ouch_port {0} --json_port {1}
                      --session_code {2} --exchange_host {3} --exchange_port {4} 
                      --session_duration {5} --tag focal""".format(
                p['focal_proxy_ouch_port'], 
                p['focal_proxy_json_port'],
                session_code, 
                settings.focal_exchange_host,
                focal_exchange_port, 
                session_dur), 'focal_proxy'
    external_proxy = """run_proxy.py --ouch_port {0} --json_port {1}
                        --session_code {2} --exchange_host {3} --exchange_port {4} 
                        --session_duration {5} --tag external""".format(
                p['external_proxy_ouch_port'], 
                p['external_proxy_json_port'], 
                session_code, 
                settings.external_exchange_host,
                external_exchange_port, 
                session_dur), 'external_proxy'

    rabbit_agent_focal = """run_agent.py --session_duration {0} --exchange_ouch_port {1}
                            --session_code {2} --agent_type rabbit --config_num {3} 
                            --random_seed {4}""".format(
                    session_dur, 
                    p['focal_proxy_ouch_port'],
                    session_code, 
                    0, 
                    random_seed), 'rabbit_agent_focal'
    rabbit_agent_external = """run_agent.py --session_duration {0} --exchange_ouch_port {1}
                               --session_code {2} --agent_type rabbit --config_num {3} 
                               --random_seed {4}""".format(
                    session_dur, 
                    p['external_proxy_ouch_port'],
                    session_code, 
                    1, 
                    random_seed), 'rabbit_agent_external'

    interactive_agents = []
    for i in range(get_interactive_agent_count(params['agent_state_configs'])):
        agent_i = """run_agent.py --session_duration {0} --exchange_ouch_port {1} \
            --exchange_json_port {2}  --external_exchange_host 127.0.0.1 \
            --external_exchange_json_port {3} --session_code {4} \
            --agent_type elo --config_num {5} --debug""".format(
                session_dur, 
                p['focal_proxy_ouch_port'],
                p['focal_proxy_json_port'], 
                p['external_proxy_json_port'],
                session_code, 
                i), 'dynamic_agent_{0}'.format(i)
        interactive_agents.append(agent_i)

    processes = {}
    for pair in [focal_proxy, external_proxy, rabbit_agent_focal,
                 rabbit_agent_external] + interactive_agents:
        cmd, process_tag = pair[0], pair[1]
        if options.debug:
            cmd += ' --debug'
        cmd = sys.executable + ' ' + cmd
        processes[process_tag] = subprocess.Popen(shlex.split(cmd))
    exit_codes = [p.wait() for p in processes.values()]
    # once all other subprocesses have finished, kill exchanges
    focal_exchange_proc.terminate()
    external_exchange_proc.terminate()
    if sum(exit_codes) == 0 and session_results_ready(session_code):
        export_session(session_code)
        copy_params_to_logs(session_code)

    log.info('session %s complete!' % session_code)


if __name__ == '__main__':
    run_elo_simulation(options.session_code)

import os

MIN_BID = 0
MAX_ASK = 2147483647

default_simulation_parameters = {
    # configs for elo simulation
    'session_duration': 10,
    'initial_price': 1000000,
    'fundamental_value_noise_mean': 0,
    'fundamental_value_noise_std': 20000,
    'exogenous_order_price_noise_mean': 0,
    'exogenous_order_price_noise_std': 12000,
    'bid_ask_offset': 1000000,
    'lambdaJ': 0.5,
    'lambdaI': 1,
    'time_in_force': 5,
    'tax_rate': 0.1,
    'k_reference_price': 0.01,
    'k_signed_volume': 0.5,
    'read_fundamental_values_from_array': False,
    'a_x_multiplier': 1,   # a_x <-> signed volume
    'a_y_multiplier': 1,   # a_y <-> inventory
    'speed_unit_cost': 10000,  # per second
    'focal_market_format': 'CDA',
    'external_market_format': 'CDA',
    'focal_market_fba_interval': 3,
    'external_market_fba_interval': 3,
    'random_seed': None,
    'fundamental_values': [],
    'agent_state_configs': [],
    'init_y': 0.5,
    'init_z': 0.5,
    'step': 0.05,
    'symmetric': False,
    'num_moves': 8,
    'move_interval': 3.0,
    'explore_all': False,
    'explore_all_num_submoves': 6,
}

logs_dir = './app/logs/'
results_export_path = './app/data/{session_id}_{record_class}_accessed_{timestamp}.csv'
params_export_path = './app/data/{session_id}_params_{timestamp}.yaml'

custom_config_path = './app/parameters.yaml'

focal_exchange_host = os.getenv('FOCAL_EXCHANGE_HOST', 'localhost')
external_exchange_host = os.getenv('EXTERNAL_EXCHANGE_HOST', 'localhost')

ports = {
    'focal_proxy_ouch_port': 9201,
    'focal_proxy_json_port': 9202,
    'external_proxy_ouch_port': 9301,
    'external_proxy_json_port': 9302,
}

initial_trader_market_view = {
    'best_bid': MIN_BID,
    'volume_at_best_bid': 0,
    'next_bid': MIN_BID,
    'best_offer': MAX_ASK,
    'volume_at_best_offer': 0,
    'next_offer': MAX_ASK,
    'signed_volume': 0,
    'e_best_bid': MIN_BID,
    'e_best_offer': MAX_ASK,
    'e_signed_volume': 0,
    'tax_rate': default_simulation_parameters['tax_rate'],
    'reference_price': default_simulation_parameters['initial_price']
}

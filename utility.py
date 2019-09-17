from high_frequency_trading.hft.incoming_message import IncomingWSMessage, IncomingMessage
from twisted.internet import reactor, error
from random import randint, choice
from shutil import copyfile
import subprocess
import shlex
import settings
import string
import csv
import logging
import datetime
import yaml

log = logging.getLogger(__name__)

SESSION_CODE_CHARSET = string.ascii_lowercase + string.digits  # otree <3


def get_simulation_parameters():
    custom_parameters = read_yaml(settings.custom_config_path)
    merged_parameters = settings.default_simulation_parameters.copy()
    if custom_parameters:
        for k, v in custom_parameters.items():
            if k in merged_parameters:
                merged_parameters[k] = v
    return merged_parameters


def get_elo_agent_parameters(
        parameter_names=('a_x_multiplier', 'a_y_multiplier', 'speed_unit_cost')
    ):
    all_parameters = get_simulation_parameters()
    return {k: all_parameters[k] for k in parameter_names}


def copy_params_to_logs(session_id: str):
    path = settings.params_export_path.format(
        session_id=session_id, 
        params=get_simulation_parameters(),
        timestamp=datetime.datetime.now(),
    )
    copyfile(settings.custom_config_path, path)


def get_interactive_agent_count(agent_events):
    return max([int(row[1]) for row in agent_events])


def get_traders_initial_market_view():
    result = settings.initial_trader_market_view
    for k, v in get_simulation_parameters().items():
        if k in result:
            result[k] = v
    log.info('initial market view of trader: %s' % ' '.join(
                '{0}:{1}'.format(k, v) for k, v in result.items()))
    return result


def dict_stringify(dict_to_str):
    return '%s' % ' '.join('{0}:{1}'.format(k, v) for k, v in dict_to_str.items())


def generate_account_id(size=4):
    return ''.join(choice(string.ascii_uppercase) for i in range(size))


def random_chars(num_chars):
    return ''.join(choice(SESSION_CODE_CHARSET) for _ in range(num_chars))


def transform_incoming_message(source, message, external_market_state=None):
    """ this handles key mismatches in messages
        between the otree app and simulator"""
    def transform_external_proxy_msg(message):
        """
        traders in elo environment treat one of the
        markets as external, format the message so
        correct handlers are activated on trader model
        """
        if message['type'] == 'reference_price_change':
            message['type'] = 'external_reference_price'
            return message
        if not external_market_state:
            raise Exception('external_market_state is not set.')
        if message['type'] == 'bbo':
            message['e_best_bid'] = message['best_bid']
            message['e_best_offer'] = message['best_offer']
            external_market_state['e_best_bid'] = message['best_bid']
            external_market_state['e_best_offer'] = message['best_offer']
            message['e_signed_volume'] = external_market_state['e_signed_volume']
        if message['type'] == 'post_batch':
            message['e_best_bid'] = message['best_bid']
            message['e_best_offer'] = message['best_offer']
            external_market_state['e_best_bid'] = message['best_bid']
            external_market_state['e_best_offer'] = message['best_offer']
            message['e_signed_volume'] = external_market_state['e_signed_volume']
        if message['type'] == 'signed_volume':
            message['e_signed_volume'] = message['signed_volume']
            message['e_best_bid'] = external_market_state['e_best_bid']
            message['e_best_offer'] = external_market_state['e_best_offer']
            external_market_state['e_signed_volume'] = message['signed_volume']
        message['type'] = 'external_feed_change'
        return message
    message['subsession_id'] = 0
    message['market_id'] = 0
    if message['type'] == 'reference_price':
        message['type'] = 'reference_price_change'
    if source == 'external':
        message = transform_external_proxy_msg(message)
    if message['type'] == 'bbo':
        message['type'] = 'bbo_change'
    if message['type'] == 'signed_volume':
        message['type'] = 'signed_volume_change'
    if 'technology_on' in message:
        message['value'] = message['technology_on']
    return message


def extract_firm_from_message(message):
    if hasattr(message, 'order_token'):
        return message.order_token[:4]

def transform_agent_events_array(agent_events, config_number):
    """transform an array of agent events from paramaters.yaml.
    turn it into a usable set of speed and slider events for a specific player"""
    input_list = {'speed': [], 'slider': []}
    for row in agent_events:
        arrival_time, agent_num, tech_subsc, a_x, a_y, a_z = row
        agent_num = int(agent_num)
        if agent_num-1 == config_number:
            speed_row = (arrival_time, tech_subsc)
            slider_row = (arrival_time, a_x, a_y, a_z)
            input_list['speed'].append(speed_row)
            input_list['slider'].append(slider_row)
    return input_list


def get_mock_market_msg(market_facts: dict, msg_type: str):
    mock_msg = market_facts
    mock_msg['type'] = msg_type
    mock_msg['subsession_id'] = 0
    mock_msg['market_id'] = 0
    msg = IncomingMessage(mock_msg)
    return msg


class MockWSMessage(IncomingWSMessage):

    sanitizer_cls = None

    def translate(self, message):
        return message


incoming_message_defaults = {'subsession_id': 0,  'market_id': 0, 'player_id': 0}


def read_yaml(path: str):
    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    return config

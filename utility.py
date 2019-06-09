from high_frequency_trading.hft.incoming_message import IncomingWSMessage
from random import randint, choice
import string


SESSION_CODE_CHARSET = string.ascii_lowercase + string.digits  # otree <3

def random_chars(num_chars):
    return ''.join(choice(SESSION_CODE_CHARSET) for _ in range(num_chars))    

def transform_incoming_message(source, message):
    if source == 'external' and message['type'] == 'bbo':
        message['type'] = 'external_feed_change'
        message['e_best_bid'] = message['best_bid']   
        message['e_best_offer'] = message['best_offer']
    if source == 'external' and message['type'] == 'signed_volume':
        message['type'] = 'external_feed_change'
        message['e_signed_volume'] = message['signed_volume']
    message['subsession_id'] = 0
    return message


def generate_random_test_orders(num_orders, session_duration):
    return iter(
            {'arrival_time': randint(10, 60) / 10,
            'price': randint(100, 110),
            'buy_sell_indicator': choice(['B', 'S']),
            'time_in_force': choice([10, 15, 20])
            } for o in range(50))

def extract_firm_from_message(message):
    if hasattr(message, 'order_token'):
        return message.order_token[:4]

class MockWSMessage(IncomingWSMessage):

    sanitizer_cls = None

    def translate(self, message):
        return message


incoming_message_defaults = {
    'subsession_id': 0,  'market_id': 0, 'player_id': 0}


fields_to_freeze =  {
    'trader_model': {
        'events_to_capture': ('speed_change', 'role_change', 'slider', 
                'market_start', 'market_end', 'A', 'U', 'C', 'E'),
        'properties_to_serialize': (
            'subsession_id', 'market_id', 'id_in_market', 'player_id', 'delay', 
            'staged_bid', 'staged_offer', 'net_worth', 'cash', 'cost', 'tax_paid',
            'speed_cost', 'implied_bid', 'implied_offer', 'best_bid_except_me',
            'best_offer_except_me'),
        'subproperties_to_serialize': {
            'trader_role': ('trader_model_name', ),
            'sliders': ('slider_a_x', 'slider_a_y', 'slider_a_z'),
            'orderstore': ('inventory', 'bid', 'offer', 'firm'),
            'inventory': ('position', ),
            'market_facts': (
                'reference_price', 'best_bid', 'best_offer', 
                'signed_volume', 'e_best_bid', 'e_best_offer', 'e_signed_volume',
                'next_bid', 'next_offer', 'volume_at_best_bid', 'volume_at_best_offer')
        }
    },
    'market': {
        'events_to_capture': ('Q', 'E', 'market_start', 'market_end',
            'external_feed'), 
        'properties_to_serialize': ('subsession_id', 'market_id'),
        'subproperties_to_serialize': {
            'bbo': ('best_bid', 'best_offer', 'next_bid', 'next_offer', 
                    'volume_at_best_bid', 'volume_at_best_offer'),
            'external_feed': ('e_best_bid', 'e_best_offer', 'e_signed_volume'),
            'signed_volume': ('signed_volume', ),
            'reference_price': ('reference_price', ),
        }
    }
}



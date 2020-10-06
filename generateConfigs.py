import os
import pandas as pd
import numpy as np 
import utility
from draw import elo_draw
from high_frequency_trading.session_config.createExternalFeedFromExternalInvestors import main

#This script will generate the investors arrivals and external feed configurations.
#Set the desired parameters in parameters.yaml found in app/parameters.yaml
#Invoke this script by going into a virtual environment then doing python generateConfigs.py
#This will put the conig files in the session_config folder

#Parameters
period_length = 240
investor_arrivals_file_name = 'investor_arrivals_focal.csv'
external_feed_file_name = 'external_feed_config.csv'

#Create investors arrival file
print('Generating investors arrival file')
d = elo_draw(period_length, utility.get_simulation_parameters(), config_num=0)

df = pd.DataFrame(d, columns=['arrival_time', 'fundamental_value', 'price', 'buy_sell_indicator', 'time_in_force', 'pegged_state'])
df['market_id_in_subsession'] = 0
df = df[['arrival_time', 'market_id_in_subsession', 'price', 'buy_sell_indicator', 'time_in_force']]
df.to_csv(investor_arrivals_file_name, index=False)

#Move investors arrival file to session_config folder
os.rename('/home/leeps/financial_market_simulatororig/' + investor_arrivals_file_name, '/home/leeps/financial_market_simulatororig/session_config/' + investor_arrivals_file_name)
print('Successfully created investors arrivals file')

#Create external feed file to session_config folder
print('Generating external feed file')
main('/home/leeps/financial_market_simulatororig/session_config/' + investor_arrivals_file_name, external_feed_file_name)

#Replace any N/A values
dataframe = pd.read_csv(external_feed_file_name)
dataframe['e_signed_volume'] = dataframe['e_signed_volume'].replace(np.nan, 0)
dataframe.to_csv(external_feed_file_name, index=False)

#Move external feed file to config folder
os.rename('/home/leeps/financial_market_simulatororig/' + external_feed_file_name, '/home/leeps/financial_market_simulatororig/session_config/' + external_feed_file_name)
print('Successfully generated external feed file.')



import os
import pandas as pd
import numpy as np 
import utility
from draw import elo_draw
from high_frequency_trading.session_config.createExternalFeedFromExternalInvestors import main
from datetime import datetime
from shutil import copyfile
import smtplib, ssl

#This script will generate the investors arrivals and external feed configurations.
#Set the desired parameters in parameters.yaml found in app/parameters.yaml
#Invoke this script by going into a virtual environment then doing python generateConfigs.py
#This will put the conig files in the session_config folder

#Grab config parameters
conf = utility.get_simulation_parameters()

#Parameters
investor_arrivals_file_name_base = 'investor_focal'
external_arrivals_file_name_base = 'investor_external'
external_feed_file_name_base = 'external_feed'

#Email to receive notification that script is done
receiver_email = 'kvargha@ucsc.edu'

#Grab current time and create folder with time stamp
now = datetime.now()

# dd-mm-YY_H:M
dt_string = now.strftime('%m-%d-%Y_%H:%M:%S')
current_dir = os.getcwd() + '/session_config/' + dt_string + '_'  + conf['suffix'] + '/'
os.mkdir(current_dir)

#Copy parameters file into folder
copyfile(os.getcwd() + '/app/parameters.yaml', current_dir + 'parameters.yaml')

#Create number config files depending on num_periods parameter
for i in range(conf['num_periods']):
    file_num = '_T' + str(i + 1) + '_'

    #File name for each period
    investor_arrivals_file_name = investor_arrivals_file_name_base + file_num + dt_string + '_' + conf['suffix'] + '.csv' 
    external_arrivals_file_name = external_arrivals_file_name_base + file_num + dt_string + '_' + conf['suffix'] + '.csv' 
    external_feed_file_name = external_feed_file_name_base + file_num + dt_string + '_' + conf['suffix'] +'.csv'

    #Create investors arrival file
    print('Generating investors arrival files ' + str(i + 1))
    d = elo_draw(conf, np.random.randint(0, high=2 ** 8), config_num=0)

    df = pd.DataFrame(d, columns=['arrival_time', 'fundamental_value', 'price', 'buy_sell_indicator', 'time_in_force', 'pegged_state'])
    df['market_id_in_subsession'] = 0
    df = df[['arrival_time', 'market_id_in_subsession', 'price', 'buy_sell_indicator', 'time_in_force']]
    df.to_csv(investor_arrivals_file_name, index=False)

    #Move investors arrival file to session_config folder
    os.rename(os.getcwd() + '/' + investor_arrivals_file_name, current_dir + investor_arrivals_file_name)
    print('Successfully created investors arrivals file ' + str(i + 1))

    #Create external arrivals file
    d = elo_draw(conf, np.random.randint(0, high=2 ** 8), config_num=1)

    df = pd.DataFrame(d, columns=['arrival_time', 'fundamental_value', 'price', 'buy_sell_indicator', 'time_in_force', 'pegged_state'])
    df['market_id_in_subsession'] = 0
    df = df[['arrival_time', 'market_id_in_subsession', 'price', 'buy_sell_indicator', 'time_in_force']]
    df.to_csv(external_arrivals_file_name, index=False)

    #Move investors arrival file to session_config folder
    os.rename(os.getcwd() + '/' + external_arrivals_file_name, current_dir + external_arrivals_file_name)
    print('Successfully created external arrivals file ' + str(i + 1))

    
    #Create external feed file to session_config folder
    print('Generating external feed file ' + str(i + 1))
    main(current_dir + external_arrivals_file_name, external_feed_file_name)

    #Replace any N/A values
    dataframe = pd.read_csv(external_feed_file_name)
    dataframe['e_signed_volume'] = dataframe['e_signed_volume'].replace(np.nan, 0)
    dataframe.to_csv(external_feed_file_name, index=False)

    #Move external feed file to config folder
    os.rename(os.getcwd() + '/' + external_feed_file_name, current_dir +  external_feed_file_name)
    print('Successfully generated external feed file ' + str(i + 1)+ '\n')


#Send email to notify person the script has finished
message = """\
Subject: LEEPS Simulator Notifcation

External feed and arrivals files have been successfully generated."""

context = ssl.create_default_context()
with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
    server.login('leepsnotifier@gmail.com', 'Throwaway')
    server.sendmail('leepsnotifier@gmail.com', receiver_email, message)
    
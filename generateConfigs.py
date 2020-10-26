import os
import pandas as pd
import numpy as np 
import matplotlib.pyplot as plt
import utility
from draw import elo_draw
from high_frequency_trading.session_config.createExternalFeedFromExternalInvestors import main
from datetime import datetime
from shutil import copyfile
import smtplib, ssl
import csv, operator
import yaml

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
trade_file_name_base = 'trade_file'

#Parameters for config file for experiment
#yamlFileName = 'CDA_1groups_3players_3rounds_150_sec.yaml'
yamlFileName = 'CDA_1groups_3playersGroup_15_rounds_240secs_pilotConfigs.yaml'




#Email to receive notification that script is done
receiver_email = 'kvargha@ucsc.edu'

#Grab current time and create folder with time stamp
now = datetime.now()

# dd-mm-YY_H:M
dt_string = now.strftime('%m-%d-%Y_%H-%M')
current_dir = os.getcwd() + '/session_config/' + dt_string + '_'  + conf['suffix'] + '/'
os.mkdir(current_dir)

#Make directory for plots
plotsDir = current_dir + 'plots/'
os.mkdir(plotsDir)


#Copy parameters file into folder
copyfile(os.getcwd() + '/app/parameters.yaml', current_dir + 'parameters.yaml')

investorsArrivalsDict = {'investor-arrivals' : []}
externalFeedDict = {'external-feed' : []}

#Create number config files depending on num_periods parameter
for i in range(conf['num_periods']):
    file_num = '_T' + str(i + 1) + '_'

    #File name for each period
    investor_arrivals_file_name = investor_arrivals_file_name_base + file_num + dt_string + '_' + conf['suffix'] + '.csv' 
    external_arrivals_file_name = external_arrivals_file_name_base + file_num + dt_string + '_' + conf['suffix'] + '.csv' 
    external_feed_file_name = external_feed_file_name_base + file_num + dt_string + '_' + conf['suffix'] +'.csv'
    trade_file_name = trade_file_name_base + file_num + dt_string + '_' + conf['suffix'] +'.csv'

    #Append file names to dictionary
    investorsArrivalsDict['investor-arrivals'].append(investor_arrivals_file_name)
    externalFeedDict['external-feed'].append(external_feed_file_name)

    #Create investors arrival file
    seed = np.random.randint(0, high=2 ** 8)
    print('Generating investors arrival files ' + str(i + 1))
    d, fundamental_values = elo_draw(conf, seed, config_num=0)

    df = pd.DataFrame(d, columns=['arrival_time', 'fundamental_value', 'price', 'buy_sell_indicator', 'time_in_force', 'pegged_state'])
    df['market_id_in_subsession'] = 1
    df = df[['arrival_time', 'market_id_in_subsession', 'price', 'buy_sell_indicator', 'time_in_force', 'fundamental_value']]
    df.to_csv(investor_arrivals_file_name, index=False)

    #Move investors arrival file to session_config folder
    os.rename(os.getcwd() + '/' + investor_arrivals_file_name, current_dir + investor_arrivals_file_name)
    print('Successfully created investors arrivals file ' + str(i + 1))

    #Generate investor arrivals plots
    plotDF = df[['arrival_time', 'buy_sell_indicator']]
    plotDF['fundDiff'] = df['price'].astype(float) - df['fundamental_value'].astype(float)
    plotDF['price'] = df['price'].astype(float)
    plotDF['arrival_time'] = df['arrival_time'].astype(float)
    plotDF['buy_sell_indicator'] = df['buy_sell_indicator']
    
    #Variables for B indicator
    buyX = plotDF.loc[plotDF.buy_sell_indicator == 'B', 'arrival_time']
    buyY = plotDF.loc[plotDF.buy_sell_indicator == 'B', 'fundDiff']
    buyPrice = plotDF.loc[plotDF.buy_sell_indicator == 'B', 'price']

    #Plot for histogram buy
    plt.hist(buyY, density=True, bins=10)
    plt.xlabel('Price - Fundamental Value')
    plt.title('Investors Arrivals Focal - Buy')

    #Generate histogram file
    plt.savefig(investor_arrivals_file_name_base + file_num + 'Buy' + '.png', bbox_inches = 'tight')
    #Move histogram file to session_config folder
    os.rename(os.getcwd() + '/' + investor_arrivals_file_name_base + file_num + 'Buy' + '.png', plotsDir + investor_arrivals_file_name_base + file_num + 'Buy' + '.png')

    #Clear plot
    plt.clf()
    
    #Variables for S indicator
    sellX = plotDF.loc[plotDF.buy_sell_indicator == 'S', 'arrival_time']
    sellY = plotDF.loc[plotDF.buy_sell_indicator == 'S', 'fundDiff']
    sellPrice = plotDF.loc[plotDF.buy_sell_indicator == 'S', 'price']

    #Plot for histogram sell
    plt.hist(sellY, density=True, bins=10)
    plt.xlabel('Price - Fundamental Value')
    plt.title('Investors Arrivals Focal - Sell')
    
    #Generate histogram file
    plt.savefig(investor_arrivals_file_name_base + file_num + 'Sell' + '.png', bbox_inches = 'tight')
    #Move histogram file to session_config folder
    os.rename(os.getcwd() + '/' + investor_arrivals_file_name_base + file_num + 'Sell' + '.png', plotsDir + investor_arrivals_file_name_base + file_num + 'Sell' + '.png')
    
    #Clear plot
    plt.clf()

    #Generate investors arrivals focal random order
    plt.plot(df['arrival_time'].astype(float), df['fundamental_value'].astype(float), color = 'black', label = 'Fundamental Value')
    plt.hlines(y = buyPrice, xmin = buyX, xmax = buyX + 5, color = 'red', label = 'Buy', linewidth = 1, alpha=0.6)
    plt.hlines(y = sellPrice, xmin = sellX, xmax = sellX + 5, color = 'deepskyblue', label = 'Sell', linewidth = 1, alpha=0.6)

    plt.xlabel('Arrival Times')
    plt.ylabel('Price')
    plt.title('Investors Arrivals Focal')
    plt.legend(loc="upper left", bbox_to_anchor=(1, 0.5))

    #Generate file
    plt.savefig(investor_arrivals_file_name_base + file_num + 'RandomOrders' + '.png', bbox_inches = 'tight')
    #Move random orders file to session_config folder
    os.rename(os.getcwd() + '/' + investor_arrivals_file_name_base + file_num + 'RandomOrders' + '.png', plotsDir + investor_arrivals_file_name_base + file_num + 'RandomOrders' + '.png')
    
    #Clear plot
    plt.clf()




    #Create external arrivals file
    d , fundamental_values = elo_draw(conf, seed, config_num=1)

    df = pd.DataFrame(d, columns=['arrival_time', 'fundamental_value', 'price', 'buy_sell_indicator', 'time_in_force', 'pegged_state'])
    df['market_id_in_subsession'] = 1
    df = df[['arrival_time', 'market_id_in_subsession', 'price', 'buy_sell_indicator', 'time_in_force', 'fundamental_value']]
    df.to_csv(external_arrivals_file_name, index=False)

    #Move external arrivals file to session_config folder
    os.rename(os.getcwd() + '/' + external_arrivals_file_name, current_dir + external_arrivals_file_name)
    print('Successfully created external arrivals file ' + str(i + 1))

    #Generate external investor arrivals plots
    plotDF = df[['arrival_time', 'buy_sell_indicator']]
    plotDF['fundDiff'] = df['price'].astype(float) - df['fundamental_value'].astype(float)
    plotDF['price'] = df['price'].astype(float)
    plotDF['arrival_time'] = df['arrival_time'].astype(float)
    plotDF['buy_sell_indicator'] = df['buy_sell_indicator']
    
    #Variables for B indicator
    buyX = plotDF.loc[plotDF.buy_sell_indicator == 'B', 'arrival_time']
    buyY = plotDF.loc[plotDF.buy_sell_indicator == 'B', 'fundDiff']
    buyPrice = plotDF.loc[plotDF.buy_sell_indicator == 'B', 'price']


    #Plot for histogram buy
    plt.hist(buyY, density=True, bins=10)
    plt.xlabel('Price - Fundamental Value')
    plt.title('Investors Arrivals Focal - Buy')

    #Generate histogram file
    plt.savefig(external_arrivals_file_name_base + file_num + 'Buy' + '.png', bbox_inches = 'tight')
    #Move histogram file to session_config folder
    os.rename(os.getcwd() + '/' + external_arrivals_file_name_base + file_num + 'Buy' + '.png', plotsDir + external_arrivals_file_name_base + file_num + 'Buy' + '.png')

    #Clear plot
    plt.clf()
    
    #Variables for S indicator
    sellX = plotDF.loc[plotDF.buy_sell_indicator == 'S', 'arrival_time']
    sellY = plotDF.loc[plotDF.buy_sell_indicator == 'S', 'fundDiff']
    sellPrice = plotDF.loc[plotDF.buy_sell_indicator == 'S', 'price']

    #Plot for histogram sell
    plt.hist(sellY, density=True, bins=10)
    plt.xlabel('Price - Fundamental Value')
    plt.title('Investors Arrivals Focal - Sell')
    
    #Generate histogram file
    plt.savefig(external_arrivals_file_name_base + file_num + 'Sell' + '.png', bbox_inches = 'tight')
    #Move histogram file to session_config folder
    os.rename(os.getcwd() + '/' + external_arrivals_file_name_base + file_num + 'Sell' + '.png', plotsDir + external_arrivals_file_name_base + file_num + 'Sell' + '.png')
    
    #Clear plot
    plt.clf()

    #Generate external investors arrivals random order
    plt.plot(df['arrival_time'].astype(float), df['fundamental_value'].astype(float), color = 'black', label = 'Fundamental Value')
    plt.hlines(y = buyPrice, xmin = buyX, xmax = buyX + 5, color = 'red', label = 'Buy', linewidth = 1, alpha=0.6)
    plt.hlines(y = sellPrice, xmin = sellX, xmax = sellX + 5, color = 'deepskyblue', label = 'Sell', linewidth = 1, alpha=0.6)

    plt.xlabel('Arrival Times')
    plt.ylabel('Price')
    plt.title('External Investors Arrivals')
    plt.legend(loc="upper left", bbox_to_anchor=(1, 0.5))

    #Generate file
    plt.savefig(external_arrivals_file_name_base + file_num + 'RandomOrders' + '.png', bbox_inches = 'tight')
    #Move random orders file to session_config folder
    os.rename(os.getcwd() + '/' + external_arrivals_file_name_base + file_num + 'RandomOrders' + '.png', plotsDir + external_arrivals_file_name_base + file_num + 'RandomOrders' + '.png')
    
    #Clear plot
    plt.clf()




    
    #Create external feed file to session_config folder
    print('Generating external feed file ' + str(i + 1))
    main(current_dir + external_arrivals_file_name, external_feed_file_name, trade_file_name)

    #Move trade file to config folder
    os.rename(os.getcwd() + '/' + trade_file_name, current_dir +  trade_file_name)

    #Replace any N/A values
    dataframe = pd.read_csv(external_feed_file_name)
    dataframe['e_signed_volume'] = dataframe['e_signed_volume'].replace(np.nan, 0)
    dataframe.to_csv(external_feed_file_name, index=False)

    #Generate external feed plots

    #Variables for best ask
    bestAsk = dataframe.loc[dataframe.e_best_offer != 0x7FFFFFFF, 'e_best_offer']
    bestAskArrivalTime = dataframe.loc[dataframe.e_best_offer != 0x7FFFFFFF, 'arrival_time']



    #Generate plot
    #plt.hlines(y = dataframe['e_best_bid'].astype(float), xmin = dataframe['arrival_time'].astype(float), xmax = dataframe['arrival_time'].astype(float) + 5, color = 'red', label = 'Best Bid', linewidth = 1, alpha=0.6)
    #plt.hlines(y = bestAsk.astype(float), xmin = bestAskArrivalTime.astype(float), xmax = bestAskArrivalTime.astype(float) + 5, color = 'deepskyblue', label = 'Best Offer', linewidth = 1, alpha=0.6)
    plt.plot(dataframe['arrival_time'].astype(float), dataframe['e_best_bid'].astype(float), color = 'red', label = 'Best Bid', linewidth = 1, alpha=0.6)
    plt.plot(bestAskArrivalTime.astype(float), bestAsk.astype(float), color = 'deepskyblue', label = 'Best Offer', linewidth = 1, alpha=0.6)
    
    plt.xlabel('Arrival Times')
    plt.ylabel('Price')
    plt.title('External Feed BBBO')
    plt.legend(loc="upper left", bbox_to_anchor=(1, 0.5))

    #Generate file
    plt.savefig(external_feed_file_name_base + file_num + 'BBBO' + '.png', bbox_inches = 'tight')
    #Move external feed plot file to session_config folder
    os.rename(os.getcwd() + '/' + external_feed_file_name_base + file_num + 'BBBO' + '.png', plotsDir + external_feed_file_name_base + file_num + 'BBBO' + '.png')
    

    
    #Add fundamental value jumps to external arrivals file
    with open(current_dir + external_arrivals_file_name, 'a') as f:
        writer = csv.writer(f)

        for x in fundamental_values:
            writer.writerow([x[0], 0, '', 'J', '', x[1]])

    #Sort csv by arrival time
    with open(current_dir + external_arrivals_file_name, 'r') as f:
        reader= csv.reader(f)
        header = next(reader)
        sortedData = sorted(reader, key=operator.itemgetter(0), reverse=False)
    
    #Write sorted data to csv file
    with open(current_dir + external_arrivals_file_name, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(sortedData)

    #Move external feed file to config folder
    os.rename(os.getcwd() + '/' + external_feed_file_name, current_dir +  external_feed_file_name)
    print('Successfully generated external feed file ' + str(i + 1)+ '\n')


#Add investors arrivals file and external feed file names to config for experiment

#Copy parameters file into folder
copyfile(os.getcwd() + '/app/' + 'experimentConfig.yaml', current_dir + yamlFileName)

#Combine file name dictionaries
exogenousEvents = {'exogenous-events' : [investorsArrivalsDict, externalFeedDict]}
parameters = {'parameters': conf['parameters']}
session = {'session': conf['session']}


#Update config file names 
with open(current_dir + yamlFileName, 'r') as inputFile:
    cur_yaml = yaml.load(inputFile)
    cur_yaml.update(exogenousEvents)
    cur_yaml.update(parameters)
    cur_yaml.update(session)

with open(current_dir + yamlFileName, 'w') as outputFile:
    yaml.safe_dump(cur_yaml, outputFile, default_flow_style=False)



'''

#Send email to notify person the script has finished
message = """\
Subject: LEEPS Simulator Notifcation

External feed and arrivals files have been successfully generated."""

context = ssl.create_default_context()
with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
    server.login('leepsnotifier@gmail.com', 'Throwaway')
    server.sendmail('leepsnotifier@gmail.com', receiver_email, message)
'''
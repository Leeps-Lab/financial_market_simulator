Conceptual Overview
==================

Financial Market Simulator: a tool to create systems
or networks with financial market contexts.

This repo contains code for simulating simplified high-frequency trading
market environments, like the one described in Budish, Cramton, and Shim
(2013). Currently, the exchange types supported by the simulator are
Continuous Double Auction (CDA, also known as Continuous Limit Order Book,
CLOB), Frequent Batch Auction (FBA), and combinations of the two. Other
exchange types such as IEX are in development.

When run, the simulator spawns multiple subprocesses. Two of these subprocesses
simulate exchanges (like the NASDAQ, NYSE, etc). The exchanges are responsible
for processing incoming orders and executing trades. The logic for the
exchanges is in the `exchange_server`_ submodule.
The exchanges broadcast on their own ports.
One exchange is called the focal/primary exchange, and the
other is called the external/secondary exchange. We model the external
exchange to follow the focal exchange, so that the exchanges are highly
correlated but not exactly the same at all points in time, and have traders
observe changes in the market from the external exchange, and submit orders
to the focal exchange. This is similar to how trading works in the real world,
albeit simplified.

Two more subprocesses are proxy servers for the exchanges. The proxy servers
act as indermediaries between traders and the exchanges, and can update states
of the market visible to traders. The proxies are also used to direct
public and private messages to their intended recipients.

The rest of the subprocesses (the number is configurable) simulate traders,
such as investors and high-frequency trading firms. The traders are simulated
by tunable high-frequency trading algorithms. The logic for the trading
algorithms is in the `high_frequency_trading`_ 
submodule, which is an otree experiment.
The code specific to otree (UI, models, pages, etc) is not used;
the reason this simulator uses a subset of the high_frequency_trading submodule
is to keep one SSOT for the trading logic, that both this simulator and the
otree experiment can use.

The simulator initially creates a simple HTTP server (default port 5000).
When the `v1/simulate` endpoint is hit with a GET request, a simulation
is run, and the above subprocesses are created. The parameters for the
simulation are in `parameters.yaml`_.

The simulator collects data about actions taken by traders and auctions run
by the exchanges, and outputs 2 CSV files, one containing trader data and
one containing market data. These are stored in `app/data`.

Installation:
=============

This is tested with python 3.5 - 3.6 - 3.7. However, the exchange server needs
python 3.6.

Postgres database must be installed and running.
Follow this `link`_ for instructions.

Next,
Create a virtual environment

::

    python3 -m venv simulations_venv

and activate it.

::

    source ~/simulations_venv/bin/activate
  
Given postgres is succesfully installed, 
start a shell and
switch to postgres user.

::

    sudo su - postgres

Start postgres shell:

::

    psql

Create a user and a database, and grant permissions to the user:

::

    CREATE DATABASE fimsim;
    CREATE USER simulation_user WITH PASSWORD '<somepassword>';
    GRANT ALL PRIVILEGES ON DATABASE fimsim TO simulation_user;

and exit.

::

    \q

Define and set some environmental variables
for the application to use while talking to the database.
You can also add these commands to your .bash_profile so they persist.

::

    export DBUSER=simulation_user
    export DBPASSWORD=<somepassword>
 
Next, download and clone this repo:

::

    git clone https://github.com/Leeps-Lab/financial_market_simulator.git
  
`cd` into the directory you just downloaded:

::

    cd financial_market_simulator
   
Download and update submodules:

::

    git submodule init
    git submodule update

`cd` into the high_frequency_trading directory and do a similar operation.

::

    cd high_frequency_trading
    git submodule init
    git submodule update
    git pull origin master

Go back to the root directory and do the same for the exchange_server directory.

::

    cd ../exchange_server
    git submodule init
    git submodule update
    git pull origin master

Go back to the root directory.

::

   cd ..
 
Install dependencies:

::

    pip install -r requirements.txt
    
    
From the root directory, create the required database tables.
Note that if tables exist already, they will be destroyed and recreated.

::

    python3 resetdb.py

You can also do this manually:
start an interactive python session

::

    python3
  
and create the relevant tables in the db.

::

    from db import db_commands
    db_commands.create_tables()

**matching engines**

start two more shells
and cd into the exchange_server directory in the repo
you just downloaded.
follow the `instructions`_ here to run an matching engine instance, run two matching engines in separate shells on ports 9001 and 9002 with the CDA format (if you need different ports, make sure to edit settings.py in the root directory accordingly).

*NOTE* This is no longer necessary, no? The simulator automatically creates
the exchanges.

Usage:
=======

::

    python3 run_web_api.py
  
This will start an HTTP server that listens on port 5000.

Session-wide static parameters are defined in file parameters.yaml;
edit it accordingly.

Dynamic parameters (agents' sensitivities, speed technology subscription)
is configured by editing agent_state_configs.csv.

Now, go to a browser of your choice and visit http://localhost:5000/v1/simulate
(or http://localhost:5000/v1/simulate?debug=True to toggle debug mode).
You will get a response message which includes a session id and parameters.
Note this session code since output files will be tagged with this identifier.
This will trigger a simulation session, which after completion will dump two
files in the `app/data` directory.

There is a jupyter notebook front-end that pairs with the simulator.
This gives you a nice interface to interact with and configure the simulator,
visualize and inspect session results.

If you would like to use this tool:

::

  cd app
  jupyter notebook

and go to http://localhost:8888, and check out the 'simulator_HOWTO' file.

Optimizer:
=======

Make sure you are on this branch (ep-cont). Edit your parameters as normal in
app/parameters.yaml. Edit the optimizer params at the top of agent_supervisor.py.
Run your simulation as normal. At the end, graphs will get saved in app/data/.

To do this on the simulator:

::

    ssh <username>@128.114.96.151
    cd /shared/financial_market_simulator
    python3 dbreset.py
    nohup python3 simulate.py &

Before doing the simulate command, edit the params (app/parameters.yaml).

Before doing that or resetting
the database (dbreset.py), make sure no other sims are running:

::

    ps -a

If there is a python3 process running, a simulation is already running - don't
run your own.
At the end, go into app/data. You will see files called <session_code>_agent<#>.csv.
From financial_market_simulator:

::

    python3 visualize.py app/data/<session_code>_agent1.csv app/data/<session_code>_agent2.csv app/data/<session_code>_agent2.csv

Note that you can do this on your own computer also. If you do, make sure redis
is running. To do symmetric mode, make sure `symmetric` is `true` in
app/parameters.yaml.

.. _link: https://www.postgresql.org/download/
.. _instructions: https://github.com/Leeps-Lab/exchange_server/blob/master/README.rst
.. _high_frequency_trading: https://github.com/Leeps-Lab/high_frequency_trading
.. _exchange_server: https://github.com/Leeps-Lab/exchange_server
.. _parameters.yaml: app/simulator_configs/parameters.yaml


# Eli Pandolfo notes on financial_market_simulator

#### Python Versions
While the simulator is allegedly tested with python3.5-3.7, the exchange server needs python3.6.
Since I think using pyenv is the easiest way to manage virtual environments with versions of python
different from your system version, I recommend making a pyenv virtualenv with version 3.6.5 and
using that for the entire simulator (including the exchange-server submodule). Pyenv lets you
make a virtual environment local to a directory and its subdirectories, which is exactly
what is needed here.

#### README.md
- Line 6: python version, see above
- The postgres instructions are not applicable to everyone (eg people who
install postgres with homebrew).
- Line 44: `DATABASE simulations` should be changed to `DATABASE fimsim`.
- Create the relevant tables in the db: we have moved this to a script called
    `resetdb.py`. Usage: `python resetdb.py`.
- You don't need to start 2 separate exchange servers, `python3 run_web_api`
starts the exchanges on available ports for you

#### Code
    -   `draw.py` holds the code for the pseudorandom elements of the simulation:
        generating fundamental price jumps, players' random orders, etc.
    1.  `api/app.py` starts a really simple http server
    1.  When you hit the `v1/simulate` endpoint, app.py opens a subprocess and runs
        `simulate.py`.
    1.  `simulate.py` creates 2 markets (focal/primary/fundamental value,
        external/secondary/public signal) in subprocesses on 2 available ports.
        These are created with `exchange_server/run_exchange_server.py`. It also
        creates 2 proxy servers, one for each exchange server. The proxy servers
        server as an intermediate between the agents and the exchange server,
        and simplify the messages to and from the exchange, so that the exchange
        can remain as simple as possible.
    1.  `simulate.py` then creates some agents, each in a subprocess. These
        are created with `run_agent.py`. There are 2 rabbit agents, and some
        number of dynamic agents.
    1.  `simulate.py` waits until all processes terminate themselves (could be
        entry point for bugs), and if they all exit cleanly will write the database
        to CSV files. There are 2 tables, 1 for agents and 1 for markets, and 2
        CSV files, which correspond to the database tables. It uses a postgres
        database to allow concurrent writes.
    1. `run_agents.py`. For rabbit agents, creates generator for choices agent will
        take during simulation. For dynamic agents, uses params in some file in
        `app/simulation_configs`. It then sets up TCP connections with the OUCH
        ports on the exchanges (I think the model is receive from external, send
        to focal). It then sets up a callback to run at the end of the session
        that stops the reactor (the TCP connection thing). It sends the params
        for the agent to `agents/dynamic_agent` and `agents/pacemaker_agent`
        for dynamic/ELO and rabbit agents, respectively.
    1.  `agents/pacemaker_agent.py`. A baseline agent, uses minimal market
        information for making orders.
    1.  `agents/dynamic_agent.py` handles incoming messages but does not perform
        any trading logic. That is done in `high_frequency-trading/hft/trader.py`.
    1.  `high_frequency_trading/hft/trader.py` defines an ELOTrader class and an
        extended ELOInvestor class. These hold logic for processing messages,
        but not for responding to them (at first glance). I think the logic
        is in `h/h/trader_states.py`. It is really fragmented.
    1.  `run_proxy.py` creates a proxy server; registers its OUCH port with the
        reactor. `proxies/elo_market_proxy` wraps `high_frequency_trading/hft/
        market.py`. This has code to update features of the market.

#### Exchange Server code
    -   `exchange.py` handles messages to the server. Does not appear to handle
        auctions.
    -   `exchange_client.py` is a client for the ouch server. I guess the OUCH
        protocol has its own server that acts as an intermediate between the proxy
        server and the exchange?
    -   `fba_exchange.py` is an extension of the Exchange class defined in
        `exchange.py`. It handles FBA environments.

        

#### Bugs

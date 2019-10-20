cd ..
mkdir fms
mv financial_market_simulator fms
cd fms
brew upgrade pyenv || brew install pyenv
brew upgrade postgresql || brew install postgresql
brew upgrade redis || brew install redis
brew services start postgresql
brew services start redis

pyenv install 3.6.8
pyenv virtualenv 3.6.8 v_fms
pyenv local v_fms

psql postgres << EOF
CREATE DATABASE fimsim;
CREATE USER simulation_user WITH PASSWORD 'fmsbananaslug';
GRANT ALL PRIVILEGES ON DATABASE fimsim TO simulation_user;
EOF

if [[ $SHELL == "/bin/zsh" ]]; then
    echo "DBUSER=simulation_user" >> ~/.zshrc  
    echo "DBPASSWORD=fmsbananaslug" >> ~/.zshrc
else
    echo "DBUSER=simulation_user" >> ~/.bash_profile
    echo "DBPASSWORD=fmsbananaslug" >> ~/.bash_profile
fi

cd financial_market_simulator
git submodule init
git submodule update

cd high_frequency_trading
git submodule init
git submodule update

cd ..
pip install -r requirements.txt

python3 dbreset.py


FROM python:3


# Configure apt and install packages
RUN apt-get update \
    && apt-get -y install --no-install-recommends apt-utils dialog 2>&1 \
    && apt-get -y install git \
    && apt-get install rabbitmq-server -y \
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

#ENV
ENV WORKSPACE /workspaces
ENV SSH_DIR /workspaces/.ssh
ENV ANT_BOT_PATH /workspaces/Ants-Auto-Trading-Bot

#mkdir
RUN mkdir -p $SSH_DIR

#code clone
WORKDIR ${WORKSPACE}
RUN git clone https://github.com/ccassistant/Ants-Auto-Trading-Bot.git

#bot copy
WORKDIR /workspaces/Ants-Auto-Trading-Bot/
RUN git checkout dev \
    && python3 -m venv venv_ants

#add PYTHONPATH
ENV PYTHONPATH "/workspaces/Ants-Auto-Trading-Bot:/workspaces/Ants-Auto-Trading-Bot/ants:/workspaces/Ants-Auto-Trading-Bot/messenger:/workspaces/Ants-Auto-Trading-Bot/enviroments:/workspaces/Ants-Auto-Trading-Bot/exchange:/workspaces/Ants-Auto-Trading-Bot/exchange/exchangem"

#config파일을 받도록한다
VOLUME [ "/workspaces/.ssh", "/workspaces/Ants-Auto-Trading-Bot/configs", "/workspaces/Ants-Auto-Trading-Bot/logs"]

#pip install
RUN . ${ANT_BOT_PATH}/venv_ants/bin/activate \ 
    && pip install -r requirements.txt

#run bot
CMD bash entrypoint.sh

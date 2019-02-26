# -*- coding: utf-8 -*-
# https://github.com/python-telegram-bot/python-telegram-bot

import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

import ants.utils as utils
import logging
import json

class TelegramRepoter():
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        try:
            mtoken = utils.readConfig('configs/telegram_bot.conf')
            
            if(mtoken['use'].upper() == 'TRUE'):
                self.use = True
            else:
                self.use = False
                self.logger.info('Telegram disable')
                return
            
            self.token = mtoken['bot_token']
            self.chat_id = mtoken['chat_id']
            self.bot = telegram.Bot(token=mtoken["bot_token"])
            
            self.logger.info('Telegram is Ready, {}'.format(self.bot.get_me()))
            self.send_message('Telegram Repoter is ready')
        except Exception as exp:
            self.logger.warning('Can''t load Telegram Config : {}'.format(exp))
            self.use = False
            return
        
    def run_listener(self):
        if(self.use == False):
            return
        
        self.updater = Updater(self.token)
        dp = self.updater.dispatcher
        
        # on different commands - answer in Telegram
        dp.add_handler(CommandHandler("menu", self.menu))
        dp.add_handler(CommandHandler("help", self.help))
        dp.add_handler(CommandHandler("whoami", self.whoami))
        dp.add_handler(CommandHandler("room", self.roominfo))
        dp.add_handler(CommandHandler("setid", self.setid))
        dp.add_handler(CallbackQueryHandler(self.button))
        #총 수익
        #오늘 수익
        #거래소 잔고
        #거래소 오더 상황(미체결)
        #거래소 동작(빤스런, 올매수)
        #거래소 스탑로스 설정 및 동작
        #inline keyboard를 사용하여 명령어 제어
        
        # on noncommand i.e message - echo the message on Telegram
        # dp.add_handler(MessageHandler(Filters.text, self.echo))
        
        # log all errors
        dp.add_error_handler(self.error)
        
        # Start the Bot
        # 내부적으로 쓰레드로 처리된다.
        # https://github.com/python-telegram-bot/python-telegram-bot/blob/master/telegram/ext/updater.py
        self.updater.start_polling()
    
        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        self.updater.idle()
        
    def send_message(self, msg):
        self.logger.debug('send_message : {}'.format(self.use))
        if(self.use) :
            self.logger.debug('send_msg : {}-{}'.format(self.chat_id, msg))
            self.bot.sendMessage(self.chat_id, msg)
    
    def roominfo(self, update, context):
        context.message.reply_text(str(context.message.chat.type))
        context.message.reply_text(str(context.message.chat))
        
    def whoami(self, update, context):
        context.message.reply_text(str(context.message.chat.type))
        
        if(context.message.chat.type != 'private'):
            context.message.reply_text('1:1방에서 확인하세요')
            return
            
        # self.send_message(str(context.message.chat.id))
        context.message.reply_text(str(context.message.chat.id))
    
    def setid(self, update, context):
        if(context.message.chat.type != 'private'):
            context.message.reply_text('1:1방에서만 설정 가능합니다')
            return
        
        # 'from': {'id': 444609550, 'first_name': 'LeMY', 'is_bot': False, 'username': 'lemy0715',
        
        user = context.effective_user
        print(user)
        
        self.chat_id = user.id
        
        msg = '환영합니다. {}님'.format(user.first_name)
        self.send_message(msg)
    
        
    def menu(self, update, context):
        """Send a message when the command /start is issued."""
        """
        {'message_id': 4034, 'date': 1551111044, 'chat': {'id': -241706808, 'type': 'group', 'title': 'TestGroup', 'all_members_are_administrators': False}, 
        'text': '/whoami', 
        'entities': [{'type': 'bot_command', 'offset': 0, 'length': 7}], 
        'caption_entities': [], 
        'photo': [], 
        'new_chat_members': [], 
        'new_chat_photo': [], 
        'delete_chat_photo': False, 
        'group_chat_created': False, 
        'supergroup_chat_created': False, 
        'channel_chat_created': False, 
        'from': {'id': 444609550, 'first_name': 'LeMY', 'is_bot': False, 'username': 'lemy0715', 'language_code': 'ko'}}
        """
        keyboard = [[InlineKeyboardButton("Option 1", callback_data='1'),
                    InlineKeyboardButton("Option 2", callback_data='2')],
                    [InlineKeyboardButton("Option 3", callback_data='3')]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.message.reply_text('Please choose:', reply_markup=reply_markup)
        
    def button(self, update, context):
        query = context.callback_query
        query.edit_message_text(text="Selected option: {}".format(query.data))
    
    def help(self, update, context):
        """Send a message when the command /help is issued."""
        context.message.reply_text('Help!')
    
    def echo(self, update, context):
        """Echo the user message."""
        # update is bot
        # context is <class 'telegram.update.Update'>
        # context.message is <class 'telegram.message.Message'>
        # bot.send_message(update.message.chat_id, *args, **kwargs)
        print(type(context)) 
        # print(update.get_me())
        # print(getattr(update))
        print(type(context.message.reply_text))
        # print(update.message.replay_text)
        context.message.reply_text(context.message.text)
    
    
    def error(self, update, context):
        """Log Errors caused by Updates."""
        self.logger.warning('Update "%s" caused error "%s"', update, context.error)
    

if __name__ == '__main__':
    print('strategy test')
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_hander = logging.StreamHandler()
    stream_hander.setFormatter(formatter)
    logger.addHandler(stream_hander)
    
    logging.getLogger("ccxt.base.exchange").setLevel(logging.WARNING)
    logging.getLogger("telegram.vendor.ptb_urllib3.urllib3.connectionpool").setLevel(logging.WARNING)
    
    tel = TelegramRepoter()

    # tel.send_message("봇클래스 테스트.")

    tel.run_listener()
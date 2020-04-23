#!/usr/bin/env python3
# Standard library modules.
import io
import os
import sys
import json
import time
import signal
import random
import logging
import traceback
from functools import wraps

# Third party modules.
import telegram
from tabulate import tabulate
from mosquito.utils import NameSpaceDict, SingletonContextABC
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Local modules
from util import tts, timeout
from challenge import Challenge

# Globals and constants variables.
_FSTRING_LOG = '{asctime}  {threadName:<25}  {levelname:>8}:  {message}'
_FSTRING_MSG = '{message}'

_FORMATTER_LOG = logging.Formatter(_FSTRING_LOG, style='{')
_FORMATTER_MSG = logging.Formatter(_FSTRING_MSG, style='{')

_STDOUT_HANDLER = logging.StreamHandler(stream=sys.stdout)
_STDOUT_HANDLER.setFormatter(_FORMATTER_LOG)

_FILE_HANDLER_LOG = logging.FileHandler(os.path.expanduser('~/.das_system/log'), encoding='utf-8')
_FILE_HANDLER_LOG.setFormatter(_FORMATTER_LOG)

_FILE_HANDLER_MSG = logging.FileHandler(os.path.expanduser('~/.das_system/msg'), encoding='utf-8')
_FILE_HANDLER_MSG.setFormatter(_FORMATTER_MSG)

system_log = logging.getLogger('das-system-log')
system_log.addHandler(_STDOUT_HANDLER)
system_log.addHandler(_FILE_HANDLER_LOG)

system_msg = logging.getLogger('das-system-msg')
system_msg.addHandler(_STDOUT_HANDLER)
system_msg.addHandler(_FILE_HANDLER_LOG)
system_msg.addHandler(_FILE_HANDLER_MSG)

system_log.setLevel(logging.DEBUG)
system_msg.setLevel(logging.DEBUG)

# TODO update
TEMPLATE_HELP = """
*Hilfe*
_Unterstützte Befehle_
  - `\\start`: Starte die Konversation mit dem System
  - `\\challenge [name]`: Wähle die nächste challenge. Wenn du keinen Namen angibst, wird eine zufällige Challenge gewählt
  - `\\giveup`: Die aktuelle Challenge aufgeben
  - `\\reset`: Löscht deinen Zustand. Danach fängst du wieder von ganz vorne an!
  - `\\help`: Diese Hilfe anzeigen
  
_Challenges_
```
{challenges}
```

_Aktive Challenge:_ *{active}* 
`{active_help}`
""".strip()


def forbidden(update, context):
    system_msg.info(f'not authorized: {update.effective_user.name}')

    context.bot.send_message(
        text=f'`{update.effective_user.name}: access denied`',
        chat_id=update.effective_chat.id,
        parse_mode=telegram.ParseMode.MARKDOWN
    )


def initial_state():
    return dict(
        active=None,
        solved=[]
    )


def callback(func):
    @wraps(func)
    def wrapper(update, context):
        system_msg.info(f'callback: {update.effective_chat.id} ({update.effective_user.username}) --> {func.__name__}')

        try:
            with BotContext() as bc:
                if update.effective_user.name not in bc.config.telegram.allowed_users:
                    return forbidden(update, context)
    
                if update.effective_user.username not in bc.state:
                    bc.state[update.effective_user.username] = initial_state()

                bc.config.telegram.chats = sorted(
                    {*bc.config.telegram.chats, update.effective_chat.id}
                )
    
                msg = func(update, context, bc.state[update.effective_user.username])

                if msg is not None:
                    context.bot.send_message(
                        text=msg,
                        chat_id=update.effective_chat.id,
                        parse_mode=telegram.ParseMode.MARKDOWN
                    )
            
        except Exception as error:
            with io.StringIO() as buffer:
                traceback.print_exception(type(error), error, error.__traceback__, file=buffer)
                system_log.error(buffer.getvalue().replace('\n', '\\n'))

            context.bot.send_message(
                text='Ein interner Fehler ist aufgetreten, '
                     'ich kann die Nachricht nicht verarbeiten! O.o',
                chat_id=update.effective_chat.id,
                parse_mode=telegram.ParseMode.MARKDOWN
            )

            raise error

    return wrapper


@callback
def cmd_start(update, context, *args, **kwargs):
    return 'Hallo, ich bin `das System`.\n\n' \
           'Mit `\\help` bekommst du eine Übersicht der Befehle und deines aktuellen Zustands.'


@callback
def cmd_help(update, context, state):
    return TEMPLATE_HELP.format(
        active=state.active,
        active_help=Challenge.load(state).help if state.active else '',
        challenges=tabulate(
            [(c.name, c.unlocked, c.solved) for c in Challenge.list(state)],
            ['challenge', 'unlocked', 'solved'],
            tablefmt='fancy_grid')
    )


@callback
def cmd_challenge(update, context, state, *args, **kwargs):
    if state.active is not None:
        return f'*Es ist bereits Challenge "{state.active}" aktiv*\n\n' \
               f'{Challenge.registry[state.active].help}'

    candidates = {c.name: c for c in Challenge.list(state, unlocked=True, solved=False)}

    # handle case when challenge is specified by user
    if context.args:
        if context.args[0] in candidates:
            candidates = {context.args[0]: candidates[context.args[0]]}
        else:
            return f'Du kannst "{context.args[0]}" nicht auswählen!\n\n' \
                   f'Folgende Challenges sind für dich freigeschaltet: {list(candidates.keys())}'

    # if a challenge is remaining, set it active
    if candidates:
        challenge = random.choice(list(candidates.values()))
        state.active = challenge.name

        context.bot.send_message(
            text=f'Challenge `{challenge.name}` wurde aktiviert',
            chat_id=update.effective_chat.id,
            parse_mode=telegram.ParseMode.MARKDOWN
        )

        return challenge.start(update, context)

    return 'Ich habe leider keine neue Challenge für Dich :/'


@callback
def cmd_giveup(update, context, state):
    if not state.active:
        return 'Du machst doch gerade gar keine Challenge🦦 '

    state.active = None

    return 'schade Schokolade :/'


@callback
def cmd_submit(update, context, state):
    if not state.active:
        return 'Cool cool, aber was soll ich damit anfangen?'

    challenge = Challenge.load(state)
    with timeout(60):
        challenge.submit(update, context)

    if challenge.solved:
        state.active = None
        state.solved.append(challenge.name)
        return f'Cool! Du hast die Challenge `{challenge.name}` gelöst!'

    return 'Die Lösung war leider nicht korrekt :/'


@callback
def cmd_reset(update, context, state):
    state.clear()
    state.update(initial_state())
    return 'Dein Zustand wurde gelöscht!'


def cmd_echo(update, context):
    context.bot.send_message(text=' '.join(context.args), chat_id=update.effective_chat.id)


def cmd_tts_echo(update, context):
    with tts(' '.join(context.args)) as f:
        context.bot.send_voice(chat_id=update.effective_chat.id, voice=f)


def echo(update, context):
    return update.effective_message.text_markdown


def voice(update, context):
    msg = 'Joooo! Ich kann zwar reden, aber glaub bloß nicht, dass ich dir zuhöre.'
    with tts(msg) as buffer:
        context.bot.send_voice(chat_id=update.effective_chat.id, voice=buffer)


class BotContext(SingletonContextABC):
    def __on_open__(self):
        system_log.debug('open crawler context')

        self.path = os.path.expanduser(os.environ.get('CONFIG_PATH', '~/.das_system'))

        os.makedirs(self.path, exist_ok=True)

        with open(os.path.join(self.path, 'config.json'), mode='rt') as f:
            self.config = NameSpaceDict(json.load(f))

        with open(os.path.join(self.path, 'state.json'), mode='rt') as f:
            self.state = NameSpaceDict(json.load(f))

        system_log.debug(f'loaded config and state from: {self.path}')

        self.telegram = Updater(token=self.config.telegram.token, use_context=True)
        self.telegram.dispatcher.add_handler(CommandHandler('start', cmd_start))
        self.telegram.dispatcher.add_handler(CommandHandler('help', cmd_help))
        self.telegram.dispatcher.add_handler(CommandHandler('challenge', cmd_challenge))
        self.telegram.dispatcher.add_handler(CommandHandler('giveup', cmd_giveup))
        self.telegram.dispatcher.add_handler(CommandHandler('reset', cmd_reset))
        self.telegram.dispatcher.add_handler(CommandHandler('echo', cmd_echo))
        self.telegram.dispatcher.add_handler(CommandHandler('ttsecho', cmd_tts_echo))
        self.telegram.dispatcher.add_handler(MessageHandler(Filters.all, cmd_submit))
        self.telegram.start_polling(clean=True)

        system_log.debug(f'launched telegram updater')

    def __on_close__(self):
        self.persist()

        self.telegram.stop()
        system_log.debug(f'stopped telegram updater')

        del self.path
        del self.config
        del self.state
        del self.telegram

        system_log.debug('close bot context')

    def persist(self):
        with open(os.path.join(self.path, 'config.json'), mode='wt') as f:
            json.dump(self.config, f, indent=4)

        with open(os.path.join(self.path, 'state.json'), mode='wt') as f:
            json.dump(self.state, f, indent=4)


def signal_handler(sig, frame):
    system_log.info('terminate')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def main():
    with BotContext() as ctx:
        while True:
            ctx.persist()
            time.sleep(1)


if __name__ == '__main__':
    main()

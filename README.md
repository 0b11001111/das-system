# Telegram Bot for Learning Python (German)

This is a fun project to motivate beginners for learning python. It does not aim to be a complete
tutorial.

**WARNING: This bot executes code provided by users without any checking, sandboxing or other
security mechanisms. Never expose it to the public!**

## setup

First of all you need to create telegram bot which can be done by texting the 
[botfather](https://telegram.me/botfather). It provides you with a token we need later.

Then install `das system` via [pipenv](https://github.com/pypa/pipenv):
```shell script
pipenv install .
```

Further, create a config file located at `~/.das_system/config.json`:
```json
{
    "telegram": {
        "allowed_users": [
            "@user_1",
            "@user_2"
        ],
        "chats": [],
        "token": "..."
    }
}
```

## run
````shell script
pipenv run systembot
````
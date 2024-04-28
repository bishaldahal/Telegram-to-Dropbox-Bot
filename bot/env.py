import os
from dotenv import load_dotenv,set_key
load_dotenv()


def get_env(name: str, terminal_action: bool = True) -> str:
    if name in os.environ:
        return os.environ[name]
    if terminal_action:
        value = input(f'Enter your {name}: ')
        with open('.env', 'a') as f:
            f.write(f'{name}={value}\n')
        return value
    else:
        return name

dotenv_path = '.env'

def update_env_file(key, value):
    set_key(dotenv_path, key, value)
    load_dotenv()
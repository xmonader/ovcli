import base64
import os
import subprocess


def base64url_decode(input):
    """Helper method to base64url_decode a string.
    Args:
        input (str): A base64url_encoded string to decode.
    """
    rem = len(input) % 4

    if rem > 0:
        input += b'=' * (4 - rem)

    return base64.urlsafe_b64decode(input)


def select_item_fzf(items, prompt):
    proc = subprocess.Popen(['fzf', '--prompt', prompt], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.stdin.write(('\n'.join(items)).encode('utf-8'))
    proc.stdin.close()
    proc.wait()
    return proc.stdout.read().strip().decode('utf-8')

def select_item(items, prompt, match=None):
    items = list(sorted(items))
    if match:
        items = list(filter(lambda item: match in item, items))
        if len(items) == 0:
            raise LookupError('Could not find item with filter {}'.format(match))
    if len(items) == 1:
        return items[0]
    try:
        subprocess.check_call(['which', 'fzf'], stdout=open(os.devnull))
    except subprocess.CalledProcessError:
        while True:
            for idx, item in enumerate(items):
                print("{}: {}".format(idx + 1, item))
            data = input(prompt)
            if data.isdigit():
                idx = int(data) - 1
                if idx < len(items):
                    return items[idx]
            print('Entered wrong value')
    else:
        return select_item_fzf(items, prompt)

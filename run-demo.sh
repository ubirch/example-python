#!/usr/bin/env bash

python3 -m venv venv
. ./venv/bin/activate

pip --no-cache-dir install -r requirements.txt

# redirects stderr, so make sure you have demo:stdout = true in the demo.ini file
python demo.py 2>/dev/null

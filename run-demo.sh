#!/usr/bin/env bash

cd $(dirname $0)

if [ -z "$VIRTUAL_ENV" ]; then
    python3 -m venv venv
    . ./venv/bin/activate

    pip -q --no-cache-dir install -r requirements.txt
fi

# redirects stderr, so make sure you have demo:stdout = true in the demo.ini file
python src/demo.py $1 2>/dev/null

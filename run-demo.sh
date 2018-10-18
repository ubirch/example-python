#!/usr/bin/env bash

cd $(dirname $0)

if [ -z "$VIRTUAL_ENV" ]; then
    python3 -m venv venv
    . ./venv/bin/activate

    pip -q --no-cache-dir install -r requirements.txt
fi

# don't silence the stderr if stdout is not enabled
if cat ${1:-demo.ini} | grep "stdout\\s*=\\s*true" > /dev/null; then
    python src/demo.py $1 2>/dev/null
else
    python src/demo.py $1
fi

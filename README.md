# Python examples for ubirch API

See [Python client examples on ubirch.github.io](ubirch.github.io/examples.html#python-client) for a nice description
of what's going on here.

## Files
* `demo.ini` - default configuration file for configuring the demo
* `run-validator.sh` - sets up the validator docker container with proper authentication token
* `run-demo.sh` - sets up virtualenv, downloads all the dependencies and runs `src/demo.py`
* `src/demo.py` - main entry point for the examples 

## Running
Be sure to put your authentication token in the config file (`demo.ini` by default).

The first argument to most of the scripts is the path to the config file.
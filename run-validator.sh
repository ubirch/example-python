#!/usr/bin/env bash

UBIRCH_ENV=$(cat ${1:-demo.ini} | grep env | cut -d= -f2 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
export VALIDATOR_BACKEND_ADDRESS=https://api.ubirch.${UBIRCH_ENV}.ubirch.com/api/avatarService/v1/device/verify
export VALIDATOR_ADDITIONAL_HEADERS="Authorization: $(
    cat ${1:-demo.ini} | grep auth | cut -d= -f2 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'
)"

docker run -dti -p8080:8080 -e VALIDATOR_ADDITIONAL_HEADERS -e VALIDATOR_BACKEND_ADDRESS ubirch/standalone-validator:1.0

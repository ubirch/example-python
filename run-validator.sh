#!/usr/bin/env bash

export VALIDATOR_BACKEND_ADDRESS=https://api.ubirch.dev.ubirch.com/api/avatarService/v1/device/verify
export VALIDATOR_ADDITIONAL_HEADERS="Authorization: $(
    cat demo.ini | grep auth | cut -d' ' -f3,4
)"

docker run -dti -p8080:8080 -e VALIDATOR_ADDITIONAL_HEADERS -e VALIDATOR_BACKEND_ADDRESS ubirch/standalone-validator:1.0

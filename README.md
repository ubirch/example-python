# Python examples for ubirch API

This project is a demonstration of ubirch client for Python. The entry point is the [`demo.py` file](src/demo.py).

The demo follows these steps (step names link to the relevant code):
1) [**Setup**](https://github.com/ubirch/example-python/blob/master/src/demo.py#L22-L25)

    In this step the `ubirch.API`, `ubirch.KeyStore` and `ubirch.Protocol` instances are created. Note that the actual
    protocol implementation is a derived class defined in [`ubirch_proto.py` file](src/ubirch_proto.py).
    
    The `ubirch.KeyStore` is needed for generating and verifying message signatures. To initialize the `ubirch.API`
    object, pass your authorization token and the desired ubirch environment name. In this example auth token and
    the environment are [loaded from the configuration file](src/config.py). 

2) [**Checking authorization**](https://github.com/ubirch/example-python/blob/master/src/demo.py#L28-L41)

    Here we check if the auth token used is actually valid. We can do this by simply sending any request using the
    `ubirch.API` instance, but for the sake of demonstration we fetch user info and display the username. This is 
    also an example of how to do ubirch api calls which aren't yet implemented in the `ubirch.API` class (which
    is the case for the `/userInfo` endpoint.
    
3) [**Identity creation**](https://github.com/ubirch/example-python/blob/master/src/demo.py#L28-L41)

    In this step we initialize our keystore and register the newly created certificate in the ubirch backend.
    This happens in two steps: 
    * first, we create the registration message
        ```python
        message = protocol.message_signed(identity_uuid, UBIRCH_PROTOCOL_TYPE_REG, keystore.get_certificate(identity_uuid))
        ```
    * next, we send the message using the `register_identity` method
        ```python
        registration_response = api.register_identity(message)
        ```
        
4) [**Device creation**](https://github.com/ubirch/example-python/blob/master/src/demo.py#L64-L92)

    Here we check if the device already exists, and create it if it doesn't. You can always check the exact meaning of
    the passed arguments in the [API documentation](http://developer.ubirch.com/docs/api/). In our case it's the
    `POST /device` endpoint of the Avatar service.
    
5) [**Sending messages**](https://github.com/ubirch/example-python/blob/master/src/demo.py#L96-L142)

    In this part of the demo we're sending all kinds of messages to the ubirch backend. You can see the currently
    supported payload types in the `Payload Type` section of 
    [ubirch protocol's README](https://github.com/ubirch/ubirch-protocol/blob/master/README.md).
    
    Payload types used in this demo:
    * `0x32` (single) - a measurement represented by an array of numbers, where the first one is interpreted as 
    timestamp (in microseconds)
    * `0x32` (multi) - an array of measurements (see previous point)
    * `0x53` - a generic sensor message; a json/msgpack object, collection of key-value pairs
    * `0x00` - uninterpreted binary data; useful if you have some data that doesn't naturally fit any of the above
    
6) [**Sealing the messages**](https://github.com/ubirch/example-python/blob/master/src/demo.py#L146-L175)

    But what if you don't want to send your sensitive data to ubirch servers, you ask? Well, you can also use ubirch
    to validate your data by sending just its hash, which is presented in this step of the demo. 
    
    Sealing the messages is done by hashing your data and sending the hash to ubirch with `0x00` payload type.
    You can then send your sensitive data to your own backend and verify the integrity on the other side, which
    is demonstrated in the next step...

7) [**Verifying the messages**](https://github.com/ubirch/example-python/blob/master/src/demo.py#L181-L203)

    When you receive messages you previously sealed, you can verify their integrity, by hashing the data in the 
    same way it's been done during the sealing procedure. Having this hash, you can validate your data by sending a
    validation request either to `https://api.ubirch.${ubirch:env}.ubirch.com/api/avatarService/v1/device/verify/${hash}`
    or to your on-premise validator `${validator-address}/validate/${hash}` (coming soon).

## Files
* [`demo.ini`](demo.ini) - default configuration file for configuring the demo
* [`run-validator.sh`](run-validator.sh) - sets up the validator docker container with proper authentication token; run 
this first to showcase the on-premise validation (`validator:address` should be set to `http://localhost:8080/validate`)
* [`run-demo.sh`](run-demo.sh)) - sets up virtualenv, downloads all the dependencies and runs `src/demo.py`
* [`src/demo.py`](src/demo.py) - main entry point for the examples 

## Running
Be sure to put your authentication token in the config file (`demo.ini` by default).

The first argument to most of the scripts is the (optional) path to the config file.

## See also
[ubirch-protocol-python](https://github.com/ubirch/ubirch-protocol-python)
[Other examples on ubirch.github.io](https://ubirch.github.io/examples.html)

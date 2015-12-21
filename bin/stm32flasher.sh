#!/bin/bash

HERE=`dirname $0`

. "$HERE/activate"
python -m hedgehog_light.stm32flasher "$1"
deactivate

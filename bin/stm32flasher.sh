#!/bin/bash

. env/bin/activate
python -m hedgehog_light.stm32flasher "$1"
deactivate

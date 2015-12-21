#!/bin/bash

. env/bin/activate
python -m hedgehog_light "$1"
deactivate

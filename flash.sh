#!/bin/bash

HERE=`dirname $0`

. "$HERE/../env/bin/activate"

python3 "$HERE/main.py" "$1"


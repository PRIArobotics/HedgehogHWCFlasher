Hedgehog HWC Flasher
====================

A simple tool for rewriting the Hedgehog Educational Robotics Controller's firmware.

The Hedgehog Hardware Controller (HWC) uses an STM32 CPU.
Its primary UART, `BOOT0` and `RESET` pins are connected to the Orange Pi, allowing the firmware to be easily rewritten.
This tool implements this functionality.

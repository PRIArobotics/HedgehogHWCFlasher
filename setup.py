from setuptools import setup, find_packages

import hedgehog_light

setup(
    name="stm32flasher",
    description="STM32 USART Flasher",
    version=hedgehog_light.__version__,
    license="AGPLv3",
    url="https://github.com/PRIArobotics/STM32Flasher",
    author="Clemens Koza",
    author_email="koza@pria.at",

    packages=['hedgehog_light'],
    install_requires=['pyserial>=2.7'],
    scripts=['bin/flash.sh'],
)


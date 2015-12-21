from setuptools import setup, find_packages

from hedgehog_light import stm32flasher

setup(
    name="stm32flasher",
    description="STM32 USART Flasher",
    version=stm32flasher.__version__,
    license="AGPLv3",
    url="https://github.com/PRIArobotics/STM32Flasher",
    author="Clemens Koza",
    author_email="koza@pria.at",

    namespace_packages = ['hedgehog_light'],
    packages=['hedgehog_light', 'hedgehog_light.stm32flasher'],
    install_requires=['pyserial>=2.7'],
    scripts=['bin/stm32flasher.sh'],
)


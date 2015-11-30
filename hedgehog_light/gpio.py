def _pin_file(pin, file):
    """
    Returns the file path, specific to the Orange PI/gpio-sunxi kernel module,
    that corresponds to the given pin and function.
    The validity of the arguments is not checked.

    :param pin: a pin name such as `'PA0'`
    :param file: a file name such as `'data'`
    :return: the absolute path of the specified file
    """
    return '/sys/class/gpio_sw/%s/%s' % (pin, file)


def _write(file, value):
    """
    Performs a single write to the given file.

    :param file: the file name
    :param value: the string value to write
    """
    with open(file, 'w') as fd:
        fd.write(value)


def _read(file):
    """
    Reads the given file.

    :param file: the file name
    :return: the string content of the file
    """
    with open(file, 'r') as fd:
        return fd.read()


class GPIO:
    def __init__(self, pin):
        """
        Creates a GPIO object.

        :param pin: a pin name such as `'PA0'`
        """
        self.pin = pin
        self.data_file = _pin_file(pin, 'data')

    def set(self, value):
        """
        Writes the value to the pin's `data` file. The boolean value is
        converted to `'1'`/`'0'`.

        :param value: a boolean value
        """
        _write(self.data_file, '1' if value else '0')

    def get(self):
        """
        Reads the value of the pin's `data` file.

        :return: `True` if the file contains `'1'`, `False` otherwise
        """
        return _read(self.data_file) == '1'

    def write(self, file, value):
        """
        Writes an arbitrary string to one of the pin's files.

        :param file: a file name such as `'data'`
        :param value: the string value for the file
        """
        _write(_pin_file(self.pin, file), value)

    def read(self, file):
        """
        Reads the contents of one of the pin's files.

        :param file: a file name such as `'data'`
        :return: the string content of the file
        """
        return _read(_pin_file(self.pin, file))

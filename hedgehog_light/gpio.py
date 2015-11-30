def _pin_file(pin, file):
    return '/sys/class/gpio_sw/%s/%s' % (pin, file)


def _write(file, value):
    with open(file, 'w') as fd:
        fd.write(str(value))


def _read(file):
    with open(file, 'r') as fd:
        return fd.read()


class GPIO:
    def __init__(self, pin):
        self.pin = pin
        self.data_file = _pin_file(pin, 'data')

    def set(self, value):
        _write(self.data_file, '1' if value else '0')

    def get(self):
        return _read(self.data_file) == '1'

    def write(self, file, value):
        _write(_pin_file(self.pin, file), value)

    def read(self, file):
        return _read(_pin_file(self.pin, file))

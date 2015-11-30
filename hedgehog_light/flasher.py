import serial
import time
from . import gpio

_CONF = {
    'port': serial.device(3),
    'baud': 115200,
    'address': 0x08000000,
    'erase': 0,
    'write': 0,
    'verify': 0,
    'read': 0,
    'go_addr':-1,
    'pin_reset': 'PA8',
    'pin_boot0': 'PA7'
}


class FlasherException(Exception):
    pass


class _FlasherSerial:
    def __init__(self, serial):
        self.serial = serial

    def write(self, data):
        self.serial.write(data)

    def read(self, size=1):
        return self.serial.read(size)

    def write_byte(self, byte):
        self.write(bytes([byte]))

    def read_byte(self):
        result = self.read()
        return None if len(result) == 0 else result[0]

    def await_ack(self, msg=""):
        try:
            ack = self.read_byte()
        except Exception as ex:
            raise FlasherException("Reading `ack` failed") from ex
        else:
            if ack is None:
                raise FlasherException("Receiving `nack` timed out - %s" % (msg,))
            if ack == 0x1F:
                raise FlasherException("Received `nack` - %s" % (msg,))
            elif ack != 0x79:
                raise FlasherException("Unknown response: 0x%02X - %s" % (ack, msg))

    def cmd(self, cmd, msg=None):
        self.write_byte(cmd)
        self.write_byte(cmd ^ 0xFF)
        if msg is None:
            msg = "0x%02X" % (cmd,)
        self.await_ack("cmd %s" % (msg,))


def _with_checksum(data):
    checksum = 0
    for byte in data:
        checksum ^= byte
    return bytes(data) + bytes([checksum])


def _encode_address(addr):
    return _with_checksum([(addr >> i) & 0xFF for i in reversed(range(0, 32, 8))])


class Flasher:
    def __init__(self, conf=None):
        if conf is None:
            conf = _CONF
        self._conf = conf

        self._reset = gpio.GPIO(self._conf['pin_reset'])
        self._boot0 = gpio.GPIO(self._conf['pin_boot0'])
        self._serial = _FlasherSerial(serial.Serial(
            port=self._conf['port'],
            baudrate=self._conf['baud'],
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_ONE,
            timeout=5,
            xonxoff=False,
            rtscts=False,
            writeTimeout=None,
            dsrdtr=False,
            interCharTimeout=None,
        ))

    def reset(self):
        self._reset.set(False)
        time.sleep(0.1)
        self._reset.set(True)
        time.sleep(0.5)

    def init_chip(self):
        self._boot0.set(True)
        self.reset()

        self._serial.serial.flushInput()
        self._serial.serial.flushOutput()

        self._serial.write_byte(0x7F)
        self._serial.await_ack("sync")

    def release_chip(self):
        self._boot0.set(False)
        self.reset()

    def cmd_get(self):
        self._serial.cmd(0x00, "get")
        len = self._serial.read_byte() + 1
        version = self._serial.read_byte()
        cmds = set(self._serial.read(len - 1))
        self._serial.await_ack("end get")
        return version, cmds

    def cmd_get_id(self):
        self._serial.cmd(0x02, "get_id")
        len = self._serial.read_byte() + 1
        bytes = self._serial.read(len)
        id = 0
        for ord, val in enumerate(reversed(bytes)):
            id |= val << (ord*8)
        self._serial.await_ack("end get_id")
        return id

    def cmd_write_memory(self, data, addr):
        length = len(data)
        assert 1 < length <= 0x100
        self._serial.cmd(0x31, "write_memory")
        self._serial.write(_encode_address(addr))
        self._serial.await_ack("write_memory: address")
        self._serial.write(_with_checksum(bytes([length - 1]) + data))
        self._serial.await_ack("end get_id")

    def write_memory(self, data, addr=None):
        if addr is None:
            addr = self._conf['address']
        length = len(data)
        print("Length: 0x%2X" % (length,))
        for off in range(0, length, 256):
            slice_ = data[off:off + 256]
            print("Write data[0x%2X:0x%2X]..." % (off, off + len(slice_)))
            self.cmd_write_memory(slice_, addr + off)

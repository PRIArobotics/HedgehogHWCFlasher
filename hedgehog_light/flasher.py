import serial
import time
from . import gpio


def _checksum(data):
    """
    Calculates the checksum of some data bytes according to the STM32
    bootloader USART protocol.

    :param data: a `bytes` object
    :return: the XOR of all the bytes, i.e. a number between 0x00 and 0xFF
    """
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum


def _with_checksum(data):
    """
    Appends the checksum (see _checksum) to the data and returns it.

    :param data: a `bytes` object
    :return: a new `bytes` object with the checksum appended
    """
    return data + bytes([_checksum(data)])


def _encode_address(addr):
    """
    Returns a `bytes` object consisting of the 4 byte address, MSB first,
    followed by the address' checksum.

    :param addr: The 32 bit address
    :return: a `bytes` object consisting of 5 bytes
    """
    data = bytes([(addr >> i) & 0xFF for i in reversed(range(0, 32, 8))])
    return _with_checksum(data)


class FlasherException(Exception):
    """
    This exception is thrown when the STM32 bootloader USART protocol is not
    followed.
    """
    pass


class _FlasherSerial:
    """
    Encapsulates common functions for the STM32 bootloader USART protocol:
    - Awaiting acknowledgement
    - sending a command, including checksum & acknowledgement
    - wrappers around read & write of the underlying `Serial` object
    """

    def __init__(self, serial_):
        self.serial = serial_

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
        """
        Returns on a successful acknowledgement, otherwise raises a
        `FlasherException`.

        :param msg: A message to be shown in raised errors
        """
        try:
            ack = self.read_byte()
        except Exception as ex:
            raise FlasherException("Reading `ack` failed - %s: %s" % (msg, str(ex))) from ex
        else:
            if ack is None:
                raise FlasherException("Receiving `nack` timed out - %s" % (msg,))
            if ack == 0x1F:
                raise FlasherException("Received `nack` - %s" % (msg,))
            elif ack != 0x79:
                raise FlasherException("Unknown response: 0x%02X - %s" % (ack, msg))

    def cmd(self, cmd, msg=None):
        """
        Sends a command and awaits an acknowledgement.

        :param cmd: The command byte
        :param msg: A message to be shown in raised errors; defaults to `cmd` in hex
        """
        self.write(_with_checksum(bytes([cmd])))
        if msg is None:
            msg = "0x%02X" % (cmd,)
        self.await_ack("cmd %s" % (msg,))


class Flasher:
    def __init__(self,
                 port=serial.device(3),
                 baudrate=115200,
                 reset='PA8',
                 boot0='PA7'):
        self.reset = gpio.GPIO(reset)
        self.boot0 = gpio.GPIO(boot0)
        self.serial = _FlasherSerial(serial.Serial(
            port=port,
            baudrate=baudrate,
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

    def do_reset(self):
        self.reset.set(False)
        time.sleep(0.1)
        self.reset.set(True)
        time.sleep(0.5)

    def init_chip(self):
        self.boot0.set(True)
        self.do_reset()

        self.serial.serial.flushInput()
        self.serial.serial.flushOutput()

        self.serial.write_byte(0x7F)
        self.serial.await_ack("sync")

    def release_chip(self):
        self.boot0.set(False)
        self.do_reset()

    def cmd_get(self):
        self.serial.cmd(0x00, "get")
        length = self.serial.read_byte() + 1
        version = self.serial.read_byte()
        cmds = set(self.serial.read(length - 1))
        self.serial.await_ack("end get")
        return version, cmds

    def cmd_get_id(self):
        self.serial.cmd(0x02, "get_id")
        length = self.serial.read_byte() + 1
        data = self.serial.read(length)
        id_ = 0
        for i, val in enumerate(reversed(data)):
            id_ |= val << (i*8)
        self.serial.await_ack("end get_id")
        return id_

    def cmd_write_memory(self, data, addr):
        length = len(data)
        assert 1 < length <= 0x100
        self.serial.cmd(0x31, "write_memory")
        self.serial.write(_encode_address(addr))
        self.serial.await_ack("write_memory: address")
        self.serial.write(_with_checksum(bytes([length - 1]) + data))
        self.serial.await_ack("end write_memory")

    def write_memory(self, data, addr=0x08000000):
        length = len(data)
        print("Length: 0x%2X" % (length,))
        for off in range(0, length, 256):
            slice_ = data[off:off + 256]
            print("Write data[0x%2X:0x%2X]..." % (off, off + len(slice_)))
            self.cmd_write_memory(slice_, addr + off)

    def cmd_read_memory(self, length, addr):
        assert 1 < length <= 0x100
        self.serial.cmd(0x11, "read_memory")
        self.serial.write(_encode_address(addr))
        self.serial.await_ack("read_memory: address")
        self.serial.write(_with_checksum(bytes([length - 1])))
        self.serial.await_ack("read_memory: length")
        data = self.serial.read(length)
        return data

    def read_memory(self, length, addr=0x08000000):
        fragments = []
        print("Length: 0x%2X" % (length,))
        for off in range(0, length, 256):
            end = min(length, off + 256)
            print("Read data[0x%2X:0x%2X]..." % (off, end))
            fragment = self.cmd_read_memory(end - off, addr + off)
            fragments.append(fragment)
        return b''.join(fragments)

class FlasherSerialException(Exception):
    """
    This exception is thrown when the STM32 bootloader USART protocol is not
    followed.
    """
    pass


class FlasherSerial:
    """
    Encapsulates common functions for the STM32 bootloader USART protocol:
    - Awaiting acknowledgement
    - sending a command, including checksum & acknowledgement
    - wrappers around read & write of the underlying `Serial` object
    """

    def __init__(self, serial):
        self.serial = serial

    @classmethod
    def _checksum(cls, data):
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

    @classmethod
    def with_checksum(cls, data):
        """
        Appends the checksum (see _checksum) to the data and returns it.

        :param data: a `bytes` object
        :return: a new `bytes` object with the checksum appended
        """
        return data + bytes([cls._checksum(data)])

    @classmethod
    def single_checksum(cls, byte):
        """
        Returns a `bytes` object consisting of the data byte and its complement..

        :param byte: a byte
        :return: a new `bytes` object consisting of the data byte and its complement
        """
        return bytes([byte, byte ^ 0xFF])

    @classmethod
    def encode_address(cls, addr):
        """
        Returns a `bytes` object consisting of the 4 byte address, MSB first,
        followed by the address' checksum.

        :param addr: The 32 bit address
        :return: a `bytes` object consisting of 5 bytes
        """
        data = bytes([(addr >> i) & 0xFF for i in reversed(range(0, 32, 8))])
        return cls.with_checksum(data)

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
            raise FlasherSerialException("Reading `ack` failed - %s: %s" % (msg, str(ex))) from ex
        else:
            if ack is None:
                raise FlasherSerialException("Receiving `nack` timed out - %s" % (msg,))
            if ack == 0x1F:
                raise FlasherSerialException("Received `nack` - %s" % (msg,))
            elif ack != 0x79:
                raise FlasherSerialException("Unknown response: 0x%02X - %s" % (ack, msg))

    def cmd(self, cmd, msg=None):
        """
        Sends a command and awaits an acknowledgement.

        :param cmd: The command byte
        :param msg: A message to be shown in raised errors; defaults to `cmd` in hex
        """
        self.write(self.single_checksum(cmd))
        if msg is None:
            msg = "0x%02X" % (cmd,)
        self.await_ack("cmd %s" % (msg,))

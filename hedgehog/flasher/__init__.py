import serial
import time
from .gpio import GPIO
from .flasher_serial import FlasherSerial, FlasherSerialException


class Flasher:
    """
    `Flasher` implements the STM32 bootloader USART protocol.
    See http://www.st.com/web/en/resource/technical/document/application_note/CD00264342.pdf
    The document, and therefore this class, is applicable to the STM32
    microcontroller series: L0, L1, F0, F1, F2, F3, F4

    In addition to the USART protocol, this class also handles setting the
    `RESET` and `BOOT0` pins to enable the bootloader.
    """
    def __init__(self,
                 port=serial.device(3),
                 baudrate=115200,
                 reset='PA8',
                 boot0='PA7'):
        self.reset = GPIO(reset)
        self.boot0 = GPIO(boot0)
        self.serial = FlasherSerial(serial.Serial(
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
        """
        Pulls the `RESET` pin to `0` for 0.1 seconds, then blocks for another
        0.5 seconds.
        """
        self.reset.set(False)
        time.sleep(0.1)
        self.reset.set(True)
        time.sleep(0.5)

    def init_chip(self):
        """
        Pulls the `BOOT0` pin to `1`, does a reset, flushes all data in the
        serial's buffers, and starts the communication by sending the initial
        `0x7F` byte and waiting for acknowledgement.
        """
        self.boot0.set(True)
        self.do_reset()

        self.serial.serial.flushInput()
        self.serial.serial.flushOutput()

        self.serial.write_byte(0x7F)
        self.serial.await_ack("sync")

    def release_chip(self):
        """
        Pulls the `BOOT0` pin to `0`, and does a reset.
        """
        self.boot0.set(False)
        self.do_reset()

    def cmd_get(self):
        """
        0x00 - Get
        Returns the bootloader version, and a set of bytes that are valid commands
        (such as 0x00).

        :return: version, cmds
        """
        self.serial.cmd(0x00, "get")
        length = self.serial.read_byte() + 1
        version = self.serial.read_byte()
        cmds = set(self.serial.read(length - 1))
        self.serial.await_ack("end get")
        return version, cmds

    def cmd_get_version(self):
        """
        0x01 - Get Version & Read Protection Status
        Returns the bootloader version. The Read Protection Status seems not
        to be returned, according to documentation.

        :return: version
        """
        self.serial.cmd(0x01, "get_version")
        version = self.serial.read_byte()
        data = self.serial.read(2)
        assert data[0] == 0x00 and data[1] == 0x00
        self.serial.await_ack("end get_version")
        return version

    def cmd_get_id(self):
        """
        0x02 - Get ID
        Returns the product ID of the device.

        :return: id
        """
        self.serial.cmd(0x02, "get_id")
        length = self.serial.read_byte() + 1
        data = self.serial.read(length)
        pid = 0
        for i, val in enumerate(reversed(data)):
            pid |= val << (i*8)
        self.serial.await_ack("end get_id")
        return pid

    def cmd_read_memory(self, length, addr):
        """
        0x11 - Read Memory
        Reads up to 256 bytes from the specified address. The data are
        returned as a `bytes()` object.

        NOTE: This method will raise an exception if the memory is read protected!
        NOTE: The case of a second NACK for read protection is not handled!

        :param length: the number of bytes to read: 1 < length < 256
        :param addr: the address to read from
        :return: data
        """
        assert 1 < length <= 0x100
        self.serial.cmd(0x11, "read_memory")
        self.serial.write(self.serial.encode_address(addr))
        self.serial.await_ack("read_memory: address")
        self.serial.write(self.serial.single_checksum(length - 1))
        self.serial.await_ack("read_memory: length")
        data = self.serial.read(length)
        return data

    def cmd_go(self, addr=0x08000000):
        """
        0x21 - Go
        Re-Initializes hardware & stack pointer, and jump to the given address.

        NOTE: The address must point to either RAM or Flash!
        NOTE: This method will raise an exception if the memory is read protected!
        NOTE: The case of a second NACK for read protection is not handled!

        :param addr: the address to jump to
        """
        self.serial.cmd(0x21, "go")
        self.serial.write(self.serial.encode_address(addr))
        self.serial.await_ack("go: address")

    def cmd_write_memory(self, data, addr):
        """
        0x31 - Write Memory
        Writes up to 256 bytes to the specified address. The data are
        given as a `bytes()` object.

        NOTE: Writing to write-protected memory is silently ignored!
        NOTE: Writing to Option byte area will generate a system reset!
        NOTE: This method will raise an exception if the memory is read protected!
        NOTE: The case of a second NACK for read protection is not handled!

        :param data: the number of bytes to read: 1 < len(data) < 256
        :param addr: the address to write to
        """
        length = len(data)
        assert 1 < length <= 0x100
        self.serial.cmd(0x31, "write_memory")
        self.serial.write(self.serial.encode_address(addr))
        self.serial.await_ack("write_memory: address")
        self.serial.write(self.serial.with_checksum(bytes([length - 1]) + data))
        self.serial.await_ack("end write_memory")

    def cmd_erase_memory(self, pages=None):
        """
        0x43 - Erase Memory
        Erases all or up to 255 pages of memory.

        NOTE: Erasing write-protected memory is silently ignored!

        :param pages: `None` for global erase, or a list with 1 <= len(pages) <= 255
        """
        assert pages is None or 1 <= len(pages) <= 0xFF
        self.serial.cmd(0x43, "erase_memory")
        if pages is None:
            self.serial.write(self.serial.with_checksum([0xFF]))
        else:
            self.serial.write(self.serial.with_checksum([len(pages) - 1] + pages))
        self.serial.await_ack("end erase_memory")

    def cmd_extended_erase_memory(self, pages=None, mode='pages'):
        """
        0x44 - Extended Erase Memory
        Erases specified pages of memory, or mass erases memory banks.

        NOTE: Erasing write-protected memory is silently ignored!
        NOTE: The maximum number of pages to delete is device dependent!

        :param pages: `None` for special erase, or a list with 1 <= len(pages)
        :param mode: 'pages' to erase specified pages
                     'global' for global mass erase
                     'bank_1' for bank 1 mass erase
                     'bank_2' for bank 2 mass erase
        """
        def encode_page(page):
            return bytes([(page >> i) & 0xFF for i in reversed(range(0, 16, 8))])

        codes = {
            'pages': -1,
            'global': 0xFFFF,
            'bank_1': 0xFFFE,
            'bank_2': 0xFFFD,
        }
        assert mode in codes
        code = codes[mode]
        assert (code == -1) == (pages is not None)
        assert pages is None or 1 <= len(pages) <= 0xFFF0
        self.serial.cmd(0x44, "extended_erase_memory")
        if code == -1:
            data = b''.join([encode_page(page)
                             for page in [len(pages) - 1] + pages])
            self.serial.write(self.serial.with_checksum(data))
        else:
            self.serial.write(self.serial.with_checksum(encode_page(code)))
        self.serial.await_ack("end extended_erase_memory")

    def read_memory(self, length, addr=0x08000000):
        """
        Reads data from the specified address as a `bytes()` object.
        This uses multiple 0x11 - Read Memory commands to read more than 256
        bytes.

        NOTE: This method will raise an exception if the memory is read protected!
        NOTE: The case of a second NACK for read protection is not handled!

        :param length: the number of bytes to read: 1 < length
        :param addr: the address to read from
        :return: data
        """
        fragments = []
        print("Length: 0x%2X" % (length,))
        for off in range(0, length, 256):
            end = min(length, off + 256)
            print("Read data[0x%04X:0x%04X]..." % (off, end))
            fragment = self.cmd_read_memory(end - off, addr + off)
            fragments.append(fragment)
        return b''.join(fragments)

    def write_memory(self, data, addr=0x08000000):
        """
        Writes data in the form of a `bytes()` object to the specified address.
        This uses multiple 0x31 - Write Memory commands to write more than 256
        bytes.

        NOTE: Writing to write-protected memory is silently ignored!
        NOTE: Writing to Option byte area will generate a system reset! This
              means subsequent write commands issued by this method will not
              succeed, and generally result in unexpected behavior!
        NOTE: This method will raise an exception if the memory is read protected!
        NOTE: The case of a second NACK for read protection is not handled!

        :param data: the number of bytes to read: 1 < len(data) < 256
        :param addr: the address to write to
        """
        length = len(data)
        print("Length: 0x%2X" % (length,))
        for off in range(0, length, 256):
            slice_ = data[off:off + 256]
            print("Write data[0x%04X:0x%04X]..." % (off, off + len(slice_)))
            self.cmd_write_memory(slice_, addr + off)


def main():
    import sys

    argv = sys.argv[1:]

    flasher = Flasher()
    try:
        flasher.init_chip()
        version, cmds = flasher.cmd_get()
        id_ = flasher.cmd_get_id()

        print("Bootloader version:", hex(version))
        print("Commands:", [hex(cmd) for cmd in cmds])
        print("Extended erase:", 0x44 in cmds)
        print("ID:", hex(id_))

        bin_ = open(argv[0], 'rb').read()

        flasher.cmd_extended_erase_memory(mode='global')
        flasher.write_memory(bin_)
        verify = flasher.read_memory(len(bin_))
        if bin_ != verify:
            raise FlasherSerialException('Verify failed')
    finally:
        flasher.release_chip()


if __name__ == '__main__':
    main()

import sys
from hedgehog_light.flasher import Flasher, FlasherException

if __name__ == "__main__":
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
            raise FlasherException('Verify failed')
    finally:
        flasher.release_chip()

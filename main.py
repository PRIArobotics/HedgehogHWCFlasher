import sys
from hedgehog_light.flasher import Flasher

if __name__ == "__main__":
    argv = sys.argv[1:]

    flasher = Flasher()
    try:
        flasher.init_chip()
        version, cmds = flasher.cmd_get()
        id = flasher.cmd_get_id()

        print("Bootloader version:", hex(version))
        print("Commands:", [hex(cmd) for cmd in cmds])
        print("Extended erase:", 0x44 in cmds)
        print("ID:", hex(id))

        bin = open(argv[0], 'rb').read()
        flasher.write_memory(bin)
    finally:
        flasher.release_chip()

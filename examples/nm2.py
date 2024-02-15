
import sys
sys.path.insert(0, './../src/')
from packet_handler import TCPhandler
import numpy as np


tcp = TCPhandler()

# Toggle reset ASIC pin from system
tcp.writeSysReg(0xFFA0, 0, 1)
data = tcp.getSystemReadBack(200)

tcp.writeSysReg(0xFFA0, 1, 1)
data = tcp.getSystemReadBack(200)


# Enable ASIC SPI
tcp.writeAsicSpiRegister(0xFA00, 1, 8, 5)
data = tcp.getSystemReadBack(200)
print(f'SPI Reg 0: {data}')

tcp.writeAsicSpiRegister( 0xFA01, 1, 8, 26)
data = tcp.getSystemReadBack(200)
print(f'SPI Reg 1: {data}')

# Program ASIC analog outputs high...
tcp.writeAsicSpiRegister(0x00CD, 1, 8, 3)
data = tcp.getSystemReadBack(200)

tcp.writeAsicSpiRegister(0x00CE, 1, 8, 255)
data = tcp.getSystemReadBack(200)

tcp.writeAsicSpiRegister(0x00CF, 1, 8, 3)
data = tcp.getSystemReadBack(200)

tcp.writeAsicSpiRegister(0x00D0, 1, 8, 255)
data = tcp.getSystemReadBack(200)
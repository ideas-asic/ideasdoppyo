
import sys, os
sys.path.append('.\\..\\src\\ideasdoppyo')
from tcphandler import TCPhandler

tcp = TCPhandler()

# Toggle reset ASIC pin from system
tcp.writeSysReg(0xFFA0, 0, 1)
data = tcp.getSystemReadBack(200)

tcp.writeSysReg(0xFFA0, 1, 1)
data = tcp.getSystemReadBack(200)


# Enable ASIC SPI
tcp.writeAsicSpiRegister(0xFA00, 1, 8, 5)
data = tcp.getSystemReadBack(200)

tcp.writeAsicSpiRegister( 0xFA01, 1, 8, 26)
data = tcp.getSystemReadBack(200)

# Program ASIC analog outputs high...
tcp.writeAsicSpiRegister(0x00CD, 1, 8, 3)
data = tcp.getSystemReadBack(200)

tcp.writeAsicSpiRegister(0x00CE, 1, 8, 255)
data = tcp.getSystemReadBack(200)

tcp.writeAsicSpiRegister(0x00CF, 1, 8, 3)
data = tcp.getSystemReadBack(200)

tcp.writeAsicSpiRegister(0x00D0, 1, 8, 255)
data = tcp.getSystemReadBack(200)
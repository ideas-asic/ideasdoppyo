
import sys
sys.path.insert(0, './../src/')
from packet_handler import TCPhandler
import numpy as np


tcp = TCPhandler()

tcp.setSpiFormat(spi_format=2)

tcp.writeSysReg(0xFFA0, 0, 1)
data = tcp.getSystemReadBack(200)
print(f'Data: {data}')


tcp.writeSysReg(0xFFA0, 1, 1)
data = tcp.getSystemReadBack(200)
print(f'Data: {data}')


SPI_REG0 = 0xFA00
SPI_REG1 = 0xFA01

SPI_REG0_SYS_CLK_ENABLE	=	1
SPI_REG0_SEQ_RESET		=	0
SPI_REG0_SEQ_HALT		=	1
SPI_REG0_RESERVED		=	0

tcp.writeAsicSpiRegister(SPI_REG0, 1, 5, 5)
data = tcp.getSystemReadBack(200)
print(f'SPI Reg 0: {data}')

tcp.readAsicSpiExRegister(SPI_REG0, 5)
data = tcp.getSystemReadBack(200)
print(f'SPI Reg 0: {data}')

SPI_REG1_CLK_DIV_MODE	=	2
SPI_REG1_SYSCLK_DLY		=	2
SPI_REG1_PLL_ENABLE		=	1
SPI_REG1_RESERVED		=	0

tcp.writeAsicSpiRegister(SPI_REG1, 1, 7, 26)
data = tcp.getSystemReadBack(200)
print(f'SPI Reg 1: {data}')

tcp.readAsicSpiExRegister(SPI_REG1, 7)
data = tcp.getSystemReadBack(200)
print(f'SPI Reg 1: {data}')

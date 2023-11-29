
import sys
sys.path.insert(0, './../src/')
from packet_handler import TCPhandler
import numpy as np


tcp = TCPhandler()

tcp.readSysReg(0x0000)
data = tcp.getSystemReadBack(200)
print(data)
tcp.readSysReg(0x0001)
data = tcp.getSystemReadBack(200)
print(data)
tcp.readSysReg(0x0002)

data = tcp.getSystemReadBack(200)
print(data)

tcp.readSysReg(0x040)
data = tcp.getSystemReadBack(200)
print(f'SPI option: {data}')

SPI_REG0 = '0xFA00'
SPI_REG1 = '0xFA01'

SPI_REG0_SYS_CLK_ENABLE	=	1
SPI_REG0_SEQ_RESET		=	0
SPI_REG0_SEQ_HALT		=	1
SPI_REG0_RESERVED		=	0



SPI_REG1_CLK_DIV_MODE	=	2
SPI_REG1_SYSCLK_DLY		=	2
SPI_REG1_PLL_ENABLE		=	1
SPI_REG1_RESERVED		=	0

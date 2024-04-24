
"""
Copyright 2024 Integrated Detector Electronics AS, Norway.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.
   
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys, os
sys.path.append('.\\..\\src\\ideasdoppyo')
from tcphandler import TCPhandler

tcp = TCPhandler()
#tcp.setAutoReadBack(True)
tcp.doPrint = False

print(f'Reset + SPI registers: ', end=' ')
# Toggle reset ASIC pin from system
tcp.writeSysReg(reg_addr=0xFFA0, value=0, len_reg_data=1)
data = tcp.getSystemReadBack(len_reg_data=1)
tcp.writeSysReg(reg_addr=0xFFA0, value=1, len_reg_data=1)
data = tcp.getSystemReadBack(len_reg_data=1)

tcp.writeSysReg(reg_addr=0x0C01, value=4, len_reg_data=1)
data = tcp.getSystemReadBack(len_reg_data=1)
tcp.writeSysReg(reg_addr=0xF017, value=0, len_reg_data=4)
data = tcp.getSystemReadBack(len_reg_data=4)
print('done')

# Enable ASIC SPI
tcp.writeAsicSpiRegister(reg_addr=0xFA00, reg_length=1, asic_bit_length=8, write_data=5)
data = tcp.getASICSPIReadBack(len_reg_data=1)
tcp.writeAsicSpiRegister(reg_addr=0xFA01, reg_length=1, asic_bit_length=8, write_data=26)
data = tcp.getASICSPIReadBack(len_reg_data=1)

wrongly_programmed = tcp.checkReadBack()
print(wrongly_programmed, end= ' ')

print(f'Programming instruction RAM:', end=' ')
tcp.setAutoReadBack(True)
for i in range(8192, 8594):
   tcp.writeAsicSpiRegister(reg_addr=i, reg_length=1, asic_bit_length=8, write_data=3)
tcp.finishReadBack(len_reg_data=1)
wrongly_programmed = tcp.checkReadBack()
print(wrongly_programmed, end=' ')
print('done')

#tx_ch7_0_rst 39 0027 7:0 0 w/pulse Reset Channel 0->7 / Channel independent / Puls
print(f'Programming pulse register. Wrongly programmed:', end=' ')
tcp.writeAsicSpiRegister(reg_addr=0x0027, reg_length=1, asic_bit_length=8, write_data=1)
data = tcp.getASICSPIReadBack(len_reg_data=1)
wrongly_programmed = tcp.checkReadBack()
print(wrongly_programmed, end=' ')
print('done')

tcp.socketClose()

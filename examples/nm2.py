
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
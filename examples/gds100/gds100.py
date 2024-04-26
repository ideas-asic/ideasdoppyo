
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
sys.path.append('.\\..\\..\\src\\ideasdoppyo')
from tcphandler import TCPhandler

tcp = TCPhandler()

# Your socket connection
print(tcp.tcp_s)
tcp.tcp_s.settimeout(2.0)


# Write and read system register
MARES_addr = 0x0F08
enable_addr = 0x0F00

tcp.writeSysReg(enable_addr, 15, 1)
tcp.getSysReadBack(1)

# Write and read ASIC shift register
# Default configuration.
shift_reg = '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003ffffffffffffffffffffffffffffffff000000000000000000000000000000003aaaaba66aa69d99aaaaaaa9aa6a655555555555544040000d01c040434040007713a7eff3bbbde85eae195710c0cefebaa59540433f3ed9ada4fd5dab5925d92000021151164589aa6a9598999998959995a9969999aaa694a80214101310111bf9b48c176190b0116f2cdab49e7e19b6fd0eac5adf449eed62f7b25eeb4794c008000000001fca1fe000000000000000008000000'

shift_reg_bytes = int(shift_reg, 16).to_bytes(int(len(shift_reg)/2), 'big')

tcp.writeReadShiftReg(shift_reg_bytes)
data = tcp.getShiftRegReadBack(100)
tcp.socketClose()

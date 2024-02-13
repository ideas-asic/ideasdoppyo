
import sys
import os
sys.path.insert(0, './../src/ideasdoppyo/')
from packet_handler import TCPhandler

tcp = TCPhandler()

# Your socket connection
print(tcp.tcp_s)
tcp.tcp_s.settimeout(2.0)


# Write and read system register
MARES_addr = 0x0F08
enable_addr = 0x0F00
tcp.writeSysReg(address=enable_addr, value=15, data_length=1)
tcp.getSystemReadBack(200)

# Write and read ASIC shift register
# Default configuration.
shift_reg = '0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003ffffffffffffffffffffffffffffffff000000000000000000000000000000003aaaaba66aa69d99aaaaaaa9aa6a655555555555544040000d01c040434040007713a7eff3bbbde85eae195710c0cefebaa59540433f3ed9ada4fd5dab5925d92000021151164589aa6a9598999998959995a9969999aaa694a80214101310111bf9b48c176190b0116f2cdab49e7e19b6fd0eac5adf449eed62f7b25eeb4794c008000000001fca1fe000000000000000008000000'

shift_reg_bytes = int(shift_reg, 16).to_bytes(int(len(shift_reg)/2), 'big')

tcp.writeReadShiftRegister(shift_reg_bytes)
data = tcp.getSystemReadBack(2000)
tcp.socketClose()

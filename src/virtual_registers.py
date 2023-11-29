
"""
The two main classes in the virtual_registers module are meant to:
Read and store information about the registers, i.e., hold information about
addresses, default values, bitfields etc. The register itself is stored in
RegisterDefinition. This is the parent class to RegisterHandler, so the
RegisterHandler inherites the register from RegisterDefinition. 
"""

import pandas as pd

class RegisterDefinition():
    def __init__(self, filename):
        self.filename = filename
        self.__dict__ = ...

    ... # Property?
    def readjson(self):
        ...


class RegisterHandler(RegisterDefinition):
    """
    ...
    """
    ...
    def __init__(self):
        ...
        
    def setAsicSpiBitFieldByAddr(self, reg_addr, bit_addr, bit_value, asic_id: int=0, system_id: int=0):
        """
        Set a SPI Register Bit Field Local Value.
        
        Args:
            reg_addr: ASIC SPI address.
            bit_addr: Bit field address in SPI register
            bit_value: 
            asic_id: ...
            system_id: ...
        """


if __name__ == '__main__':
    print('Running virtual_registers.py directly.')
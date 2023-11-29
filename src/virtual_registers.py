
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
    def readcsv(self):
        ...


class RegisterHandler(RegisterDefinition):
    """
    ...
    """
    ...
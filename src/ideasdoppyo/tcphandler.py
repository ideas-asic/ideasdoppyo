

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

"""
Sends and receives TCP packets to IDEAS Doppio.
For TCP, the hardware is configured as the network server, with the PC as client.
"""

import numpy as np
import socket
import binascii
import time


class TCPhandler:
    """
    server_ip: IP on the hardware side.
    """
    def __init__(self, server_ip: str="10.10.0.50", port: int=50010):

        # Setup of socket
        self.server_ip = server_ip
        self.port = port
        tcp_s = socket.socket()
        tcp_s.connect((self.server_ip, self.port))
        tcp_s.settimeout(3.0)
        self.tcp_s = tcp_s

        # General variables for all ASICs and systems
        self.asic_id = int(0).to_bytes(1, 'big')

        # For SPI transactions
        self.version = '{0:03b}'.format(0)
        self.system_number = '{0:05b}'.format(0)
        self.sequence_flag = '{0:02b}'.format(0)
        self.packet_count = '{0:014b}'.format(0)
        self.reserved = '{0:032b}'.format(0)
        self.spi_format = int(2).to_bytes(1, 'big')         # System level SPI format.

        # Printer instance
        self.doPrint = True
        self.doPrintFormat = 1
        self.doPrinter = doPrinter(self.doPrintFormat)

        # TCP ReadBack
        self.spare_bytes = b''
        self.auto_readback = [False, 50]
        self.not_readback = {}                              # packet_count: ((package meta data length, data length), (address, value))
        self.now_readback = []

        # Length of header + metadata in readback packets
        self._0x12_METADATA_LENGTH = 10 + 2 + 1 
        self._0xC4_METADATA_LENGTH = 10 + 1 + 1 + 2 + 2

    def setSequenceFlag(self, value: int):
        """
        Change sequence_flag.

        '00': Standalone, '01': First packet, '10': Continuation Packet, '11': Last packet.
        """
        options = ['00', '01', '10', '11']
        sequence_flag = '{0:02b}'.format(value)
        assert (sequence_flag in options), f"sequence_flag should be 0, 1, 2 or 3"
        self.sequence_flag = sequence_flag

    def setSpiFormat(self, spi_format: int) -> None:
        """
        Change system SPI mode.

        Note that the system SPI format may be different than its containing ASIC SPI mode.
        For IDEAS Doppio based systems, use spi_format = 2.

        Args:
            spi_format: System SPI mode.
        """
        self.spi_format = int(spi_format).to_bytes(1, 'big')
        if self.doPrint:
            print(f'spi_format set to {self.spi_format}')

    def setdoPrintFormat(self, doPrint_format: int) -> None:
        """
        Change the doPrintFormat. Updates doPrinter object.

        Args:
            format: See doPrinter class for available formats.
        """
        self.doPrintFormat = doPrint_format
        self.doPrinter = doPrinter(self.doPrintFormat)

    def setAutoReadBack(self, enable: bool) -> None:
        """Performes readback automatically after TCP write."""
        self.auto_readback[0] = enable

    def socketClose(self) -> None:
        """Closes TCP socket."""
        self.tcp_s.close()

    def checkReadBack(self) -> list:
        """
        Compares write dictionary (not_readback) with read back dictionary (now_readback). 
        
        Returns:
            wrongly_programmed: Addresses. Note: The address may be a pulse register!
        """
        wrongly_programmed = []
        not_readback_addr_val = [a[1] for a in self.not_readback.values()]
        if len(self.now_readback) == len(not_readback_addr_val):
            if self.now_readback == not_readback_addr_val:
                if self.doPrint:
                    print(f'Readback is as expected!')
            else:
                for i, j in zip(self.now_readback, not_readback_addr_val):
                    if i != j:
                        wrongly_programmed.append(j[0])
                        if self.doPrint:
                            print(f'ERROR: Readback is wrong!: {j[0]}')
        if self.doPrint:
            print(f'Clearing now_readback and not_readback.')
        self.now_readback = []
        self.not_readback = {}
        wrongly_programmed = [hex(val) for val in wrongly_programmed]
        return wrongly_programmed
    
    def finishReadBack(self, len_reg_data: int) -> list:
        """
        Reads back packages not currently read back.

        To be used after 'fast readout' (auto_readback[0]=True).
        """
        to_be_read_back = len([a[1] for a in self.not_readback.values()]) - len(self.now_readback)
        for _ in range(to_be_read_back):
            self.getAsicSpiReadBack(len_reg_data)
        self.auto_readback = [False, 50]                # Resets auto_readback


    def _packetCountIncrement(self) -> None:
        """Updates packet_count by 1."""
        self.packet_count = '{0:014b}'.format(int(self.packet_count, 2) + 1)[:-14]

    def _getPacketHeader(self, packet_type: hex, len_reg_data: hex) -> bytes:
        """
        Constructs packet header based on function.

        Args:
            packet_type: Defines how the packet data field should be decoded.
            len_reg_data: Number of bytes proceeding header.
        """
        packet_type_bin = '{0:08b}'.format(packet_type)
        data_length_bin = '{0:016b}'.format(len_reg_data)
        packet_header = self.version + self.system_number + packet_type_bin + self.sequence_flag + self.packet_count + self.reserved + data_length_bin
        packet_header_10 = int(packet_header, 2).to_bytes(10, 'big')
        expected_packet_length = 3+5+8+2+14+32+16
        if len(packet_header) != expected_packet_length:
            # TODO Raise error
            print(f"Packet header size isn't of correct size... Now length was {len(packet_header)}, but it should be {expected_packet_length}.")
        return packet_header_10

    def _commonReadBack(self, expected_data_length: int) -> bytes:
        """
        Internal function called by getSystemReadBack and getASICSPIReadBack. 
        """
        data = self.spare_bytes
        while len(data) < expected_data_length:
            data += self.tcp_s.recv(1)
        spare_bytes_length = len(data) - expected_data_length
        self.spare_bytes = data[-spare_bytes_length:] if spare_bytes_length != 0 else b''
        return_data = data[:-spare_bytes_length or None]
        if self.doPrint:
            self.doPrinter.data_bytes = return_data     # If no spare: Full array is used.
            print(self.doPrinter)
        if return_data[1] == 18: self.now_readback.append((int.from_bytes(return_data[10:12], byteorder='big'), int.from_bytes(return_data[13:], byteorder='big')))
        elif return_data[1] == 196: self.now_readback.append((int.from_bytes(return_data[12:14], byteorder='big'), int.from_bytes(return_data[16:], byteorder='big')))
        else: print(f'Unknown readback..')
        return return_data

    def writeSysReg(self, reg_addr: hex, value: hex, len_reg_data: hex) -> bool:
        """
        Writes system register value. Packet type 0x10.

        Args:
            reg_addr: System register address.
            value: Value to be written.
            len_reg_data: Byte length of system register.

        Returns:
            return_val: Verification that the address and value is correctly written.
        """
        PACKET_TYPE = 0x10
        packet_data_length = 3 + len_reg_data
        packet_header_array = self._getPacketHeader(packet_type=PACKET_TYPE, len_reg_data=packet_data_length)
        reg_addr_bytes = reg_addr.to_bytes(2, 'big')
        reg_length_bytes = len_reg_data.to_bytes(1, 'big')
        data_bytes = value.to_bytes(len_reg_data, 'big')
        data_field = reg_addr_bytes + reg_length_bytes + data_bytes
        write_packet = packet_header_array + data_field
        self.tcp_s.sendall(write_packet)
        if self.doPrint:
            self.doPrinter.data_bytes = write_packet
            print(self.doPrinter)
        self.not_readback[self.packet_count] = ((self._0x12_METADATA_LENGTH, len_reg_data), (reg_addr, value))
        self._packetCountIncrement()    

    def readSysReg(self, reg_addr: hex) -> None:
        """
        Reads system register value. Packet type 0x11.

        Args:
            reg_addr: System register address.
        """
        PACKET_TYPE = 0x11
        DATA_LENGTH = 0x02
        packet_header = self._getPacketHeader(PACKET_TYPE, DATA_LENGTH)
        reg_addr_bytes = reg_addr.to_bytes(2, 'big')
        write_packet = packet_header + reg_addr_bytes
        self.tcp_s.sendall(write_packet)
        if self.doPrint:
            self.doPrinter.data_bytes = write_packet
            print(self.doPrinter)
        self.not_readback[self.packet_count] = ((self._0x12_METADATA_LENGTH, ...), (reg_addr, None))        # TODO: To be reviewed
        self._packetCountIncrement()

    def getSysReadBack(self, len_reg_data: int) -> bytes:
        """
        Response packet from system to system write/reads. Packet type 0x12.

        Args:
            reg_length: Byte length of system register.
        """
        expected_data_length = self._0x12_METADATA_LENGTH + len_reg_data
        data = self._commonReadBack(expected_data_length)     
        return data

    def writeReadShiftReg(self, configuration_data: bytes) -> None:
        """
        Write/read ASICs with shift registers. Packet type 0xC0.

        Args:
            configuration_data: Shift-in data.
        """
        PACKET_TYPE = 0xC0
        len_reg_data = 3 + len(configuration_data)
        packet_header = self._getPacketHeader(PACKET_TYPE, len_reg_data)
        conf_len = len(configuration_data)          # Byte-length of configuration register
        conf_bit_len = (conf_len*8-(8-conf_len%8)).to_bytes(2, 'big')
        data_packet = self.asic_id + conf_bit_len + configuration_data
        write_packet = packet_header + data_packet
        self.tcp_s.sendall(write_packet)
        if self.doPrint:
            self.doPrinter.data_bytes = write_packet
            print(self.doPrinter)
        self._packetCountIncrement()

    def getShiftRegReadBack(self, len_reg_data: int) -> bytes:
        """
        Response packet from system to ASIC shift register write/read. Packet type 0xC1.

        Args:
            len_reg_data: Byte length of shift register.
        """
        expected_data_length = 10 + 1 + 2 + len_reg_data
        data = self._commonReadBack(expected_data_length)
        return data

    def writeAsicSpiReg(self, reg_addr: hex, reg_length: int, asic_bit_length: int, write_data: hex) -> None:
        """
        Write ASIC SPI register. Packet type 0xC2.

        Args:
            reg_addr: SPI register address.
            reg_length: Byte length of SPI register.
            asic_bit_length: Number of bit in SPI register.
            write_data: Data to write.
        """
        PACKET_TYPE = 0xC2
        len_reg_data = 6 + reg_length
        packet_header = self._getPacketHeader(PACKET_TYPE, len_reg_data)
        reg_addr_bytes = reg_addr.to_bytes(2, 'big')
        asic_bit_length_bytes = asic_bit_length.to_bytes(2, 'big')
        data_bytes = write_data.to_bytes(1, 'big')            # TODO: Not constant
        data_packet = self.asic_id + self.spi_format + reg_addr_bytes + asic_bit_length_bytes + data_bytes
        write_packet = packet_header + data_packet
        if self.doPrint:
            self.doPrinter.data_bytes = write_packet
            print(self.doPrinter)
        self.tcp_s.sendall(write_packet)
        self.not_readback[self.packet_count] = ((self._0xC4_METADATA_LENGTH, reg_length), (reg_addr, write_data))
        if self.auto_readback[0]:
            self.auto_readback[1] -= 1
            if self.auto_readback[1] == 0:
                self.to_be_read_back = 50
                for _ in range(50):
                    self.getAsicSpiReadBack(reg_length)
                self.auto_readback[1] = 50
        self._packetCountIncrement()

    def readAsicSpiReg(self, reg_addr: hex, reg_bit_length: int) -> None:
        """
        Read ASIC SPI Register. Packet type 0xC3.

        Args:
            reg_addr: SPI register address.
            reg_bit_length: Number of bits in SPI register.
        """
        PACKET_TYPE = 0xC3
        DATA_LENGTH = 6
        packet_header = self._getPacketHeader(PACKET_TYPE, DATA_LENGTH)
        reg_addr_bytes = reg_addr.to_bytes(2, 'big')
        reg_bit_length = reg_bit_length.to_bytes(2, 'big')
        data_packet = self.asic_id + self.spi_format + reg_addr_bytes + reg_bit_length
        write_packet = packet_header + data_packet
        self.tcp_s.sendall(write_packet)
        if self.doPrint:
            self.doPrinter.data_bytes = write_packet
            print(self.doPrinter)
        self._packetCountIncrement()

    def getAsicSpiReadBack(self, len_reg_data) -> bytes:
        """
        Response packet from system to ASIC SPI write/reads. Packet type 0xC4.

        Args:
            len_reg_data: Register length for ASIC register.
        """
        expected_data_length = self._0xC4_METADATA_LENGTH + len_reg_data
        data = self._commonReadBack(expected_data_length)
        return data


class doPrinter:
    """
    Formats printing of TCPhandler object.

    NOTE only active if doPrint = True (for TCPhandler object). Similarly select doPrintFormat there.
    """
    def __init__(self, doPrintFormat):
        self.data_bytes = None

        self.doPrintFormat = doPrintFormat

        self.printString_packet_type = {
            0x10: "Sent: Write System Register,         ",
            0x11: "Sent: Read System Register,          ",
            0x12: "Recv: System Register Read-Back,     ",
            0xC0: "Sent: Write Shift Register,          ",
            0xC1: "Recv: ASIC Shift Register Read-Back, ",
            0xC2: "Sent: ASIC SPI Register Write,       ",
            0xC3: "Sent: ASIC SPI Register Read,        ",
            0xC4: "Recv: ASIC SPI Register Read-Back,   "
        }

    def __str__(self) -> str:
        """Prints according to selected doPrintFormat."""
        doPrintFunctions = {
            # Key: doPrintFormat
            1: self.default_doPrintFormat(),
            2: self.uint8_doPrintFormat(),
            3: ...                                  # Please add issue to github repo if you wish another print format.
        }
        printString = doPrintFunctions[self.doPrintFormat]
        return printString

    def default_doPrintFormat(self) -> str:
        """
        Examples:
            Send: Write system register,  Reg: 0xFFA0 - Val: 1
            Recv: Read system register, Reg: 0xFA01 - Val: 1A
        """
        packet_type = self.data_bytes[1]
        string_packet_type = self.printString_packet_type[packet_type]
        
        if packet_type in [0x10, 0x12]:
            reg_addr = binascii.hexlify(self.data_bytes[10:12]).decode('utf-8').upper()
            value = ' '.join([hex(i)[2:] for i in self.data_bytes[13:]]).upper()
            printString = f'{string_packet_type} Addr: {reg_addr} - Val: {value}'

        elif packet_type in [0x11]:
            reg_addr = binascii.hexlify(self.data_bytes[10:12]).decode('utf-8').upper()
            printString = f'{string_packet_type} Addr: {reg_addr}'
        
        elif packet_type in [0xC0, 0xC1]:
            value = ' '.join([hex(i)[2:] for i in self.data_bytes[13:]]).upper()
            printString = f'{string_packet_type} Val: {value}'
        
        elif packet_type in [0xC3]:
            reg_addr = binascii.hexlify(self.data_bytes[12:14]).decode('utf-8').upper()
            printString = f'{string_packet_type} Addr: {reg_addr}'
        
        elif packet_type in [0xC2, 0xC4]:
            reg_addr = binascii.hexlify(self.data_bytes[12:14]).decode('utf-8').upper()
            value = ' '.join([hex(i)[2:] for i in self.data_bytes[16:]]).upper()
            printString = f'{string_packet_type} Addr: {reg_addr} - Val: {value}'
        
        else:
            printString = 'ERROR! NO VALID PACKET TYPE DETECTED..!'        

        return printString

    def uint8_doPrintFormat(self):
        """
        Examples:
            [0, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # FIXME
        """
        printString = np.frombuffer(self.data_bytes, np.uint8)
        return str(printString)


"""
Sends and receives TCP packets to IDEAS Doppio.
For TCP, the readout PC is configured as client with the hardware as the network server.
For UDP, the hardware is configured as network server with the hardware as client.
"""

import numpy as np
import socket
import binascii


class TCPhandler:
    def __init__(self, server_ip: str="10.10.0.50", port: int=50010):
        
        # Setup of socket
        self.server_ip = server_ip
        self.port = port
        tcp_s = socket.socket()
        tcp_s.connect((self.server_ip, self.port))
        tcp_s.settimeout(1.0)
        self.tcp_s = tcp_s

        # General variables for all ASICs and systems
        self.asic_id = int(0).to_bytes(1, 'big')
        
        # For SPI transactions      
        self.version = '{0:03b}'.format(0)
        self.system_number = '{0:05b}'.format(0)
        self.sequencer_flag = '{0:02b}'.format(0)
        self.packet_count = '{0:014b}'.format(0)
        self.reserved = '{0:032b}'.format(0)
        self.spi_format = int(2).to_bytes(1, 'big')

        # printer instance
        self.doPrint = True
        self.doPrintFormat = 1
        self.doPrinter = doPrinter(self.doPrintFormat)


    def setSpiFormat(self, spi_format: int) -> None:
        """
        Updates spi format.
        
        TODO: Is this for ASIC SPI Format or for Doppio SPI format.
        
        Args:
            spi_format: TODO Is it ASIC or Doppio SPI format?
        """
        self.spi_format = int(spi_format).to_bytes(1, 'big')
        if self.doPrint:
            print(f'spi_format set to {self.spi_format}')


    def packet_count_increment(self) -> None:
        """Updates packet_count by 1."""
        self.packet_count = '{0:014b}'.format(int(self.packet_count, 2) + 1)


    def getPacketHeader(self, packet_type: hex, data_length: hex) -> bytes:
        """
        Constructs packet header based on function.

        Args:
            packet_type: Defines how the packet data field should be decoded.
            data_length: Number of bytes proceeding header.
        """
        packet_type_bin = '{0:08b}'.format(packet_type)
        data_length_bin = '{0:016b}'.format(data_length)

        packet_header = self.version + self.system_number + packet_type_bin + self.sequencer_flag + self.packet_count + self.reserved + data_length_bin
        packet_header_10 = int(packet_header, 2).to_bytes(10, 'big')

        expected_packet_length = 3+5+8+2+14+32+16
        if len(packet_header) != expected_packet_length:
            # Raise error
            print(f"Packet header size isn't of correct size... Now length was {len(packet_header)}, but it should be {expected_packet_length}.")       
        return packet_header_10


    def writeSysReg(self, address: hex, value: hex, data_length: hex) -> None:
        """
        Writes system register value.

        Args:
            address: Register map address for the register to be write.
            value: Length of the data to write.
            data_length: Variable length of register data to write.
        """
        PACKET_TYPE = 0x10
        packet_data_length = 3 + data_length
        packet_header_array = self.getPacketHeader(packet_type=PACKET_TYPE, data_length=packet_data_length)
        
        reg_addr_bytes = address.to_bytes(2, 'big')
        reg_length_bytes = data_length.to_bytes(1, 'big')
        data_bytes = value.to_bytes(data_length, 'big')
        data_field = reg_addr_bytes + reg_length_bytes + data_bytes
        
        write_packet = packet_header_array + data_field
        self.tcp_s.sendall(write_packet)
        
        if self.doPrint:
            print(self.doPrinter.commonFunction(write_packet))
        self.packet_count_increment()


    def readSysReg(self, address: hex) -> None:
        """
        Reads system register value.
        
        Args:
            address: System register address.
        """
        PACKET_TYPE = 0x11
        DATA_LENGTH = 0x02
        packet_header = self.getPacketHeader(PACKET_TYPE, DATA_LENGTH)
        address_bytes = address.to_bytes(2, 'big')
        write_packet = packet_header + address_bytes
        self.tcp_s.sendall(write_packet)
        if self.doPrint:
            print(f'Sent: Read System Register, address: {address}')
        self.packet_count_increment()

    
    def getSystemReadBack(self, reg_length: int) -> bytes:
        """
        Use after write or read.

        Received packet with format 0x12.

        Args:
            reg_length: Length of system register in bytes. 
        """
        data = self.tcp_s.recv(reg_length)
        if self.doPrint:
            print(self.doPrinter.commonFunction(data))
        data = np.frombuffer(data, dtype=np.uint8)
        return data


    def writeAsicSpiRegister(self, reg_addr: hex, reg_length: int, asic_bit_length: int, write_data: hex) -> None:
        """
        Write an ASIC SPI register.

        Args:
            reg_addr: SPI register address.
            reg_length: Length of SPI register in bytes.
            asic_bit_length: Number of bit in SPI register.
            write_data: Data to write.
        """
        PACKET_TYPE = 0xC2
        data_length = 6 + reg_length

        packet_header = self.getPacketHeader(PACKET_TYPE, data_length)
        
        reg_addr_bytes = reg_addr.to_bytes(2, 'big')
        asic_bit_length_bytes = asic_bit_length.to_bytes(2, 'big')
        data_bytes = write_data.to_bytes(1, 'big')            # TODO: Not constant
        data_packet = self.asic_id + self.spi_format + reg_addr_bytes + asic_bit_length_bytes + data_bytes

        write_packet = packet_header + data_packet
        if self.doPrint:
            print(self.doPrinter.commonFunction(write_packet))
        self.tcp_s.sendall(write_packet)

        self.packet_count_increment()
        
    
    def readAsicSpiExRegister(self, reg_addr: hex, reg_bit_length: int) -> None:
        """
        Read an ASIC SPI Register.
        
        Args:
            reg_addr: SPI register address.
            reg_bit_length: Number of bit in SPI register.
        """
        PACKET_TYPE = 0xC3
        DATA_LENGTH = 6
        packet_header = self.getPacketHeader(PACKET_TYPE, DATA_LENGTH)

        reg_addr_bytes = reg_addr.to_bytes(2, 'big')
        reg_bit_length = reg_bit_length.to_bytes(2, 'big')

        data_packet = self.asic_id + self.spi_format + reg_addr_bytes + reg_bit_length
        
        write_packet = packet_header + data_packet
        if self.doPrint:
            ...
            #FIXME
            # print(f'READ: Packet header + packet data : {write_packet}')
        self.tcp_s.sendall(write_packet)

        self.packet_count_increment()

    
    def writeReadShiftRegister(self, configuration_data: bytes) -> None:
        """
        Write/read ASICs with shift registers.
        
        Args:
            configuration_data: Shift-in data.
        """
        PACKET_TYPE = 0xC0
        data_length = 3 + len(configuration_data)
        packet_header = self.getPacketHeader(PACKET_TYPE, data_length)
        
        data_packet = self.asic_id + len(configuration_data).to_bytes(2, 'big') + configuration_data

        write_packet = packet_header + data_packet
        if self.doPrint:
            print(self.doPrinter.commonFunction(write_packet))         
        self.tcp_s.sendall(write_packet)
        self.packet_count_increment()

    def socketClose(self):
        self.tcp_s.close()


class UDPhandler:
    def __init__(self, data_format, server_ip="10.10.0.100", port=50011):
        """
        Args:
            data_format: {0: Image data packet, 1: Multi-event pulse height data packet, 2: Single-event pulse height data packet, 3: Trigger Time Data P}
        """
        self.server_ip = server_ip
        self.port = port

        self.doPrint = False

        self.data_format = data_format

        udp_s = socket.socket(type=2)
        udp_s.bind((self.server_ip, self.port))
        udp_s.settimeout(10.)
        self.udp_s = udp_s

    def receiveData(self) -> bytes:
        """
        Receives UDP packets.

        NOTE Only max 1024 bytes that is received.
        """
        data, _ = self.udp_s.recvfrom(1024)
        return data

    def collectNsamples(self, N) -> np.ndarray:
        data_array = np.array([])
        this_index = 0
        while this_index <= N:
            data = self.receiveData()
            data_array = np.concatenate((data_array, data))
            this_index += len(data)
        return data_array



class doPrinter:
    def __init__(self, doPrintFormat):
        self.data_bytes = None

        self.doPrintFormat = doPrintFormat

        self.printString_packet_type = {
            0x10: "Sent: Write System Register,      ",
            0x11: "Sent: Read System Register,       ",
            0x12: "Recv: System Register Read-Back,  ",
            0xC2: "Sent: ASIC SPI Register Write,    ",
            0xC3: "Sent: ASIC SPI Register Read,     ",
            0xC4: "Recv: ASIC SPI Register Read-Back,"     
        }

    def commonFunction(self, data_bytes: bytes):
        self.data_bytes = data_bytes
        doPrintFunctions = {
            # Key: doPrintFormat
            1: self.default_doPrintFormat(),
            2: self.uint8_doPrintFormat(),
            3: ...
        }
        printString = doPrintFunctions[self.doPrintFormat]
        return printString
    
    def default_doPrintFormat(self):
        """
        Examples:
            Send: Write system register,  Reg: 0xFFA0 - Val: 1
            Recv: Read system register, Reg: 0xFA01 - Val: 1A  
        """
        packet_type = self.data_bytes[1]
        string_packet_type = self.printString_packet_type[packet_type]
        if packet_type in [0x10, 0x12]:
            address = binascii.hexlify(self.data_bytes[10:12]).decode('utf-8').upper()
            value = ' '.join([hex(i)[2:] for i in self.data_bytes[13:]]).upper()
        elif packet_type in [0xC2, 0xC4]:
            address = binascii.hexlify(self.data_bytes[12:14]).decode('utf-8').upper()
            value = ' '.join([hex(i)[2:] for i in self.data_bytes[16:]]).upper() 
        else:
            address = value = ...
        printString = f'{string_packet_type} Addr: {address} - Val: {value}' 
        return printString
    
    def uint8_doPrintFormat(self):
        """
        Examples:
            [0, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # FIXME
        """
        printString = np.frombuffer(self.data_bytes, np.uint8)
        return printString




if __name__ == "__main__":    
    # Set up tcp instance
    tcp = TCPhandler("10.10.0.50", 50010)
    print(tcp)
    udp = UDPhandler("10.10.0.100", port=50011)
    print(udp)


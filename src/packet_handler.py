
import numpy as np
import socket


class TCPhandler():
    def __init__(self, server_ip: str="10.10.0.50", port: int=50010):
        self.server_ip = server_ip
        self.port = port
        self.version = '{0:03b}'.format(0)
        self.system_number = '{0:05b}'.format(0)
        self.sequencer_flag = '{0:02b}'.format(0)
        self.packet_count = '{0:014b}'.format(0)
        self.reserved = '{0:032b}'.format(0)

        self.asic_id = int(0).to_bytes(1, 'big')
        self.spi_format = int(2).to_bytes(1, 'big')
        
        # print strings in functions
        self.doPrint = False
        
        # Setup of socket
        tcp_s = socket.socket()
        tcp_s.connect((self.server_ip, self.port))
        self.tcp_s = tcp_s


    def doPrintEnable(self, enable: bool) -> None:
        """Print strings in functions."""
        if enable:
            self.doPrint = True
        else:
            self.doPrint = False


    def setSpiFormat(self, spi_format: int) -> None:
        """Updates spi format."""
        self.spi_format = int(spi_format).to_bytes(1, 'big')
        if self.doPrint:
            print(f'spi_format set to {self.spi_format}')


    def packet_count_increment(self) -> None:
        """Updates packet_count by 1."""
        self.packet_count = '{0:014b}'.format(int(self.packet_count, 2) + 1)


    def getPacketHeader(self, packet_type: hex, data_length: hex) -> np.ndarray:
        """
        Constructs packet header based on function.

        Args:
            version: Version of packet protocol. Fixed 0b000.
            system_number: 
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
        packet_type = 0x10
        packet_data_length = 3 + data_length
        packet_header_array = self.getPacketHeader(packet_type=packet_type, data_length=packet_data_length)
        # print(f'Packet header array: {packet_header_array}')
        
        reg_addr_bytes = address.to_bytes(2, 'big')
        reg_length_bytes = data_length.to_bytes(1, 'big')
        data_bytes = value.to_bytes(data_length, 'big')
        data_field = reg_addr_bytes + reg_length_bytes + data_bytes
        
        write_packet = packet_header_array + data_field
        self.tcp_s.sendall(write_packet)
        if self.doPrint:
            print(f'Write packet: {write_packet}]')
        self.packet_count_increment()


    def readSysReg(self, address: int) -> None:
        """
        Reads system register value.
        """
        packet_type = 0x11
        data_length = 0x02
        packet_header = self.getPacketHeader(packet_type, data_length)
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
            reg_length: Length of system register. 
        """
        data = self.tcp_s.recv(reg_length)
        data = np.frombuffer(data, dtype=np.uint8)
        return data


    def writeAsicSpiRegister(self, reg_addr, reg_length, asic_bit_length, write_data) -> None:
        """
        Write an ASIC SPI register
        """
        packet_type = 0xC2
        data_length = 6 + reg_length

        packet_header = self.getPacketHeader(packet_type, data_length)
        
        reg_addr_bytes = reg_addr.to_bytes(2, 'big')
        asic_bit_length_bytes = asic_bit_length.to_bytes(2, 'big')
        data_bytes = write_data.to_bytes(1, 'big')            # TODO: Not constant
        data_packet = self.asic_id + self.spi_format + reg_addr_bytes + asic_bit_length_bytes + data_bytes

        write_packet = packet_header + data_packet
        if self.doPrint:
            print(f'Packet header + packet data : {write_packet}')
        self.tcp_s.sendall(write_packet)

        self.packet_count_increment()
        
    
    def readAsicSpiExRegister(self, reg_addr: hex, reg_bit_length: int) -> None:
        """
        Read an ASIC SPI Register.
        
        Args:
            reg_addr: ...
            reg_bit_length: ...
        """
        packet_type = 0xC3
        DATA_LENGTH = 6
        packet_header = self.getPacketHeader(packet_type, DATA_LENGTH)

        reg_addr_bytes = reg_addr.to_bytes(2, 'big')
        reg_bit_length = reg_bit_length.to_bytes(2, 'big')

        data_packet = self.asic_id + self.spi_format + reg_addr_bytes + reg_bit_length
        
        write_packet = packet_header + data_packet
        if self.doPrint:
            print(f'READ: Packet header + packet data : {write_packet}')
        self.tcp_s.sendall(write_packet)

        self.packet_count_increment()


if __name__ == "__main__":    
    # Set up tcp instance
    tcp = TCPhandler("10.10.0.50", 50010)
    print(tcp)

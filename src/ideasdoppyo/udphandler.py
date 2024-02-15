
"""
Sends and receives TCP packets to IDEAS Doppio.
For TCP, the hardware is configured as the network server, with the PC as client.
For UDP, the PC is configured as network server, with the hardware as client.
"""

import numpy as np
import socket
import binascii

class UDPhandler:
    """
    server_ip: IP on the PC side.
    """
    def __init__(self, data_format: int, server_ip: str="10.10.0.100", port: int=50011):
        """
        Args:
            data_format: {0: Image, 1: Multi-event pulse height, 2: Single-event pulse height, 3: Trigger Time, 4: Pipeline Sampling}
        """
        self.server_ip = server_ip
        self.port = port

        self.doPrint = False

        self.data_format = data_format
        header_byte_length_dict = {
            0 : 20,
            1 : 3,
            2 : 7,
            3 : 0,
            4 : 14
        }

        # FIXME
        self.mask_common_header = False
        self.header_byte_length  = header_byte_length_dict[data_format]
        if self.mask_common_header:
            self.header_byte_length += 10

        udp_s = socket.socket(type=2)
        udp_s.bind((self.server_ip, self.port))
        udp_s.settimeout(None)
        self.udp_s = udp_s

    def getDataPacketFormat(self):
        ...

    def setTimeout(self, timeout: float):
        """Set timeout on udp."""
        self.udp_s.settimeout(timeout)

    def receiveData(self) -> bytes:
        """
        Receives UDP packets.

        NOTE Only max 1024 bytes that is received.
        """
        data, _ = self.udp_s.recvfrom(1024)
        return data

    def collectNpackets(self, N: int, include_header = True) -> bytes:
        """
        Collects N data samples.

        Each packet must be less than 1024 bytes.
        """
        data_bytes = b''
        packet_counter = 0
        if include_header:
            filter_index = 0
        else:
            filter_index = self.header_byte_length

        while packet_counter <= N:
            data_packet = self.receiveData()[filter_index:]
            data_bytes += data_packet
            packet_counter += 1

        return data_bytes

    def data2csv(self, data_array: np.ndarray, filename: str) -> None:
        """Store captured data to a csv-file."""
        data_array.tofile(filename, sep=';')

    def socketClose(self) -> None:
        """Closes UDP connection."""
        self.udp_s.shutdown(socket.SHUT_RDWR)
        self.udp_s.close()

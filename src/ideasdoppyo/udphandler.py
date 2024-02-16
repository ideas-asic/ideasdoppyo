
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
Receives UDP packets from IDEAS Doppio.
For UDP, the PC is configured as network server, with the hardware as client.
"""

import numpy as np
import socket
import binascii
from dataformats import common_header_format, pipeline_sampling_format

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

        # TODO: change to packet ID to fit with documentation
        self.data_format = data_format
        header_byte_length_dict = {
            0 : 20,
            1 : 3,
            2 : 7,
            3 : 0,
            4 : 14
        }

        self.mask_header = False
        self.mask_common_header = False # Only mask common header

        self.header_byte_length  = header_byte_length_dict[data_format]

        udp_s = socket.socket(type=2)
        udp_s.bind((self.server_ip, self.port))
        udp_s.settimeout(None)
        self.udp_s = udp_s

    def loadDataPacketFormat(self):
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

    def collectNpackets(self, N: int) -> bytes:
        """
        Collects N data samples.

        Each packet must be less than 1024 bytes.
        """
        data_bytes = b''
        packet_counter = 0

        if self.mask_common_header:
            filter_index = 10
        elif self.mask_header:
            filter_index = self.header_byte_length + 10
        else:
            filter_index = 0

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

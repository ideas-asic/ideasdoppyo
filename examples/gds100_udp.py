import sys
import os
import socket
import numpy as np
import pandas as pd
import time

sys.path.append(os.getcwd()+'\\src\\ideasdoppyo')

from packet_handler import UDPhandler

def main():
    udp = UDPhandler(data_format = 2)
    data_string = udp.collectNpackets_GDS100(10)
    print('Data String:')
    print(data_string)
    print('len: ', len(data_string))
    array_type = [('Packet ID', '>u2'),
          ('Packet Sequence', '>u2'),
          ('Timestamp', '>u4'),
          ('Data Length', '>u2'),
          ('Source ID', '>u1'),
          ('Trigger Type', '>u1'),
          ('Status', '>u2'),
          ('ASIC Dout', '>u2'),
          ('Event ID', '>u4'),
          ('PPS Timestamp', '>u4')]

    for i in range(160):
        cell = ('Cell' + str(i), '>u2')
        array_type.append(cell)
    dtype = np.dtype(array_type)
    np_data = np.frombuffer(data_string, dtype)
    df_events = pd.DataFrame(np_data)

    udp.socketClose()


if __name__ == '__main__':
    main()
    #print (recieved)
    #plt.show()

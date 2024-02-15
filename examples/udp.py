import socket
import matplotlib.pyplot as plt
import numpy as np

import sys
sys.path.insert(0, './../src/ideasdoppyo/')
from ideasdoppyo.packet_handler import UDPhandler

def main():
    data_array = udp.collectNpackets(N=1000, include_header=False)
    udp.socketClose()
    return data_array

if __name__ == '__main__':
    udp = UDPhandler(data_format=0)
    try:
        data_array = main()
        flat = np.array(data_array).flatten()
        plt.hist(flat, np.arange(30000, 35000, 1))
        plt.xlabel('ADC[LSB]')
        plt.ylabel('Counts')
        plt.grid()
        plt.show()

        plt.plot(flat[0:10000], '.')
        plt.show()
    
    except KeyboardInterrupt:
        udp.socketClose()
        sys.exit()
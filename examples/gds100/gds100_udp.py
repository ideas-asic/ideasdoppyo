
import socket
import numpy as np
import pandas as pd
import time

import sys, os
sys.path.append('.\\..\\..\\src\\ideasdoppyo')

from udphandler import UDPhandler
from dataformats import pipeline_sampling_format, common_header_format, pipeline_data_format

def GDS100binaryToDataframe(data_string):
    gds100_format = common_header_format + pipeline_sampling_format
    dtype = np.dtype(gds100_format)
    np_data = np.frombuffer(data_string, dtype)
    df_events = pd.DataFrame(np_data)
    print(df_events)

def main():
    # Collect UDP packets
    udp = UDPhandler(data_format = 4)

    try:
        data_string = udp.collectNpackets(10)

    except KeyboardInterrupt:
        udp.socketClose()
        sys.exit()

    # Process data
    GDS100binaryToDataframe(data_string)

if __name__ == '__main__':
    main()

import socket
import numpy as np
import matplotlib.pyplot as plt

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("10.10.0.100", 50011))

    print(f'Started listening for UDP packets ...')

    data_array = []

    #sock.settimeout(10.)
    i=0
    while len(data_array)<1000:
        data, _ = sock.recvfrom(1024)
        #print(data)
        data_array.append(np.frombuffer(data, '>H')[20:])
        i = i+1
        #last_digit.append(np.frombuffer(data, np.uint8)[-1])
        #print(last_digit)
    # except:
    # sock.close()
    return data_array

if __name__ == '__main__':
    data_array = main()
    flat = np.array(data_array).flatten()
    plt.hist(flat, np.arange(20000, 40000, 1))
    plt.xlabel('ADC[LSB]')
    plt.ylabel('Counts')
    plt.grid()
    plt.show()

    plt.plot(flat[0:10000], '.')
    plt.show()
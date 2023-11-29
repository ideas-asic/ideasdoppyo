
import socket

s = socket.socket()

s.connect(("10.10.0.50", 50010))

example_string = b'\x00\x11\x00\x00\x00\x00\x00\x00\x00\x02\x00\x01'            # Read the Serial number register

s.sendall(example_string)

serial_number = s.recv(500)
print(serial_number)

from typing import List
from threading import Thread
import time

from serial import Serial
from serial.tools import list_ports
import cv2

# Get port name from pid
# Arduino nano: 29987
def pid2portname(pid: int, nth_port: int = 0):
    ports = list_ports.comports()
    found_port_names = []
    for port in ports:
        if port.pid == pid: found_port_names.append(port.device)
    return found_port_names[nth_port]


class Ard6S(Serial):
    def __init__(self):
        super().__init__(port=pid2portname(29987, nth_port=0), baudrate=115200)
        print(self.readline())
        print(self.readline())
        self._thread = Thread(target=self.check_runnning)
        self._thread.daemon = True
        self._thread.start()
        self.num_command_queue = 0

    def check_runnning(self):
        while True:
            print(self.readline(), self.num_command_queue)
            self.num_command_queue -= 1

    def is_running(self):
        return self.num_command_queue > 0

    # Send string as binary after adding \n
    def write(self, string: str):
        super().write(f'{string}\n'.encode('utf-8'))

    # homing_list is like ['X', 'Y', 'Z']
    def run_homing(self, homing_list: List):
        string = 'G28 '
        for axis in homing_list:
            string += axis
            # self.set_current_position(axis=0)
        self.write(string)
        self.num_command_queue += 1
        while self.is_running(): pass

    # Move absolutely
    def move_to(self, X: int = None, Y: int = None, Z: int = None, A: int = None, B: int = None, C: int = None, wait_finishing = True):
        position = ''
        for axis, value in [('X', X), ('Y', Y), ('Z', Z), ('A', A), ('B', B), ('C', C)]:
            if value is not None:
                position += f'{axis}{value}'
        self.write(f'G90 {position}')
        self.num_command_queue += 1
        while self.is_running() and wait_finishing: pass

    # Move relative;y
    def move(self, X: int = None, Y: int = None, Z: int = None, A: int = None, B: int = None, C: int = None, wait_finishing = True):
        position = ''
        for axis, value in [('X', X), ('Y', Y), ('Z', Z), ('A', A), ('B', B), ('C', C)]:
            if value is not None:
                position += f'{axis}{value}'
        self.write(f'G91 {position}')
        self.num_command_queue += 1
        while self.is_running() and wait_finishing: pass

    # Usually set current position after homing
    def set_current_position(self, X: int = None, Y: int = None, Z: int = None, A: int = None, B: int = None, C: int = None):
        position = ''
        for axis, value in [('X', X), ('Y', Y), ('Z', Z), ('A', A), ('B', B), ('C', C)]:
            if value is not None:
                position += f'{axis}{value}'
        self.write(f'G92 {position}')
        self.num_command_queue += 1

    # invert_list is like ['X', 'Y', 'Z']
    def invert_axis(self, invert_list: List):
        total_value = 0
        for axis, value in [('X', 1), ('Y', 2), ('Z', 4), ('A', 8), ('B', 16), ('C', 32)]:
            if axis in invert_list:
                total_value += value
        self.write(f'$3={total_value}')
        self.num_command_queue += 1

    # invert_list is like ['X', 'Y', 'Z']
    def invert_homing_axis(self, invert_list: List):
        total_value = 0
        for axis, value in [('X', 1), ('Y', 2), ('Z', 4), ('A', 8), ('B', 16), ('C', 32)]:
            if axis in invert_list:
                total_value += value
        self.write(f'$23={total_value}')
        self.num_command_queue += 1

    # default: 3600
    def set_speed(self, X: int = None, Y: int = None, Z: int = None, A: int = None, B: int = None, C: int = None):
        for code, value in [('$110', X), ('$111', Y), ('$112', Z), ('$113', A), ('$114', B), ('$115', C)]:
            if value is not None:
                self.write(f'{code}={value}')
                self.num_command_queue += 1

    # default 10000
    def set_acceleration(self, X: int = None, Y: int = None, Z: int = None, A: int = None, B: int = None, C: int = None):
        for code, value in [('$120', X), ('$121', Y), ('$122', Z), ('$123', A), ('$124', B), ('$125', C)]:
            if value is not None:
                self.write(f'{code}={value}')
                self.num_command_queue += 1


def cap():
    capture = cv2.VideoCapture(2)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    capture.set(cv2.CAP_PROP_EXPOSURE, -7)
    # print(capture.get(cv2.CAP_PROP_EXPOSURE))
    while(True):
        ret, frame = capture.read()
        cv2.imshow('frame', cv2.resize(frame, (640, 480)))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.imwrite('image.png', frame)
            break
        # print(capture.get(cv2.CAP_PROP_EXPOSURE))
    capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    A_max = 2770
    Y_max = 2770
    Z_max = 1760

    A_max_micro = 22000
    Y_max_micro = 22000
    Z_max_micro = 14000


    ard_serial = Ard6S()
    ard_serial.invert_homing_axis(['X', 'Y', 'Z', 'A', 'B', 'C'])
    # ard_serial.run_homing(['Y', 'Z'])
    Thread(target=cap).start()
    ard_serial.set_speed(A=500, B=500, C=1000)
    while True:
        ard_serial.run_homing(['A', 'B', 'C'])
        ard_serial.set_current_position( A=0, B=0, C=0)
        ard_serial.move_to(A=500, B=500)
        ard_serial.move_to(A=500, B=500, C=500)
        while True:
            axis = input("axis:")
            num = int(input("num:"))
            if axis == 'x':
                ard_serial.move_to(A=num, B=num)
                time.sleep(0.3)
                print(ard_serial.is_running())
            else:
                ard_serial.move_to(C=num)
                time.sleep(0.3)
                print(ard_serial.is_running())

    # ard_serial.set_speed(A=1000, B=1000)
    # ard_serial.set_acceleration(X=50000)
    # ard_serial.move_to(X=500)
    # ard_serial.move_to(X=2500, wait_finishing=False)

#!/usr/bin/python3
# -*- coding: utf-8 -*-

from socket import *
import time
import sys
from packet import Packet
from header import Header
from infrastructures import *

LOCALHOST = '127.0.0.1'
SENDER_IP = '127.0.0.1'
RECIVER_IP = '127.0.0.1'
RECEIVER_PORT = 6666
MWS = 3  # Maximum Window Size
MSS = 8  # Maximum Segment Size
TIMEOUT = 300
LOG_NAME = 'Receiver_log.txt'

RECEIVER_STATUS = {
                        0: 'not_connected', 
                        1: 'syn acked',
                        2: 'connection established',
                    }


class Receiver:
    def __init__(self, receiver_ip=RECIVER_IP, receiver_port=RECEIVER_PORT):
        self.receiver = socket(AF_INET, SOCK_DGRAM)
        self.receiver.bind((receiver_ip, receiver_port))
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port
        self.ack_num = 0
        self.seq_num = 0
        self.status = 0
        self.buffer = {}
        self.start_time = time.time()
        self.logger = Logger(LOG_NAME)

    def receive(self):
        header = Header()
        received_header, received_data, source_ip, source_port, received_time =\
                        receive_packet(self.receiver, logger=self.logger)
        self.receiver.connect((source_ip, source_port))

        if received_header.syn == 1 and received_header.ack == 0:
            # 1st handshake
            print('connection request from {}:{}'.format(source_ip, source_port))
            self.isn = header.isn
            header.ack_num = received_header.seq_num + 1
            self.ack_num = received_header.seq_num + 1
            self.seq_num = header.seq_num
            header.ack = 1
            header.syn = 1
            self.status = 1
            send_packet(self.receiver, header, logger=self.logger)  # 2nd handshake

        elif self.status == 1 and received_header.syn == 0 and received_header.ack == 1:
            # 3rd handshake
            self.seq_num = received_header.ack_num
            self.data_bytes = b''
            self.status = 2
            print('connection established with {}:{}'.format(source_ip, source_port))

        elif self.status == 2 and received_header.fin == 1:
            # closing
            print('connection to {}:{} closing'.format(source_ip, source_port))
            self.logger.data_size = len(self.data_bytes)

            with open(FILE_RECEIVED, 'wb') as f:
                f.write(self.data_bytes)

            header.ack = 1
            header.ack_num = received_header.seq_num + 1
            self.ack_num = header.ack_num
            header.seq_num = self.seq_num
            send_packet(self.receiver, header, logger=self.logger)

            header = Header()
            header.fin = 1
            header.seq_num = self.seq_num
            header.ack_num = self.ack_num
            send_packet(self.receiver, header, logger=self.logger)
            # received_header, received_data, source_ip, source_port =\
            #             receive_packet(self.receiver)
            print('connection to {}:{} closed'.format(source_ip, source_port))
            self.logger.receiver_conclude()
            return False

        elif self.status == 2:
            print('receiving data from {}:{}'.format(source_ip, source_port))
            if len(received_data) > 0:
                self.logger.num_segments += 1
            if received_header.seq_num in self.buffer or received_header.seq_num < self.ack_num:
                self.logger.dup_count += 1
            if received_header.seq_num == self.ack_num:
                self.ack_num = received_header.seq_num + len(received_data)
                self.data_bytes += received_data
                if len(self.buffer) > 0:
                    next_expected = received_header.seq_num + len(received_data)
                    while next_expected in self.buffer:
                        buffered_next = self.buffer[next_expected]
                        self.data_bytes += buffered_next
                        next_expected += len(buffered_next)
                        self.ack_num += len(buffered_next)
                    
            elif received_header.seq_num > self.ack_num:
                self.buffer[received_header.seq_num] = received_data

            header = Header()
            header.ack = 1
            header.ack_num = self.ack_num
            header.seq_num = self.seq_num
            send_packet(self.receiver, header, logger=self.logger)

        return True

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('parameters incorrect, please enter commad in the following format:\npython Sender.py RECIVER_PORT FILE_RECEIVED')
        sys.exit()
    RECIVER_PORT, FILE_RECEIVED = sys.argv[1:]
    receiver = Receiver()
    connection = True
    while connection:
        connection = receiver.receive()
    # print(receiver.data_bytes.decode())
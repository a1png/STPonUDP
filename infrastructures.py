from packet import Packet
from header import Header
import random
import asyncio
import time
from socket import timeout
import threading


def send_packet(socket, header, data=None, pld=None, logger=None):
    is_loss = False
    packet = Packet()
    packet.wrap(header, data)
    print("=====================")
    print("sending>>>>>>>>>>>>>\n", header, '\n-----------------\n', data, sep='')
    print("=====================")
    if pld is not None:
        # randomly loss packet
        loss = pld.roll()
        if loss < pld.p_drop:
            print('{} not sent'.format(header.seq_num))
            is_loss = True
            logger.pck_loss += 1

    if logger is not None:
        data_len = data and len(data) or 0
        logger.log('snd', header, data_len, is_loss)
    if is_loss:
        return
    if pld is not None:
        is_delay = pld.roll()
        if is_delay < pld.p_delay:
            delay = pld.roll() * pld.max_delay
            print('{} delayed for {} ms'.format(header.seq_num, delay))
            time.sleep(delay/1000)
            logger.pck_delay += 1

    socket.send(packet.msg)


def receive_packet(socket, logger=None):
    msg, address = socket.recvfrom(1024)
    received_time = time.time()
    ip, port = address
    header = Header()
    packet = Packet()
    data = packet.parse(msg, header)
    print("=====================")
    print("receiving<<<<<<<<<<<<\n", header, '\n-----------------\n', data, sep='')
    print("=====================")
    if logger is not None:
        data_len = data and len(data) or 0
        logger.log('rcv', header, data_len)
    return header, data, ip, port, received_time


class SenderWindow(dict):
    def __len__(self):
        size = 0
        for i in self:
            segment = self[i]
            if isinstance(segment, dict) and segment['status'] == 0:
                size += len(segment.get('data', ''))
        return size

    def head(self):
        for i in sorted(self.keys()):
            segment = self[i]
            if isinstance(segment, dict) and segment['status'] == 0:
                return i, i + len(segment['data'])


class PLD:
    def __init__(self, seed, p_drop, p_delay, max_delay):
        if seed is not None:
            random.seed(seed)
            self.roll = random.random
            self.p_drop = p_drop
            self.p_delay = p_delay
            self.max_delay = max_delay
        else:
            def roll(self):
                return 1
        return


class Logger:
    def __init__(self, filename):
        self.file = open(filename, 'w')
        self.start_time = time.time()
        self.file.write('<msg_type>\t<time>\t<packet_type>\t<seq>\t<size>\t<ack>\n')
        self.data_size = 0
        self.num_segments = 0
        self.pck_loss = 0
        self.pck_delay = 0
        self.retransmit = 0
        self.dup_count = 0

    def log(self, m_type, header, data_len, is_loss=False):
        """
        m_type: <snd/rcv/drop>
        time: <time>
        p_type: <type of packet> S (SYN), A (ACK), F (FIN) and D (Data)
        seq_num: <seq-number>
        length: <number-of-bytes>
        ack_num: <ack-number>
        """
        if is_loss:
            m_type = 'drop'

        if data_len > 0:
            p_type = 'D'
            self.data_size += data_len
        else:
            p_type = ''
            if header.syn == 1:
                p_type = 'S'
            if header.fin == 1:
                p_type = 'F'
            if header.ack == 1:
                p_type += 'A'

        t = '\t'.join([str(i) for i in [m_type, round((time.time() - self.start_time) * 1000, 3), p_type, header.seq_num, data_len,
                                        header.ack_num]]) + '\n'
        self.file.write(t)

    def sender_conclude(self):
        self.file.write("=====================================================\n")
        self.file.write("Amount of (original) Data Transferred (in bytes): {}\n".format(self.data_size))
        self.file.write("Number of Data Segments Sent (excluding retransmissions): {}\n".format(self.num_segments))
        self.file.write("Number of (all) Packets Dropped (by the PLD module): {}\n".format(self.pck_loss))
        self.file.write("Number of (all) Packets Delayed (for the extended assignment only): {}\n".format(self.pck_delay))
        self.file.write("Number of Retransmitted Segments: {}\n".format(self.retransmit))
        self.file.write("Number of Duplicate Acknowledgements received: {}\n".format(self.dup_count))
        self.file.close()

    def receiver_conclude(self):
        self.file.write("=====================================================\n")
        self.file.write("Amount of (original) Data Transferred (in bytes): {}\n".format(self.data_size))
        self.file.write("Number of (original) Data Segments Received: {}\n".format(self.num_segments))
        self.file.write("Number of duplicate segments received: {}\n".format(self.dup_count))


class Thread(threading.Thread):
    def __init__(self, name, sender):
        threading.Thread.__init__(self)
        self.name = name
        self.sender = sender

    def run(self):
        if self.name == 'sender':
            self.sender._sending_data_thread()

        if self.name == 'receiver':
            self.sender._receiving_data_thread()
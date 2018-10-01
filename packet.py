# a class for the stp packet
from socket import inet_aton
from struct import pack, unpack
from header import Header

"""
PACKET STRUCTURE
===================
Sequence number
Acknowledgment
Flags:syn ack fin 0 
0000
-------------------
Data
===================
"""
STRUCT_CODE = '!2i4hi'
HEADER_LEN = 20

class Packet:
    def wrap(self, header, data=None):
        self.msg = pack(STRUCT_CODE, header.seq_num, header.ack_num, header.syn, header.ack, header.fin, 0, 0)
        if data is not None:
            self.msg += data
        return

    def parse(self, msg, header):
        header.seq_num, header.ack_num, header.syn, header.ack, header.fin, _a, _b =\
            unpack(STRUCT_CODE, msg[:HEADER_LEN])
        data = msg[HEADER_LEN:]
        return data



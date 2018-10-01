# a class for the stp header

from uuid import uuid4

class Header:
    def __init__(self):
        self.syn = 0
        self.ack = 0
        self.fin = 0
        self.ack_num = 0
        self._gen_isn()

    def _gen_isn(self):
        self.isn = uuid4().time_mid
        self.seq_num = self.isn

    def __str__(self):
        return "SYN: {}\nACK: {}\nFIN: {}\nseq_num: {}\nack_num {}"\
                .format(self.syn, self.ack, self.fin, self.seq_num, self.ack_num)


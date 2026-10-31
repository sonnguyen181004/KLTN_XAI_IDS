"""Payload-free retained view for the pinned CICFlowMeter 0.5.0 exporters.

Only used AFTER admission/bulk/TCP lifecycle processing on the original packet.
Keep the original timestamp numeric type: converting Decimal to float here
would change IAT subtraction. This is not a general-purpose Scapy packet.
"""
from dataclasses import dataclass
from scapy.layers.inet import IP, TCP, UDP


@dataclass(frozen=True, slots=True)
class LengthOnly:
    size: int

    def __len__(self):
        return self.size


@dataclass(frozen=True, slots=True)
class HeaderRecord:
    ihl: object
    flags: int
    payload: LengthOnly


@dataclass(frozen=True, slots=True)
class PacketRecord:
    time: object
    size: int
    is_tcp: bool
    flag_text: str
    header: HeaderRecord

    @classmethod
    def from_packet(cls, packet):
        tcp = TCP in packet
        transport = packet[TCP] if tcp else packet[UDP]
        return cls(packet.time, len(packet), tcp, packet.sprintf('%TCP.flags%'),
                   HeaderRecord(packet[IP].ihl, int(transport.flags) if tcp else 0,
                                LengthOnly(len(transport.payload))))

    def __len__(self):
        return self.size

    def __contains__(self, layer):
        return (layer in (IP, 'IP') or
                (self.is_tcp and layer in (TCP, 'TCP')) or
                (not self.is_tcp and layer in (UDP, 'UDP')))

    def __getitem__(self, layer):
        if layer not in self:
            raise IndexError(layer)
        return self.header

    def sprintf(self, expression):
        if expression != '%TCP.flags%':
            raise ValueError('Unsupported retained-packet expression')
        return self.flag_text

"""V3 flow lifecycle. V1/V2 remain immutable comparison baselines.

Capture-time half-open windows; late packets are explicitly isolated, never
clamped, silently discarded, or appended to already exported records.
This operational policy is NOT historical CICFlowMeter/train parity.
"""
import math

from scapy.layers.inet import IP, TCP, UDP
from scapy.packet import Padding
from cicflowmeter.features.context import PacketDirection

from capture_adapter import ProjectFlow, ProjectFlowSession, packet_key

LIFECYCLE_VERSION = 'rq3-cfm-0.5.0-lifecycle-v3'


class LifecycleFlow(ProjectFlow):
    extractor_version = LIFECYCLE_VERSION

    def __init__(self, packet, direction):
        super().__init__(packet, direction)
        self.end_reason = 'open'
        self.syn_sequences = {}
        self.fin_ends = {}
        self.fin_acked = set()
        self.handshake_only = True
        self.tcp_end = None
        self._observe_tcp(packet, direction)

    def new_connection(self, packet, direction):
        if TCP not in packet or int(packet[TCP].flags) & 0x12 != 0x02:
            return False
        previous = self.syn_sequences.get(direction)
        if previous is not None:
            return int(packet[TCP].seq) != previous or bool(self.fin_ends)
        # A second direction SYN during opening may be a simultaneous open.
        return not self.handshake_only or bool(self.fin_ends)

    def _observe_tcp(self, packet, direction):
        if TCP not in packet:
            return
        tcp = packet[TCP]
        flags = int(tcp.flags)
        other = PacketDirection.REVERSE if direction == PacketDirection.FORWARD else PacketDirection.FORWARD
        if flags & 2:
            self.syn_sequences.setdefault(direction, int(tcp.seq))
        else:
            self.handshake_only = False
        if flags & 1:
            # FIN consumes one sequence number; payload/SYN consume space too.
            payload_len = len(tcp.payload) - (len(tcp[Padding]) if Padding in tcp else 0)
            self.fin_ends.setdefault(direction, (int(tcp.seq) + payload_len + 1 + bool(flags & 2)) % (2**32))
        if flags & 16 and other in self.fin_ends:
            if (int(tcp.ack) - self.fin_ends[other]) % (2**32) < 2**31:
                self.fin_acked.add(other)
        if flags & 4:
            self.tcp_end = 'tcp_rst_observed'
        elif len(self.fin_ends) == 2 and len(self.fin_acked) == 2:
            self.tcp_end = 'tcp_fin_ack_observed'

    def add_packet(self, packet, direction):
        super().add_packet(packet, direction)
        self._observe_tcp(packet, direction)

    def get_data(self, include_fields=None):
        data = super().get_data()
        data['flow_end_reason'] = self.end_reason
        return {k: v for k, v in data.items() if include_fields is None or k in include_fields}


class LifecycleSession(ProjectFlowSession):
    def __init__(self, *args, max_age=90., idle_timeout=240., **kwargs):
        if not all(math.isfinite(x) and x > 0 for x in (max_age, idle_timeout)):
            raise ValueError('Timeouts must be positive and finite')
        super().__init__(*args, flow_class=LifecycleFlow, **kwargs)
        self.max_age, self.idle_timeout = max_age, idle_timeout
        self.n_late = 0
        self._packet_watermark = float('-inf')

    def _expiry(self, flow, now):
        # Both GC and packet admission use precisely the same >= boundaries.
        deadline, reason = min((float(flow.latest_timestamp) + self.idle_timeout, 'idle_timeout'),
                               (float(flow.start_timestamp) + self.max_age, 'active_timeout'))
        if now >= deadline:
            return reason
        return None

    def _export(self, key, reason):
        if self.flows[key].end_reason == 'open':
            self.flows[key].end_reason = reason
        self._emit(key)  # Does not delete buffered data when writing fails.

    def process(self, packet):
        with self._lock:
            if self._closed:
                raise RuntimeError('Cannot add packets after capture session is closed')
            if IP not in packet or (TCP not in packet and UDP not in packet):
                self.n_ignored += 1
                return None
            timestamp = float(packet.time)
            if not math.isfinite(timestamp):
                raise ValueError('Packet timestamp must be finite')
            key = packet_key(packet)
            reverse = (key[1], key[0], key[3], key[2], key[4])
            existing = key if key in self.flows else reverse
            flow = self.flows.get(existing)
            # Preserve arrival evidence without contaminating IAT/bulk/windows.
            # A standalone late flow is an explicit segmentation limitation.
            late = timestamp < self._packet_watermark
            if late:
                late_key = (*key, 'late', self.packets_count)
                self.flows[late_key] = LifecycleFlow(packet, PacketDirection.FORWARD)
                self.packets_count += 1
                self.n_late += 1
                self._export(late_key, 'late_packet')
                return None
            # Check this tuple exactly at admission; amortize the all-flow scan.
            if flow is not None:
                reason = self._expiry(flow, timestamp)
                if reason:
                    self._export(existing, reason)
            if timestamp >= self._next_capture_gc:
                self.garbage_collect(timestamp)
                self._next_capture_gc = timestamp + 1.
            flow = self.flows.get(existing)
            direction = PacketDirection.FORWARD if existing == key else PacketDirection.REVERSE
            if flow is not None and flow.new_connection(packet, direction):
                self._export(existing, 'tcp_new_syn')
                flow = None
            if flow is None:
                existing = key
                flow = self.flows[key] = LifecycleFlow(packet, PacketDirection.FORWARD)
            else:
                flow.add_packet(packet, direction)
            self.packets_count += 1
            self._packet_watermark = max(timestamp, self._packet_watermark)
            if flow.tcp_end:
                self._export(existing, flow.tcp_end)
        return None

    def garbage_collect(self, latest_time):
        with self._lock:
            for key, flow in list(self.flows.items()):
                reason = 'flush' if latest_time is None else self._expiry(flow, latest_time)
                if reason:
                    self._export(key, reason)

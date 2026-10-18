"""V3 flow lifecycle. V1/V2 remain immutable comparison baselines.

Capture-time half-open windows; late packets are explicitly isolated, never
clamped, silently discarded, or appended to already exported records.
This operational policy is NOT historical CICFlowMeter/train parity.
"""
import math

from scapy.layers.inet import IP, TCP, UDP
from cicflowmeter.features.context import PacketDirection

from capture_adapter import ProjectFlow, ProjectFlowSession, packet_key

LIFECYCLE_VERSION = 'rq3-cfm-0.5.0-lifecycle-v3'


class LifecycleFlow(ProjectFlow):
    extractor_version = LIFECYCLE_VERSION

    def __init__(self, packet, direction):
        super().__init__(packet, direction)
        self.end_reason = 'open'

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
        if now - float(flow.latest_timestamp) >= self.idle_timeout:
            return 'idle_timeout'
        if now - float(flow.start_timestamp) >= self.max_age:
            return 'active_timeout'
        return None

    def _export(self, key, reason):
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
            late = timestamp < (float(flow.latest_timestamp) if flow else self._packet_watermark)
            if late:
                late_key = (*key, 'late', self.packets_count)
                self.flows[late_key] = LifecycleFlow(packet, PacketDirection.FORWARD)
                self.packets_count += 1
                self.n_late += 1
                self._export(late_key, 'late_packet')
                return None
            self.garbage_collect(timestamp)
            flow = self.flows.get(existing)
            if flow is None:
                self.flows[key] = LifecycleFlow(packet, PacketDirection.FORWARD)
            else:
                flow.add_packet(packet, PacketDirection.FORWARD if existing == key else PacketDirection.REVERSE)
            self.packets_count += 1
            self._packet_watermark = max(timestamp, self._packet_watermark)
        return None

    def garbage_collect(self, latest_time):
        with self._lock:
            for key, flow in list(self.flows.items()):
                reason = 'flush' if latest_time is None else self._expiry(flow, latest_time)
                if reason:
                    self._export(key, reason)

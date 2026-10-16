"""Versioned project corrections to Python CICFlowMeter 0.5.0.

Fix packet admission, protocol keys, CWR, singleton IAT and active/idle.
Length/header, variance, subflow and window conventions remain upstream;
this version does not claim parity with historical CICFlowMeter-V3 datasets.
"""
from importlib.metadata import version
import csv
import threading

import numpy as np
from scapy.layers.inet import IP, TCP, UDP
from cicflowmeter.constants import ACTIVE_TIMEOUT, EXPIRED_UPDATE
from cicflowmeter.features.context import PacketDirection
from cicflowmeter.flow import Flow
from cicflowmeter.flow_session import FlowSession

V1_VERSION = 'rq3-cfm-0.5.0-fixes-v1'
EXTRACTOR_VERSION = 'rq3-cfm-0.5.0-fixes-v2'
CANDIDATE_VERSION = 'rq3-train-conventions-experimental-v1'
LEGACY_VERSION = 'python-cicflowmeter-0.5.0-legacy'


class ProjectCSVWriter:
    """One CSV record per newline on Windows, with explicit UTF-8 encoding."""
    def __init__(self, output):
        self.file = open(output, 'w', encoding='utf-8', newline='')
        self.writer = csv.writer(self.file)
        self.line = 0

    def write(self, data):
        if self.line == 0:
            self.writer.writerow(data.keys())
        self.writer.writerow(data.values())
        self.file.flush()
        self.line += 1


def statistics(values):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return dict(total=0., mean=0., std=0., min=0., max=0.)
    return dict(total=float(values.sum()), mean=float(values.mean()),
                std=float(values.std()), min=float(values.min()), max=float(values.max()))


def packet_key(packet):
    transport = packet[TCP] if TCP in packet else packet[UDP]
    return (packet[IP].src, packet[IP].dst, int(transport.sport), int(transport.dport),
            6 if TCP in packet else 17)


class ProjectFlowV1(Flow):
    extractor_version = V1_VERSION
    def __init__(self, packet, direction):
        super().__init__(packet, direction)
        self._activity_start = self._activity_last = packet.time
        # Upstream constructor records the first packet but does not update bulk.
        # Admit it once here; later packets are admitted only in add_packet().
        self.update_flow_bulk(packet, direction)

    def update_subflow(self, packet):
        # Keep activity timing independent of latest_timestamp (already advanced
        # by upstream add_packet). Subflow output itself remains upstream's copy.
        current = packet.time
        if current < self._activity_last:
            return  # Out-of-order timestamps must not create negative idle.
        gap = current - self._activity_last
        if gap > ACTIVE_TIMEOUT:
            duration = self._activity_last - self._activity_start
            if duration > 0:
                self.active.append(duration)
            self.idle.append(gap)
            self._activity_start = current
        self._activity_last = current

    def get_data(self, include_fields=None):
        data = super().get_data()
        for prefix, direction in [('flow', None), ('fwd', PacketDirection.FORWARD),
                                  ('bwd', PacketDirection.REVERSE)]:
            packets = [p for p,d in self.packets if direction is None or d == direction]
            iats = [float(packets[i].time-packets[i-1].time) for i in range(1,len(packets))]
            stats = statistics(iats)
            for suffix in ('mean', 'std', 'max', 'min'):
                data[f'{prefix}_iat_{suffix}'] = stats[suffix]
            if prefix != 'flow':
                data[f'{prefix}_iat_tot'] = stats['total']
        data['cwr_flag_count'] = sum(TCP in p and bool(int(p[TCP].flags) & 128)
                                     for p,_ in self.packets)
        # Do not mutate activity lists on export; repeated snapshots are identical.
        active = list(self.active)
        duration = self._activity_last-self._activity_start
        if duration > 0:
            active.append(duration)
        for prefix, values in [('active', active), ('idle', self.idle)]:
            stats = statistics(values)
            for suffix in ('mean', 'std', 'max', 'min'):
                data[f'{prefix}_{suffix}'] = stats[suffix]
        data['extractor_version'] = self.extractor_version
        return {k:v for k,v in data.items() if include_fields is None or k in include_fields}


class ProjectFlow(ProjectFlowV1):
    """V2 preserves the first TCP window, including a legitimate zero window."""
    extractor_version = EXTRACTOR_VERSION

    def __init__(self, packet, direction):
        super().__init__(packet, direction)
        self._first_windows = {direction: int(packet[TCP].window)} if TCP in packet else {}

    def add_packet(self, packet, direction):
        super().add_packet(packet, direction)
        if TCP in packet:
            self._first_windows.setdefault(direction, int(packet[TCP].window))
        # Upstream treats zero as unobserved; restore the actual first value.
        for observed_direction, value in self._first_windows.items():
            self.init_window_size[observed_direction] = value


class TrainCandidateFlow(ProjectFlow):
    """Opt-in partial convention experiment; NOT certified historical V3 parity.

    Change only directional length SD, floor ratio, missing-window sentinel.
    Lengths remain whole frames; flags/bulk/IAT/mean/header/segmentation unchanged.
    """
    extractor_version = CANDIDATE_VERSION

    def get_data(self, include_fields=None):
        data = super().get_data()
        for prefix, direction in [('fwd', PacketDirection.FORWARD), ('bwd', PacketDirection.REVERSE)]:
            lengths = [len(p) for p,d in self.packets if d == direction]
            data[f'{prefix}_pkt_len_std'] = float(np.std(lengths, ddof=1)) if len(lengths) > 1 else 0.
            data[f'init_{prefix}_win_byts'] = self._first_windows.get(direction, -1)
        data['down_up_ratio'] = data['tot_bwd_pkts'] // data['tot_fwd_pkts'] if data['tot_fwd_pkts'] else 0
        return {k:v for k,v in data.items() if include_fields is None or k in include_fields}


class ProjectFlowSession(FlowSession):
    def __init__(self, *args, **kwargs):
        if version('cicflowmeter') != '0.5.0':
            raise RuntimeError('Project capture adapter requires cicflowmeter==0.5.0')
        self.flow_class = kwargs.pop('flow_class', ProjectFlow)
        super().__init__(*args, **kwargs)
        if self.output_mode == 'csv' and self.flow_class is not ProjectFlowV1:
            self.output_writer.file.close()
            self.output_writer = ProjectCSVWriter(self.output)
        # One critical section covers admission, snapshots and writes: live GC
        # cannot export/delete a flow while its packets/features are changing.
        self._lock = threading.RLock()
        self._closed = False
        self.n_ignored = 0
        self._next_capture_gc = 0.
        self.n_exported = 0
        self.n_exported_packets = 0

    def _emit(self, key):
        flow = self.flows[key]
        self.output_writer.write(flow.get_data(self.fields))
        self.n_exported += 1
        self.n_exported_packets += len(flow.packets)
        del self.flows[key]  # Keep buffered flow if writing raises.

    def process(self, packet):
        if IP not in packet or (TCP not in packet and UDP not in packet):
            self.n_ignored += 1
            return None
        key = packet_key(packet)
        reverse = (key[1], key[0], key[3], key[2], key[4])
        with self._lock:
            if self._closed:
                raise RuntimeError('Cannot add packets after capture session is closed')
            self.packets_count += 1
            direction = PacketDirection.FORWARD
            existing = key
            flow = self.flows.get(key)
            if flow is None:
                existing = reverse
                flow = self.flows.get(reverse)
                direction = PacketDirection.REVERSE
            if flow is not None and float(packet.time-flow.latest_timestamp) > EXPIRED_UPDATE:
                self._emit(existing)
                flow = None
            if flow is None:
                # Constructor already contains the first packet; do not add again.
                self.flows[key] = self.flow_class(packet, PacketDirection.FORWARD)
            else:
                flow.add_packet(packet, direction)
            # Use capture timestamps, never current wall time for offline PCAPs.
            # FIN does not end both directions; retain existing timeout policy.
            timestamp = float(packet.time)
            if timestamp >= self._next_capture_gc:
                self.garbage_collect(timestamp)
                self._next_capture_gc = timestamp + 1.
            elif flow is not None and flow.duration >= 90:
                self.garbage_collect(timestamp)
        return None

    def garbage_collect(self, latest_time):
        with self._lock:
            for key, flow in list(self.flows.items()):
                if latest_time is None or latest_time-float(flow.latest_timestamp) >= EXPIRED_UPDATE or flow.duration >= 90:
                    self._emit(key)

    def get_flows(self):
        with self._lock:
            return tuple(self.flows.values())

    def flush_flows(self):
        with self._lock:
            if self._closed:
                return
            self.garbage_collect(None)
            self._closed = True
            # Explicitly close only this session's CSV writer, not global state.
            stream = getattr(self.output_writer, 'file', None)
            if stream is not None:
                stream.close()

    def toPacketList(self):
        self.flush_flows()
        return []

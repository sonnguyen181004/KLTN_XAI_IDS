package cic.cs.unb.ca.ifm;

import cic.cs.unb.ca.jnetpcap.BasicPacketInfo;
import cic.cs.unb.ca.jnetpcap.PacketReader;
import cic.cs.unb.ca.jnetpcap.FlowGenerator;
import cic.cs.unb.ca.jnetpcap.FlowFeature;
import cic.cs.unb.ca.jnetpcap.worker.InsertCsvRow;
import org.jnetpcap.Pcap;
import org.jnetpcap.PcapIf;
import org.jnetpcap.nio.JMemory.Type;
import org.jnetpcap.packet.PcapPacket;
import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Short, bounded live trial; emits one CSV row when the Java extractor closes a flow. */
public class LiveTrial {
    public static void main(String[] args) {
        List<PcapIf> devices = new ArrayList<>();
        StringBuilder error = new StringBuilder();
        if (Pcap.findAllDevs(devices, error) != Pcap.OK) throw new IllegalStateException(error.toString());
        if (args.length == 0 || "--list".equals(args[0])) {
            for (PcapIf device : devices) System.out.println(device.getName() + " | " + device.getDescription());
            return;
        }
        if (args.length != 3) throw new IllegalArgumentException("interface-name seconds output.csv");
        PcapIf selected = null;
        for (PcapIf device : devices)
            if (device.getName().equals(args[0]) || (device.getDescription() != null && device.getDescription().equals(args[0])))
                selected = device;
        if (selected == null) throw new IllegalArgumentException("Interface not found; run --list first");
        int seconds = Integer.parseInt(args[1]);
        if (seconds < 1 || seconds > 120) throw new IllegalArgumentException("seconds must be 1..120");
        File output = new File(args[2]).getAbsoluteFile();
        if (output.exists()) throw new IllegalArgumentException("Output exists: " + output);
        output.getParentFile().mkdirs();
        FlowGenerator flows = new FlowGenerator(true, 120000000L, 5000000L);
        final int[] emitted = {0};
        flows.addFlowListener(flow -> {
            InsertCsvRow.insert(FlowFeature.getHeader(), Collections.singletonList(flow.dumpFlowBasedFeaturesEx()),
                               output.getParent(), output.getName());
            emitted[0]++;
            System.out.println("flow_closed=" + emitted[0]);
        });
        Pcap capture = Pcap.openLive(selected.getName(), 65535, Pcap.MODE_PROMISCUOUS, 1000, error);
        if (capture == null) throw new IllegalStateException("Open capture failed: " + error);
        final int[] packets = {0};
        long deadline = System.nanoTime() + seconds * 1000000000L;
        try {
            while (System.nanoTime() < deadline) {
                int status = capture.dispatch(100, (PcapPacket packet, String unused) -> {
                    PcapPacket copy = new PcapPacket(Type.POINTER);
                    packet.transferStateAndDataTo(copy);
                    BasicPacketInfo info = PacketReader.getBasicPacketInfo(copy, true, false);
                    if (info != null) { flows.addPacket(info); packets[0]++; }
                }, "");
                if (status < 0) throw new IllegalStateException("Capture dispatch failed: " + status);
            }
            long flushed = flows.dumpLabeledCurrentFlow(output.getPath(), FlowFeature.getHeader());
            System.out.println("accepted_packets=" + packets[0] + " closed_flows=" + emitted[0] + " flushed_flows=" + flushed);
        } finally {
            capture.close();
        }
    }
}

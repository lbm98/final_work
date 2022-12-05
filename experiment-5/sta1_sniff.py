from scapy.layers.dot11 import Dot11Beacon, RadioTap
from scapy.all import sniff, send, IP, UDP

import subprocess


MININET_WIFI_EXE = '/home/wifi/mininet-wifi/util/m'


def get_current_association():
    try:
        cmd = (
            f'{MININET_WIFI_EXE}'
            f' sta1 iw dev sta1-wlan0 link'
            f' | grep Connected'
            f' | cut -d " " -f3'
        )
        result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)
        assoc = result.stdout
        assoc = assoc[:-1] # remove trailing newline
        return assoc.decode()
    except:
        return ''


def pkt_callback(pkt):
    sta1_addr = "02:00:00:00:00:00"
    if pkt.haslayer(Dot11Beacon):
        if pkt.haslayer(RadioTap):
            rssi = pkt.dBm_AntSignal

            current_association = get_current_association()
            # msg = vehicle,transmitter,rssi,current_association
            msg = (
                f"{sta1_addr}"
                f",{pkt.addr2}"
                f",{rssi}"
                f",{current_association}"
            )
            # print(msg)
            packet = (
                IP(src="10.0.0.1", dst="10.0.0.100")
                / UDP(sport=8000, dport=6653)
                / msg
            )
            send(packet, verbose=0)

sniff(iface="mon0", prn=pkt_callback)
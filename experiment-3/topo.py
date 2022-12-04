#!/usr/bin/env python

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.link import wmediumd
from mn_wifi.wmediumdConnector import interference


def topology():
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference,
                       noise_th=-91, fading_cof=3)

    info("*** Creating nodes\n")

    sta1 = net.addStation('sta1', position='10,25,0',
                          mac="02:00:00:00:00:00")

    ap1 = net.addAccessPoint('ap1', ssid='ssid-ap1',
                             mode='g', channel='1', range=30,
                             position='15,30,0',
                             ip='10.0.0.1',
                             mac='00:00:00:00:00:01')

    ap2 = net.addAccessPoint('ap2', ssid='ssid-ap2',
                             mode='g', channel='1', range=30,
                             position='35,30,0',
                             ip='10.0.0.2',
                             mac='00:00:00:00:00:02')

    s3 = net.addSwitch('s3')
    h1 = net.addHost('h1', ip="10.0.0.100")
    c1 = net.addController('c1')

    net.setPropagationModel(model="logDistance", exp=5)

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info("*** Creating links\n")
    net.addLink(ap1, s3)
    net.addLink(ap2, s3)
    net.addLink(s3, h1)

    info("*** Starting network\n")
    net.build()
    c1.start()
    ap1.start([c1])
    ap2.start([c1])
    s3.start([c1])

    # create a monitor interface
    # so we can sniff beacons that contain RSSI information
    sta1.cmd('iw dev sta1-wlan0 interface add mon0 type monitor')
    sta1.cmd('ifconfig mon0 up')

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()

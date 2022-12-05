import time
import subprocess

from mininet.node import Controller, RemoteController
from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.link import wmediumd
from mn_wifi.wmediumdConnector import interference
from mininet.term import makeTerm, cleanUpScreens


start_time = time.time()


def get_rssi(sta):
    cmd = (
        f'iw dev {sta.name}-wlan0 link'
        f' | grep signal'
    )
    output = sta.cmd(cmd)
    try:
        # split on whitespace
        return output.split()[1]
    except:
        return None


def gather_telemetry(sta):
    with open(f'{sta.name}.data', 'w') as fh:
        for i in range(50):
            relative_time = time.time() - start_time
            rssi = get_rssi(sta)
            if rssi is None:
                rssi = 0
            fh.write(f'{relative_time},{rssi}\n')
            time.sleep(0.1)


def topology():
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference,
                       noise_th=-91, fading_cof=3,
                       controller=RemoteController,
                       allAutoAssociation = False)

    info("*** Creating nodes\n")

    sta1 = net.addStation('sta1', position='10,25,0',
                          mac="02:00:00:00:00:00")

    # sta2 = net.addStation('sta2', position='65,25,0',
    #                       mac="02:00:00:00:01:00")

    # if the channels are the same, we easily can sniff
    # the packets from both acess points.
    # might be a too limited assumption
    # but will do for now

    # make sure the mac matches the ssid in the following way
    # ssid-ap#
    # 00:00:00:00:00:0#
    # where # should be the same number
    ap1 = net.addAccessPoint('ap1', ssid='ssid-ap1',
                             mode='g', channel='1', range=30,
                             position='15,30,0',
                             ip='10.0.0.1',
                             mac='00:00:00:00:00:01')

    ap2 = net.addAccessPoint('ap2', ssid='ssid-ap2',
                             mode='g', channel='1', range=30,
                             position='55,30,0',
                             ip='10.0.0.2',
                             mac='00:00:00:00:00:02')

    s3 = net.addSwitch('s3')
    h1 = net.addHost('h1', ip="10.0.0.100")
    c1 = net.addController('c1')

    net.setPropagationModel(model="logDistance", exp=5)

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    net.startMobility(time=0)
    net.mobility(sta1, 'start', time=0, position='10,25,0')
    net.mobility(sta1, 'stop', time=10, position='60,25,0')
    net.stopMobility(time=30)

    # net.plotGraph(max_x=300, max_y=300)

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

    # makeTerm(h1, cmd="bash -c 'cd ryu && ./run.sh h1;'")
    # time.sleep(2)

    # the switch is programmed to:
    #   - learn the MAC addresses to avoid FLOODs
    #   - install flows to avoid sending matching packets to the controller next time
    # however, we want the controller to keep receiving packets that contain the RSSI information.
    # to accomplish this we install the rule below.
    # for this purpose we allocated the special port number 8000.
    # and instruct packets containing this port number to ALWAYS go to the controller.
    s3.cmd('ovs-ofctl add-flow "s3" in_port=1,udp,tp_src=8000,actions=controller')
    s3.cmd('ovs-ofctl add-flow "s3" in_port=2,udp,tp_src=8000,actions=controller')

    # we need to add a sub-interface of the type monitor
    # to be able to receive RSSI information.
    sta1.cmd('iw dev sta1-wlan0 interface add mon0 type monitor')
    sta1.cmd('ifconfig mon0 up')

    # setup initial association
    sta1.cmd('iw dev sta1-wlan0 connect ssid-ap1')

    # sta2.cmd('iw dev sta2-wlan0 interface add mon0 type monitor')
    # sta2.cmd('ifconfig mon0 up')

    # wpa_cli does only work with bgscan
    # sta1.cmd('wpa_cli -i sta1-wlan0 roam 00:00:00:00:00:02')

    sta1.cmd("python sta1_sniff.py &")
    # sta2.cmd("python sta2_sniff.py &")

    

    info("*** Running CLI\n")
    # gather_telemetry(sta1)
    # proc = subprocess.Popen(["python","tele_ping.py"])

    CLI(net)

    info("*** Stopping network\n")
    # proc.terminate()
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()

# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, udp
from ryu.lib.packet import ether_types

##################
# START MY CODE
##################

import os
import time

MININET_WIFI_EXE = '/home/wifi/mininet-wifi/util/m'

# vehicle -> [transmitter,rssi] pair
MY_STORE = {}
TIMEOUTS = {}
START_TIME = time.time()

##################
# END MY CODE
##################


class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = format(datapath.id, "d").zfill(16)
        self.mac_to_port.setdefault(dpid, {})

        #self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        ##################
        # START MY CODE
        ##################

        _udp = pkt.get_protocol(udp.udp)
        if _udp is not None:
            if _udp.src_port == 8000:
                app_data = pkt.protocols[3]
                app_data = app_data.decode()
                vehicle, transmitter, rssi, current_association = app_data.split(',')
                rssi = int(rssi)

                # apply timeouts
                # we receive packets from AP1 and AP2
                # if we suddenly loose connection to an AP
                # eg by means of py.setPosition(far away)
                # the rssi would still be high
                # so if we havent received a packet from an AP
                # for a while, set the rssi to the lowest
                # possible value: minus infinity.

                # update timeout
                dt = time.time() - START_TIME
                if vehicle not in TIMEOUTS:
                    TIMEOUTS[vehicle] = dt
                else:
                    TIMEOUTS[vehicle] = dt - TIMEOUTS[vehicle]
                    # expire associations
                    for veh in TIMEOUTS:
                        if TIMEOUTS[veh] > 1:
                            MY_STORE[vehicle][1] = float('-inf')

                if current_association == '':
                    # this information needs to be given
                    # for the algorithm below to be meaningful
                    pass
                elif vehicle not in MY_STORE:
                    # a new vehicle has registered.
                    # we assume this vehicle is already associated
                    # to an access point.
                    MY_STORE[vehicle] = [current_association, rssi]
                    print(f"registered new vehicle {vehicle} to AP {current_association}", flush=True)
                else:
                    # we get an other message from an already
                    # registed vehicle.
                    # it could be that we should re-associate
                    prev_transmitter, prev_rssi = MY_STORE[vehicle]
                    if prev_transmitter == transmitter:
                        # the same transmitter
                        # just update the pair
                        MY_STORE[vehicle] = [transmitter, rssi]
                    else:
                        # print(f'{prev_rssi},{rssi}')

                        # this transmitter could be better
                        # check the rssi
                        # use leeway to avoid ping pong re-assoc
                        if prev_rssi + 10 < rssi:
                            # it is better
                            print(f"detected better signal for vehicle {vehicle}")
                            print(f"re-associate {prev_transmitter} -> {transmitter}")
                            MY_STORE[vehicle] = [transmitter, rssi]
                            # now re-associate (disconnect/connect command)

                            # get the ids
                            # make sure they match
                            sta_id = int(vehicle[-1]) + 1
                            ap_id = int(transmitter[-1])
                            print(f'{sta_id},{ap_id}')

                            disconnect = (
                                f'{MININET_WIFI_EXE}'
                                f' sta{sta_id} iw dev sta{sta_id}-wlan0 disconnect'
                                f' >/dev/null 2>&1'
                           )
                            connect = (
                                f'{MININET_WIFI_EXE}'
                                f' sta{sta_id} iw dev sta{sta_id}-wlan0 connect ssid-ap{ap_id}'
                                f' >/dev/null 2>&1'
                            )
                            os.system(disconnect)
                            os.system(connect)

                            # make sure ping to h1 still works
                            # before: s3-eth3 goes to ap1
                            # after: s3-eth3 goes to ap2
                            # works bidirectonally
                            reroute = 'ovs-ofctl del-flows s3 "in_port=s3-eth3"'
                            os.system(reroute)

        ##################
        # END MY CODE
        ##################

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

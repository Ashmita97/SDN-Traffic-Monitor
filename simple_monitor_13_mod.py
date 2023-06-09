# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
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

from operator import attrgetter

from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
import network_visualization as net

magic=0
l=[]

class SimpleMonitor13(simple_switch_13.SimpleSwitch13):

    def __init__(self, *args, **kwargs):
        super(SimpleMonitor13, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        global magic,l, new_or_l, new_r_l
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            
            hub.sleep(10)
            l = []
            new_or_l = []
            new_r_l = []
            magic+=10

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.info('datapath         '
                         'in-port  eth-dst           '
                         'out-port packets  bytes')
        self.logger.info('---------------- '
                         '-------- ----------------- '
                         '-------- -------- --------')
        for stat in sorted([flow for flow in body if flow.priority == 1],
                           key=lambda flow: (flow.match['in_port'],
                                             flow.match['eth_dst'])):
            self.logger.info('%016x %8x %17s %8x %8d %8d',
                             ev.msg.datapath.id,
                             stat.match['in_port'], stat.match['eth_dst'],
                             stat.instructions[0].actions[0].port,
                             stat.packet_count, stat.byte_count)
             
    def get_variables(self, l, new_or_l, new_r_l):
    	cli = False
    	net.visualize_topology(cli, l, new_or_l, new_r_l)
    	
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        #global l
        s = []
        self.logger.info('datapath         port     '
                         'rw-pkts  rx-bytes rx-error '
                         'tx-pkts  tx-bytes tx-error link-use Time(s)')
        self.logger.info('---------------- -------- '
                         '-------- -------- -------- '
                         '-------- -------- -------- -------- --------')
        for stat in sorted(body, key=attrgetter('port_no')):
            color = ''
            self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d %.8f %8d',
                             ev.msg.datapath.id, stat.port_no,
                             stat.rx_packets, stat.rx_bytes, stat.rx_errors,
                             stat.tx_packets, stat.tx_bytes, stat.tx_errors,((stat.tx_bytes*8)/magic)/10000000,magic)
            dpid = ev.msg.datapath.id
            link_usage = ((stat.tx_bytes*8)/magic)/10000000
            if link_usage > 0.35 and link_usage < 0.6:
                  color = 'Orange'
            if link_usage > 0.60:
                  color = 'Red'
            s.append({ev.msg.datapath.id:color})
        l.append(s)
        #print('l',l)
        for el in l:
         for ele in el:
          for k,val in ele.items():
          	if val == 'Orange' and k not in new_or_l:
          		k = 's'+ str(k)
          		new_or_l.append(k)
          	if val == 'Red' and k not in new_r_l:
          		k = 's'+ str(k)
          		new_r_l.append(k)
        
        #if magic%30 == 0:
        self.get_variables( l, new_or_l, new_r_l)
        #print('New Orange List',new_or_l)
        #print('New_Red_list',new_r_l)
        #self.logger.info('Color link %s',s) 
        #print('Color link',s)
        #print(l)
        #l = []
    #l = []
        

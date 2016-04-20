#! /usr/bin/env python

# standard modules
import logging
import os
import sys
import time

# import ostinato modules
from ostinato.core import DroneProxy, ost_pb
from ostinato.protocols.tcp_pb2 import Tcp, tcp
from ostinato.protocols.eth2_pb2 import Eth2, eth2
from ostinato.protocols.vlan_pb2 import Vlan, vlan
from ostinato.protocols.ip4_pb2 import Ip4, ip4
from ostinato.protocols.payload_pb2 import Payload, payload
from ostinato.protocols.mac_pb2 import Mac, mac



# initialize the below variables
host_name = '127.0.0.1'
port_number = 8080
tx_port_number = 1
rx_port_number = 7



# setup logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


drone = DroneProxy(host_name, port_number)


try:
    # connect to drone
    log.info('connecting to drone(%s:%d)'
            % (drone.hostName(), drone.portNumber()))
    drone.connect()

    # setup tx port list
    tx_port = ost_pb.PortIdList()
    tx_port.port_id.add().id = tx_port_number;
    rx_port = ost_pb.PortIdList()
    rx_port.port_id.add().id = rx_port_number;

    stream_id = ost_pb.StreamIdList()
    stream_id.port_id.id = tx_port_number
    stream_id.stream_id.add().id = 1
    drone.addStream(stream_id)

    stream_cfg = ost_pb.StreamConfigList()
    stream_cfg.port_id.id = tx_port_number

    # stream 2 test
    # rx-port buff = drone.getCaptureBuffer(rx_port.port_id[0])
    stream_cfg = ost_pb.StreamConfigList()
    stream_cfg.port_id.CopyFrom(tx_port.port_id[0])
    s = stream_cfg.stream.add()
    s.stream_id.id = 1
    s.core.name = 'test'
    s.core.is_enabled = True
    s.control.num_packets = 10000
    s.control.next = ost_pb.StreamControl.e_nw_stop
    s.control.packets_per_sec = 5000

    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kMacFieldNumber

    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kVlanFieldNumber
    p.Extensions[vlan].vlan_tag = 0x64

    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kEth2FieldNumber

    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kIp4FieldNumber

    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kTcpFieldNumber

    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kPayloadFieldNumber

    drone.modifyStream(stream_cfg)
    # clear tx/rx stats
    log.info('clearing tx stats')
    drone.clearStats(tx_port)
    log.info('clearing rx stats')
    drone.clearStats(rx_port)



    log.info('starting transmit')
    drone.startTransmit(tx_port)

    # wait for transmit to finish
    log.info('waiting for transmit to finish ...')

    while True:
        try:
            time.sleep(5)
            tx_stats = drone.getStats(tx_port)
            if tx_stats.port_stats[0].state.is_transmit_on == False:
                break
        except KeyboardInterrupt:
            log.info('transmit interrupted by user')
            break


    # stop transmit and capture
    log.info('stopping transmit')
    drone.stopTransmit(tx_port)

    # get tx stats
    log.info('retreiving stats')
    tx_stats = drone.getStats(tx_port)
    rx_stats = drone.getStats(rx_port)

    if tx_stats.port_stats[0].tx_pkts == rx_stats.port_stats[0].rx_pkts:
        print "traffic test passed"

    elif tx_stats.port_stats[0].tx_pkts == 0:
        raise Exception("Problems with Ostinato")

    else:
        raise Exception("traffic test failed")

    log.info('tx pkts = %d' % (tx_stats.port_stats[0].tx_pkts))
    log.info('rx pkts = %d' % (rx_stats.port_stats[0].rx_pkts))
    #retrieve and dump received packets
    log.info('getting Rx capture buffer')
    buff = drone.getCaptureBuffer(rx_port.port_id[0])
    drone.saveCaptureBuffer(buff, 'capture.pcap')
    os.system('tshark -r capture.pcap')
    os.remove('capture.pcap')

    # delete streams
    log.info('deleting tx_streams')
    drone.deleteStream(stream_id)

    # bye for now
    drone.disconnect()

except Exception as ex:
    log.exception(ex)
    sys.exit(1)

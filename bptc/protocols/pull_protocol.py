import json
import zlib

from math import ceil
from time import strftime, gmtime

from twisted.internet import protocol
from functools import partial
import bptc
from bptc.data.event import Event


class PullServerFactory(protocol.ServerFactory):

    def __init__(self, me_id, hashgraph):
        self.me_id = me_id
        self.hashgraph = hashgraph
        self.protocol = PullServer


class PullServer(protocol.Protocol):

    def connectionMade(self):
        serialized_events = {}
        with self.factory.hashgraph.lock:
            for event_id, event in self.factory.hashgraph.lookup_table.items():
                serialized_events[event_id] = event.to_debug_dict()

        data_string = {'from': self.factory.me_id, 'events': serialized_events}
        data_to_send = zlib.compress(json.dumps(data_string).encode('UTF-8'))
        for i in range(1, (ceil(len(data_to_send) / 65536)) + 1):
            self.transport.write(data_to_send[(i-1) * 65536:min(i*65536, len(data_to_send))])
        self.transport.loseConnection()

    def connectionLost(self, reason):
        return


class PullClientFactory(protocol.ClientFactory):

    def __init__(self, callback_obj, doc, ready):
        self.callback_obj = callback_obj
        self.doc = doc
        self.protocol = PullClient
        self.received_data = b""
        self.ready = ready

    def clientConnectionLost(self, connector, reason):
        return

    def clientConnectionFailed(self, connector, reason):
        print('Connecting failed!')
        self.ready.set()


class PullClient(protocol.Protocol):

    def connectionMade(self):
        print('Connected! Start updating at {}...'.format(strftime("%H:%M:%S", gmtime())))
        return

    def dataReceived(self, data):
        self.factory.received_data += data

    def connectionLost(self, reason):
        if len(self.factory.received_data) == 0:
            print('No data received!')
            return

        try:
            data = zlib.decompress(self.factory.received_data)
        except zlib.error as err:
            bptc.logger.error(err)
        finally:
            self.factory.received_data = b""

        received_data = json.loads(data.decode('UTF-8'))
        from_member = received_data['from']
        s_events = received_data['events']
        events = {}
        for event_id, dict_event in s_events.items():
            events[event_id] = Event.from_debug_dict(dict_event)

        try:
            self.factory.doc.add_next_tick_callback(partial(self.factory.callback_obj.received_data_callback,
                                                            from_member, events))
        except ValueError as e:
            bptc.logger.warn(e)
            pass

        try:
            self.factory.doc.add_next_tick_callback(partial(self.factory.callback_obj.draw, from_member))
        except ValueError as e:
            bptc.logger.warn(e)
            pass

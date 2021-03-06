import datetime
import json
import zlib
from math import ceil
from time import strftime, gmtime
from twisted.internet import protocol
from functools import partial
import bptc
from bptc.data.event import Event
from bptc.utils.toposort import toposort

"""The pull protocol is used between a visualization and a client for pulling the events."""


class PullServerFactory(protocol.ServerFactory):

    def __init__(self, me_id, hashgraph):
        self.me_id = me_id
        self.hashgraph = hashgraph
        self.protocol = PullServer


class PullServer(protocol.Protocol):
    """The pull server handles the pulling of a pull client."""

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

    def __init__(self, callback_obj, doc, ready_event):
        self.callback_obj = callback_obj
        self.doc = doc
        self.protocol = PullClient
        self.received_data = b""
        self.ready_event = ready_event

    def clientConnectionLost(self, connector, reason):
        return

    def clientConnectionFailed(self, connector, reason):
        print('{}: {}'.format(datetime.datetime.now().isoformat(), reason.getErrorMessage()))
        self.ready_event.set()


class PullClient(protocol.Protocol):
    """The pull client pulls from a pull server."""

    def connectionMade(self):
        print('Connected! Start updating at {}...'.format(strftime("%H:%M:%S", gmtime())))
        return

    def dataReceived(self, data):
        self.factory.received_data += data

    def connectionLost(self, reason):
        if len(self.factory.received_data) == 0:
            print('Error: No data received!')
            return

        try:
            data = zlib.decompress(self.factory.received_data)
        except zlib.error:
            print('Error: Incomplete data!')
            self.transport.loseConnection()
            return
        finally:
            self.factory.received_data = b""

        try:
            received_data = json.loads(data.decode('UTF-8'))
        except:
            bptc.logger.warn("Could not parse JSON message")
            return

        from_member = received_data['from']
        s_events = received_data['events']
        events = {}
        for event_id, dict_event in s_events.items():
            events[event_id] = Event.from_debug_dict(dict_event)

        try:
            print('Added next tick callback!')
            self.factory.doc.add_next_tick_callback(partial(self.factory.callback_obj.received_data_callback,
                                                            from_member, toposort(events)))
        except ValueError as e:
            print(e)
            pass
        self.transport.loseConnection()

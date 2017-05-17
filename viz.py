# coding=utf-8
# -*- coding: utf-8 -*-
from itertools import repeat
from random import shuffle
import sys
from base64 import b64encode
from time import localtime, strftime, sleep

from bokeh.io import curdoc
from bokeh.layouts import layout, widgetbox, row, column
from bokeh.plotting import figure
from bokeh.palettes import plasma, small_palettes
from bokeh.models import (
    FixedTicker, Button, ColumnDataSource, PanTool, Scroll,
    RadioButtonGroup, RadioGroup, Arrow, NormalHead, HoverTool, Dimensions, logging, PreText)
from sklavit_nacl.signing import SigningKey

from utils import bfs, randrange
from swirld import HashgraphNetNode, LocalNetwork

R_COLORS = small_palettes['Set2'][8]
# shuffle(R_COLORS)
def round_color(r):
    return R_COLORS[r % 8]

I_COLORS = plasma(256)
def idx_color(r):
    return I_COLORS[r % 256]


class App:
    def __init__(self, n_nodes):
        self.i = 0
        
        self.network = LocalNetwork(n_nodes)
        self.active = self.network.nodes[0]

        self.tbd = {}

        def toggle():
            if play.label == '► Play':
                play.label = '❚❚ Pause'
                curdoc().add_periodic_callback(self.animate, 50)
            else:
                play.label = '► Play'
                curdoc().remove_periodic_callback(self.animate)

        play = Button(label='► Play', width=60)
        play.on_click(toggle)

        do_one_step = Button(label="Do 1 step", width=60)
        do_one_step.on_click(self.animate)


        selector = RadioButtonGroup(
                labels=['Node %i' % i for i in range(n_nodes)], active=0,
                name='Node to inspect')
        selector.on_click(self.sel_node)

        plot = figure(
                plot_height=700, plot_width=900, y_range=(0, 30), x_range=(0, n_nodes - 1),
                tools=[PanTool(dimensions=Dimensions.height),
                       HoverTool(tooltips=[
                           ('round', '@round'), ('hash', '@hash'),
                           ('timestamp', '@time'), ('payload', '@payload'),
                           ('number', '@idx')])])
        plot.xgrid.grid_line_color = None
        plot.xaxis.minor_tick_line_color = None
        plot.ygrid.grid_line_color = None
        plot.yaxis.minor_tick_line_color = None

        self.links_src = ColumnDataSource(data={'x0': [], 'y0': [], 'x1': [],
                                                'y1': [], 'width': []})
        #self.links_rend = plot.add_layout(
        #        Arrow(end=NormalHead(fill_color='black'), x_start='x0', y_start='y0', x_end='x1',
        #        y_end='y1', source=self.links_src))
        self.links_rend = plot.segment(color='#777777',
                x0='x0', y0='y0', x1='x1',
                y1='y1', source=self.links_src, line_width='width')

        self.tr_src = ColumnDataSource(
                data={'x': [], 'y': [], 'round_color': [], 'idx': [],
                    'line_alpha': [], 'round': [], 'hash': [], 'payload': [],
                    'time': []})

        self.tr_rend = plot.circle(x='x', y='y', size=20, color='round_color',
                                   line_alpha='line_alpha', source=self.tr_src, line_width=5)

        self.sel_node(0)

        self.log = PreText(text='')

        control_column = column(play, do_one_step, selector, self.log)
        main_row = row([control_column, plot], sizing_mode='fixed')
        curdoc().add_root(main_row)

    def sel_node(self, new: int):
        node = self.network.nodes[new]
        hashgraph = node.hashgraph
        self.active = node
        self.tbd = {}
        self.tr_src.data, self.links_src.data = self.extract_data(
                hashgraph, bfs((hashgraph.head,), lambda u: u.parents), 0)
        for u, j in tuple(self.tbd.items()):
            if u in hashgraph.famous:
                self.tr_src.data['line_alpha'][j] = 1
            else:
                self.tr_src.data['line_alpha'][j] = 0

            if u in hashgraph.idx:
                self.tr_src.data['round_color'][j] = idx_color(hashgraph.idx[u])
            self.tr_src.data['idx'][j] = hashgraph.idx.get(u)
            if u in hashgraph.idx and u in hashgraph.famous:
                del self.tbd[u]
                print('updated')
        self.tr_src.trigger('data', None, self.tr_src.data)

    def extract_data(self, hashgraph, trs, i):
        tr_data = {'x': [], 'y': [], 'round_color': [], 'idx': [],
                'line_alpha': [], 'round': [], 'hash': [], 'payload': [],
                'time': []}
        links_data = {'x0': [], 'y0': [], 'x1': [], 'y1': [], 'width': []}
        for j, event in enumerate(trs):
            self.tbd[event] = i + j  # idx of event in self.trs
            x = self.network.ids[event.verify_key]  # TODO check usage
            y = event.height
            tr_data['x'].append(x)
            tr_data['y'].append(y)
            tr_data['round_color'].append(round_color(event.round))
            tr_data['round'].append(event.round)
            tr_data['hash'].append(event.id[:8] + "...")
            tr_data['payload'].append("".format(event.d))
            tr_data['time'].append(str(event.t))  # ev.t.strftime("%Y-%m-%d %H:%M:%S"))

            tr_data['idx'].append(None)
            tr_data['line_alpha'].append(None)

            if event.parents:
                links_data['x0'].extend((x, x))
                links_data['y0'].extend((y, y))
                links_data['x1'].append(self.network.ids[event.parents[0].verify_key])  # TODO check usage
                links_data['x1'].append(self.network.ids[event.parents[1].verify_key])  # TODO check usage
                links_data['y1'].append(event.parents[0].height)
                links_data['y1'].append(event.parents[1].height)
                links_data['width'].extend((3, 1))

        return tr_data, links_data

    def animate(self):
        node = self.network.get_random_node()

        self.i += 1

        self.log.text += "Iteration {}\n".format(self.i)

        new = node.heartbeat_callback()

        if node == self.active:
            hashgraph = node.hashgraph

            # TODO remake the following code to include inside hashgraph?
            tr, links = self.extract_data(hashgraph, new, len(self.tr_src.data['x']))
            try:
                self.tr_src.stream(tr)
            except Exception as e:
                self.tr_src.stream(tr)
            self.links_src.stream(links)
            for u, j in tuple(self.tbd.items()):
                if u in hashgraph.famous:
                    self.tr_src.data['line_alpha'][j] = 1
                else:
                    self.tr_src.data['line_alpha'][j] = 0
                if u in hashgraph.idx:
                    self.tr_src.data['round_color'][j] = idx_color(hashgraph.idx[u])
                self.tr_src.data['idx'][j] = hashgraph.idx.get(u)
                if u in hashgraph.idx and u in hashgraph.famous:
                    del self.tbd[u]
                    print('updated')
            self.tr_src.trigger('data', None, self.tr_src.data)


App(int(sys.argv[1]))

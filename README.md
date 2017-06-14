# BPT Hashgraph

## Setup Linux
```shell
  sudo apt install cython python-dev libffi-dev libgl1-mesa-dev
  pip install -r requirements.txt
```
You also need the libsodium.so for libnacl - Therefore download it from [here](https://download.libsodium.org/libsodium/releases/).

## Start UI client
```shell
  python main.py
  # Or you can execute
  python -m bptc.client
```

## Build Android package
Install Buildozer following the instructions on its Github page. Note the difference between
installation for Python 2 and Python 3.

Look at the [documentation](http://buildozer.readthedocs.io/en/latest/installation.html)
for installing the right dependencies for your OS. Buildozer and its dependency Crystax
NDK require about 15 GB disk space.

After setting up Buildozer run:

```shell
  buildozer android debug deploy run
```

## Execution
Starting bokeh
```shell
  bokeh serve viz.py
```

Starting bokeh and browser
```shell
  bokeh serve --show viz.py
```


# py-swirld

Just fooling around the _Swirlds_ byzantine consensus algorithm by Leemon Baird
([whitepaper](http://www.swirlds.com/wp-content/uploads/2016/07/SWIRLDS-TR-2016-01.pdf)
available) in python. _Swirlds_ is an algorithm constructing a strongly
consistent and partition tolerant, peer-to-peer append-only log.

It seems to work as intended to me but don't take it for granted!

## Dependencies

- python=3.5
- [pyNaCl] (https://pypi.python.org/pypi/PyNaCl) for the crypto
  PyNaCl relies on [libsodium] (https://github.com/jedisct1/libsodium), a portable C library.
  And copy is bundled with PyNaCl! ([pysodium](https://pypi.python.org/pypi/pysodium) does not have one.)
- [bokeh](http://bokeh.pydata.org/en/latest/) for the analysis and interactive visualization

## Usage / High-level explanations

I don't think this is any useful to you if you don't plan to understand how the
algorithm works so you should read the whitepaper first. After that, the
implementation is _quite_ straightforward: the code is divided in the same
functions as presented in the paper:

- The main loop (which is a coroutine to enable step by step evaluation and
  avoid threads).
- `sync(<remote-node-id>, <payload-to-embed>)` which queries the remote node
  and updates local data.
- `divide_rounds` which sets round number and witnessness for the new
  transactions.
- `decide_fame` which does the voting stuff.
- `find_order` which update the final transactions list according to new
  election results.

Everything is packed into a `Node` class which is initialized with it's signing
keypair and with a dictionary mapping a node ID (it's public key) to some mean
to query data from him (the `ask_sync` method). Note that for simplicity, a
node is included in it's own mapping.

You can fiddle directly with that code or try out my nice interactive
visualizations to see how the network evolves in real time with:

```shell
bokeh serve --show viz.py --args <number of nodes>
```

This will start locally the specified number of nodes and by pressing the
_play_ button it will start choosing one at random every few milliseconds and do
a mainloop step. The color indicates the round number (it's just a random
color, the only thing is that transactions with the same round have the same
color).

## Algorithm details

Actually, I didn't implement the algorithm completely straightforward with full
graph traversals everywhere and big loops over all nodes. The main specificity
I introduced is a mapping I named `can_see`. It is updated along the round
number in `divide_rounds` and stores for each transaction a dictionary that
maps to each node the id of the latest (highest) transaction from that node
this transaction can see (if there is one). It is easily updated by a
recurrence relation and enables to quickly seeable and strongly seeable
transactions.

With nn and nt respectively the number of nodes and the number of transactions,
this datastructure adds up O(nn\*nt) space and enables to compute the set of
witnesses a transaction can strongly see in O(nn^2).

## IPFS

A variant lives in the `ipfs` branch. This variant uses [IPFS](http://ipfs.io/)
as a backend to store the hashgraph. Indeed a swirlds _hashgraph_ is just the
same as an IPFS _merkle DAG_. This enables global deduplication of the
hashgraph (bandwith and computation efficient syncing between members). The
syncing process is just about getting the head of the remote member. As the
head of a member is stored in an IPNS record, this code is currently very slow,
but a lot of work is currently going on on the IPFS side to improve IPNS (_cf_
[IPRS](https://github.com/ipfs/go-iprs)).

## Work In Progress

- The interactive visualization is still rather crude.
- There is no strong fork detection when syncing.
- There is no real networking (the _communication_ is really just a method
  call). This should not be complicated to implement, but I will have to bring
  in threads, locks and stuff like that. I am actually thinking about embedding
  the hashgraph in [IPFS](http://ipfs.io/) objects as it fits perfectly. This
  would enable to just drop any crypto and network operation as IPFS already
  takes care of it well.

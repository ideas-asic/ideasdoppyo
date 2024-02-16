# ideasdoppyo
This python package is a python implementation of the IDEAS Doppio protocol.

The Doppio protocol is used to communicate with IDEAS ASIC development
boards and some other IDEAS products via TCP/IP.

## Usage

To use it as part of your code:

```python 
import sys, os
sys.path.append('.\\..\\src\\ideasdoppyo')
from tcphandler import TCPhandler
```

This project can be installed directly using pip, write in your terminal:
```python 
python -m pip install git+https://github.com/ideas-asic/ideasdoppyo.git
```

Then import in your script using, e.g.,:
```python 
from ideasdoppyo.tcphandler import TCPhandler
from ideasdoppyo.udphandler import UDPhandler
```

_numpy_ is the only external python package required.

## Feedback and Development

This software is provided on a best effort basis as an additional tool
to users.

Please don't hesitate with registering feature requests and bug reports on
the GitHub issue tracker for this repository.

## Integrated Detector Electronics AS

IDEAS (https://ideas.no/) is based in Oslo, Norway.

It was founded in 1992 by a group of scientists and engineers from The
European Organization for Nuclear Research (CERN) and the University
of Oslo. With a strong background in applied physics, radiation
detector instrumentation, and electrical engineering, the team has
since been designing and manufacturing custom-made integrated circuits
and sub-systems for a wide range of radiation detectors and imaging
systems, used in medical imaging, industrial scanning, nuclear
science, and astrophysics.

Our integrated circuits feature low-noise, low-power amplifiers for
the readout of various detectors, such as cadmium zinc telluride
(CZT), cadmium telluride (CdTe), thallium bromide (TlBr), silicon,
photomultiplier tubes (PMTs), multi-channel plates (MCPs) and
avalanche photo diodes (APDs), silicon photomultipliers (SiPMs), and
multi-pixel photon counters (MPPCs). For space applications, these
circuits are specifically designed for radiation hardening against
latch-up and single-event upset. Recent ASIC designs support
spectroscopic photon counting, dose monitoring, continuous waveform
sampling, cryogenic operations, and readout of infrared focal-plane
arrays.

#!/usr/bin/env python
"""{ShortDescription}

{ExtendedDescription}


# QuickStart

Use the ``run_monitor`` test harness to drive this basic modules and begin your
plugin development cycle.

    $ python -m scalyr_agent.run_monitor -p /path/to/scalyr_agent/builtin_monitors

# Credits & License
Author: Scott Sullivan '<guy.hoozdis@gmail.com>'
License: Apache 2.0

------------------------------------------------------------------------
Copyright 2014 Scalyr Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
------------------------------------------------------------------------
"""

__author__ = "Scott Sullivan '<guy.hoozdis@gmail.com>'"
__version__ = "0.0.1"
__monitor__ = __name__


import sys

from scalyr_agent import ScalyrMonitor
from scalyr_agent import define_config_option, define_metric, define_log_field


try:
    import psutil
except ImportError:
    psutil = None


#
# Monitor Configuration - defines the runtime environment and resources available
#
CONFIG_OPTIONS = [
    dict(
        option_name='module',
        option_description='A ScalyrAgent plugin monitor module',
        convert_to=str,
        required_option=True,
        default='linux_process_metrics'
    ),
    dict(
        option_name='commandline',
        option_description='A regular expression which will match the command line of the process you\'re interested '
        'in, as shown in the output of ``ps aux``. (If multiple processes match the same command line pattern, '
        'only one will be monitored.)',
        default=None,
        convert_to=str
    ),
    dict(
        option_name='pid',
        option_description='The pid of the process from which the monitor instance will collect metrics.  This is '
        'ignored if the ``commandline`` is specified.',
        default='$$',
        convert_to=str
    ),
    dict(
        option_name='id',
        option_description='Included in each log message generated by this monitor, as a field named ``instance``. '
        'Allows you to distinguish between values recorded by different monitors.',
        required_option=True,
        convert_to=str
    )
]

_ = [define_config_option(__monitor__, **option) for option in CONFIG_OPTIONS] # pylint: disable=star-args
# # End Monitor Configuration
# #########################################################################################




# #########################################################################################
# #########################################################################################
# ## System Metrics / Dimensions -
# ##
# ##    Metrics define the capibilities of this monitor.  These some utility functions
# ##    along with the list(s) of metrics themselves.
# ##
def _gather_metric(method, attribute=None):
    """Curry arbitrary process metric extraction

    @param method: a callable member of the process object interface
    @param attribute: an optional data member, of the data structure returned by ``method``

    @type method callable
    @type attribute str
    """
    doc = "Extract the {} attribute from the given process object".format
    if attribute:
        doc = "Extract the {}().{} attribute from the given process object".format

    def gather_metric():
        """Dynamically Generated """
        metric = methodcaller(method)   # pylint: disable=redefined-outer-name
        value = metric(psutil)
        if attribute:
            value = attrgetter(attribute)(value)
        yield value

    gather_metric.__doc__ = doc(method, attribute)
    return gather_metric


def partion_disk_usage():
    mountpoints_initialized = [0]
    mountpoints = []

    def gather_metric():
        if mountpoints_initialized[0] == 0:
            for p in psutil.disk_partitions():
                mountpoints.append(p.mountpoint)
            mountpoints_initialized[0] = 1

        for mountpoint in mountpoints:
            try:
                diskusage = psutil.disk_usage(mountpoint)
                yield "{}={}%".format(mountpoint, diskusage.percent)
            except OSError:
                # Certain partitions, like a CD/DVD drive, are expected to fail
                pass

    gather_metric.__doc__ = "TODO"
    return gather_metric


def uptime(start_time):
    """Calculate the difference between now() and the given create_time.

    @param start_time: milliseconds passed since 'event' (not since epoc)
    @type float
    """
    from datetime import datetime
    return datetime.now() - datetime.fromtimestamp(start_time)


try:
    from operator import methodcaller, attrgetter
except ImportError:
    def methodcaller(name, *args, **kwargs):
        def caller(obj):
            return getattr(obj, name)(*args, **kwargs)
        return caller

try:
    from collections import namedtuple
    METRIC = namedtuple('METRIC', 'config dispatch')
except ImportError:

    class NamedTupleHack(object):
        def __init__(self, *args):
            self._typename = args[0]
            self._fieldnames = args[1:]
        def __str__(self):
            return "<{typename}: ({fieldnames})...>".format(self._typename, self._fieldnames[0])
    METRIC = NamedTupleHack('Metric', 'config dispatch')


METRIC_CONFIG = dict    # pylint: disable=invalid-name
GATHER_METRIC = _gather_metric


# pylint: disable=bad-whitespace
# =================================================================================
# ============================    System CPU    ===================================
# =================================================================================
_SYSTEM_CPU_METRICS = [
    METRIC( ## ------------------  User CPU ----------------------------
        METRIC_CONFIG(
            metric_name     = 'winsys.cpu',
            description     = 'The seconds the cpu has spent in the given mode.',
            category        = 'general',
            unit            = 'secs:1.00',
            cumulative      = True,
            extra_fields    = {
                'type': 'User'
            },
        ),
        GATHER_METRIC('cpu_times', 'user')
    ),
    METRIC( ## ------------------  System CPU ----------------------------
        METRIC_CONFIG(
            metric_name     = 'winsys.cpu',
            description     = 'The seconds the cpu has spent in the given mode.',
            category        = 'general',
            unit            = 'secs:1.00',
            cumulative      = True,
            extra_fields    = {
                'type': 'system'
            },
        ),
        GATHER_METRIC('cpu_times', 'system')
    ),
    METRIC( ## ------------------  Idle CPU ----------------------------
        METRIC_CONFIG(
            metric_name     = 'winsys.cpu',
            description     = 'The seconds the cpu has spent in the given mode.',
            category        = 'general',
            unit            = 'secs:1.00',
            cumulative      = True,
            extra_fields    = {
                'type': 'idle'
            },
        ),
        GATHER_METRIC('cpu_times', 'idle')
    ),

    # TODO: Additional attributes for this section
    #  * ...
]


# =================================================================================
# ========================    UPTIME METRICS     ===============================
# =================================================================================
_UPTIME_METRICS = [

    METRIC( ## ------------------  System Boot Time   ----------------------------
        METRIC_CONFIG(
            metric_name     = 'proc.uptime',
            description     = 'System boot time in seconds since the epoch.',
            category        = 'general',
            unit            = 'sec',
            cumulative      = True,
            extra_fields    = {}
        ),
        GATHER_METRIC('boot_time', None)
    ),

    # TODO: Additional attributes for this section
    #  * ...
]

# =================================================================================
# ========================    Virtual Memory    ===============================
# =================================================================================
_VIRTUAL_MEMORY_METRICS = [

    METRIC( ## ------------------    Total Virtual Memory    ----------------------------
        METRIC_CONFIG(
            metric_name     = 'memory.virtual',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            #cumulative      = {cumulative},
            extra_fields    = {
                'type': 'total',
            }
        ),
        GATHER_METRIC('virtual_memory', 'total')
    ),
    METRIC( ## ------------------    Used Virtual Memory    ----------------------------
        METRIC_CONFIG(
            metric_name     = 'memory.virtual',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            #cumulative      = {cumulative},
            extra_fields    = {
                'type': 'used',
            }
        ),
        GATHER_METRIC('virtual_memory', 'used')
    ),
    METRIC( ## ------------------    Free Virtual Memory    ----------------------------
        METRIC_CONFIG(
            metric_name     = 'memory.virtual',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            #cumulative      = {cumulative},
            extra_fields    = {
                'type': 'free',
            }
        ),
        GATHER_METRIC('virtual_memory', 'free')
    ),


    # TODO: Additional attributes for this section
    #  * ...
]

# =================================================================================
# ========================    Physical Memory    ===============================
# =================================================================================
_PHYSICAL_MEMORY_METRICS = [

    METRIC( ## ------------------    Total Physical Memory    ----------------------------
        METRIC_CONFIG(
            metric_name     = 'memory.physical',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            #cumulative      = {cumulative},
            extra_fields    = {
                'type': 'total',
            }
        ),
        GATHER_METRIC('virtual_memory', 'total')
    ),
    METRIC( ## ------------------    Used Physical Memory    ----------------------------
        METRIC_CONFIG(
            metric_name     = 'memory.physical',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            #cumulative      = {cumulative},
            extra_fields    = {
                'type': 'used',
            }
        ),
        GATHER_METRIC('virtual_memory', 'used')
    ),
    METRIC( ## ------------------    Free Physical Memory    ----------------------------
        METRIC_CONFIG(
            metric_name     = 'memory.physical',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            #cumulative      = {cumulative},
            extra_fields    = {
                'type': 'free',
            }
        ),
        GATHER_METRIC('virtual_memory', 'free')
    ),


    # TODO: Additional attributes for this section
    #  * ...
]


# =================================================================================
# ========================    Network IO Counters   ===============================
# =================================================================================
_NETWORK_IO_METRICS = [

    METRIC( ## ------------------   Bytes Sent  ----------------------------
        METRIC_CONFIG(
            metric_name     = 'network.io.bytes',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            cumulative      = True,
            extra_fields    = {
                'direction': 'sent',
                'iface': ''
            }
        ),
        GATHER_METRIC('network_io_counters', 'bytes_sent')
    ),
    METRIC( ## ------------------   Bytes Recv  ----------------------------
        METRIC_CONFIG(
            metric_name     = 'network.io.bytes',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            cumulative      = True,
            extra_fields    = {
                'direction': 'recv',
                'iface': ''
            }
        ),
        GATHER_METRIC('network_io_counters', 'bytes_recv')
    ),
    METRIC( ## ------------------   Packets Sent  ----------------------------
        METRIC_CONFIG(
            metric_name     = 'network.io.packets',
            description     = '{description}',
            category        = 'general',
            unit            = 'packets',
            cumulative      = True,
            extra_fields    = {
                'direction': 'sent',
                'iface': ''
            }
        ),
        GATHER_METRIC('network_io_counters', 'packets_sent')
    ),
    METRIC( ## ------------------   Packets Recv  ----------------------------
        METRIC_CONFIG(
            metric_name     = 'network.io.packets',
            description     = '{description}',
            category        = 'general',
            unit            = 'packets',
            cumulative      = True,
            extra_fields    = {
                'direction': 'recv',
                'iface': ''
            }
        ),
        GATHER_METRIC('network_io_counters', 'packets_recv')
    ),


    # TODO: Additional attributes for this section
    #  * dropped packets in/out
    #  * error packets in/out
    #  * various interfaces
]


# =================================================================================
# ========================     Disk IO Counters     ===============================
# =================================================================================
_DISK_IO_METRICS = [

    METRIC( ## ------------------   Disk Bytes Read    ----------------------------
        METRIC_CONFIG(
            metric_name     = 'disk.io',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            cumulative      = True,
            extra_fields    = {
                'type': 'read'
            }
        ),
        GATHER_METRIC('disk_io_counters', 'read_bytes')
    ),
    METRIC( ## ------------------  Disk Bytes Written  ----------------------------
        METRIC_CONFIG(
            metric_name     = 'disk.io',
            description     = '{description}',
            category        = 'general',
            unit            = 'bytes',
            cumulative      = True,
            extra_fields    = {
                'type': 'write'
            }
        ),
        GATHER_METRIC('disk_io_counters', 'write_bytes')
    ),
    METRIC( ## ------------------   Disk Read Count    ----------------------------
        METRIC_CONFIG(
            metric_name     = 'disk.io',
            description     = '{description}',
            category        = 'general',
            unit            = 'count',
            cumulative      = True,
            extra_fields    = {
                'type': 'read'
            }
        ),
        GATHER_METRIC('disk_io_counters', 'read_count')
    ),
    METRIC( ## ------------------   Disk Write Count    ----------------------------
        METRIC_CONFIG(
            metric_name     = 'disk.io',
            description     = '{description}',
            category        = 'general',
            unit            = 'count',
            cumulative      = True,
            extra_fields    = {
                'type': 'write'
            }
        ),
        GATHER_METRIC('disk_io_counters', 'write_count')
    ),


    # TODO: Additional attributes for this section
    #  * ...
]

# TODO: Add Disk Usage per partion

_DISK_USAGE_METRICS = [
    METRIC(
        METRIC_CONFIG(
            metric_name     = 'disk.usage',
            description     = 'Disk usage percentage for each partition',
            category        = 'general',
            unit            = 'percent',
            cumulative      = True,
            extra_fields    = {}
        ),
        partion_disk_usage()
    ),
]
# pylint: enable=bad-whitespace

METRICS = _SYSTEM_CPU_METRICS + _UPTIME_METRICS + _VIRTUAL_MEMORY_METRICS + _PHYSICAL_MEMORY_METRICS + _NETWORK_IO_METRICS + _DISK_IO_METRICS + _DISK_USAGE_METRICS
_ = [define_metric(__monitor__, **metric.config) for metric in METRICS]     # pylint: disable=star-args




#
# Logging / Reporting - defines the method and content in which the metrics are reported.
#
define_log_field(__monitor__, 'monitor', 'Always ``linux_process_metrics``.')
define_log_field(__monitor__, 'instance', 'The ``id`` value from the monitor configuration, e.g. ``tomcat``.')
define_log_field(__monitor__, 'app', 'Same as ``instance``; provided for compatibility with the original Scalyr Agent.')
define_log_field(__monitor__, 'metric', 'The name of a metric being measured, e.g. "app.cpu".')
define_log_field(__monitor__, 'value', 'The metric value.')





class SystemMonitor(ScalyrMonitor):
    """Windows System Metrics"""

    def __init__(self, config, logger, **kwargs):
        """TODO: Fucntion documentation
        """
        sampling_rate = kwargs.get('sampling_rate', 30)
        super(SystemMonitor, self).__init__(config, logger, sampling_rate)


    def gather_sample(self):
        """TODO: Fucntion documentation
        """
        try:
            for idx, metric in enumerate(METRICS):
                metric_name = metric.config['metric_name']
                logmsg = "Sampled %s at %s %d-%d".format
                for metric_value in metric.dispatch():
                    self._logger.emit_value(
                        metric_name,
                        metric_value,
                        extra_fields=metric.config['extra_fields']
                    )
        except:
            self.__process = None
            exc_type, exc_value, traceback = sys.exc_info()
            print exc_type, exc_value
            import traceback
            traceback.print_exc()

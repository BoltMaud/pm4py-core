from copy import copy
from pm4py.models.petri import semantics
from pm4py.models.petri.petrinet import PetriNet
from statistics import mean, median
from math import log, e

MAX_EDGE_PENWIDTH_GRAPHVIZ = 2.6
MIN_EDGE_PENWIDTH_GRAPHVIZ = 1.0

def single_element_statistics(log, net, initial_marking, activatedTransitions, activity_key="concept:name", timestamp_key="time:timestamp"):
    """
    Get single Petrinet element statistics

    Parameters
    ------------
    log
        Log
    net
        Petri net
    initial_marking
        Initial marking
    activatedTransitions
        Activated transitions
    activity_key
        Activity key (must be specified if different from concept:name)
    timestamp_key
        Timestamp key (must be specified if different from time:timestamp)

    Returns
    ------------
    statistics
        Petri net element statistics (frequency, unaggregated performance)
    """
    statistics = {}
    mapping = {}
    for trans in net.transitions:
        if trans.label is not None:
            mapping[trans.label] = trans
    i = 0
    while i < len(log):
        if len(log[i]) > 0:
            tracePlaceStats = 0
            tracePlaceStats = {}
            if timestamp_key in log[i][0]:
                currentTimestamp = log[i][0][timestamp_key]
            else:
                currentTimestamp = 0
            j = 0
            marking = copy(initial_marking)
            for place in marking:
                if not place in statistics:
                    statistics[place] = {"count":0}
                statistics[place]["count"] = statistics[place]["count"] + marking[place]
                if not(currentTimestamp == 0):
                    tracePlaceStats[place] = [currentTimestamp] * marking[place]
            actTrans = activatedTransitions[i]
            z = 0
            while z < len(actTrans):
                trans = actTrans[z]
                if not trans in statistics:
                    statistics[trans] = {"count":0}
                statistics[trans]["count"] = statistics[trans]["count"] + 1

                new_marking = semantics.execute(trans, net, marking)
                if not new_marking:
                    break
                marking_diff = set(new_marking).difference(set(marking))
                for place in marking_diff:
                    if not place in statistics:
                        statistics[place] = {"count": 0}
                    statistics[place]["count"] = statistics[place]["count"] + max(new_marking[place] - marking[place], 1)
                marking = new_marking
                if j < len(log[i]):
                    if timestamp_key in log[i][j]:
                        currentTimestamp = log[i][j][timestamp_key]
                    if trans.label == log[i][j][activity_key]:
                        j = j + 1
                for arc in trans.in_arcs:
                    sourcePlace = arc.source
                    if not arc in statistics:
                        statistics[arc] = {"performance": [], "count": 0}
                    statistics[arc]["count"] = statistics[arc]["count"] + 1
                    if sourcePlace in tracePlaceStats and tracePlaceStats[sourcePlace]:
                        statistics[arc]["performance"].append((currentTimestamp - tracePlaceStats[sourcePlace][0]).total_seconds())
                        del tracePlaceStats[sourcePlace][0]
                for arc in trans.out_arcs:
                    targetPlace = arc.target
                    if not arc in statistics:
                        statistics[arc] = {"performance": [], "count": 0}
                    statistics[arc]["count"] = statistics[arc]["count"] + 1
                    if not currentTimestamp == 0:
                        if not targetPlace in tracePlaceStats:
                            tracePlaceStats[targetPlace] = []
                        tracePlaceStats[targetPlace].append(currentTimestamp)
                z = z + 1
        i = i + 1
    return statistics

def human_readable_stat(c):
    """
    Transform a timedelta expressed in seconds into a human readable string

    Parameters
    ----------
    c
        Timedelta expressed in seconds

    Returns
    ----------
    string
        Human readable string
    """
    c = int(c)
    days = c // 86400
    hours = c // 3600 % 24
    minutes = c // 60 % 60
    seconds = c % 60
    if days > 0:
        return str(days)+"D"
    if hours > 0:
        return str(hours)+"h"
    if minutes > 0:
        return str(minutes)+"m"
    return str(seconds)+"s"

def find_min_max_trans_frequency(statistics):
    """
    Find minimum and maximum transition frequency

    Parameters
    -----------
    statistics
        Element statistics

    Returns
    ----------
    min_frequency
        Minimum transition frequency (in the replay)
    max_frequency
        Maximum transition frequency (in the replay)
    """
    min_frequency = 9999999999
    max_frequency = 0
    for elem in statistics.keys():
        if type(elem) is PetriNet.Transition:
            if statistics[elem]["count"] < min_frequency:
                min_frequency = statistics[elem]["count"]
            if statistics[elem]["count"] > max_frequency:
                max_frequency = statistics[elem]["count"]
    return min_frequency, max_frequency

def find_min_max_arc_frequency(statistics):
    """
    Find minimum and maximum arc frequency

    Parameters
    -----------
    statistics
        Element statistics

    Returns
    -----------
    min_frequency
        Minimum arc frequency
    max_frequency
        Maximum arc frequency
    """
    min_frequency = 9999999999
    max_frequency = 0
    for elem in statistics.keys():
        if type(elem) is PetriNet.Arc:
            if statistics[elem]["count"] < min_frequency:
                min_frequency = statistics[elem]["count"]
            if statistics[elem]["count"] > max_frequency:
                max_frequency = statistics[elem]["count"]
    return min_frequency, max_frequency

def find_min_max_arc_performance(statistics):
    """
    Find minimum and maximum arc performance

    Parameters
    -----------
    statistics
        Element statistics

    Returns
    -----------
    min_performance
        Minimum performance
    max_performance
        Maximum performance
    """
    min_performance = 9999999999
    max_performance = 0
    for elem in statistics.keys():
        if type(elem) is PetriNet.Arc:
            if statistics[elem]["performance"]:
                aggr_stat = mean(statistics[elem]["performance"])
                if aggr_stat < min_performance:
                    min_performance = aggr_stat
                if aggr_stat > max_performance:
                    max_performance = aggr_stat
    return min_performance, max_performance

def get_arc_penwidth(arc_measure, min_arc_measure, max_arc_measure):
    """
    Calculate arc width given the current arc measure value, the minimum arc measure value and the maximum arc measure value

    Parameters
    -----------
    arc_measure
        Current arc measure value
    min_arc_measure
        Minimum measure value among all arcs
    max_arc_measure
        Maximum measure value among all arcs

    Returns
    -----------
    penwidth
        Current arc width in the graph
    """
    return MIN_EDGE_PENWIDTH_GRAPHVIZ + (MAX_EDGE_PENWIDTH_GRAPHVIZ - MIN_EDGE_PENWIDTH_GRAPHVIZ) * (arc_measure - min_arc_measure)/(max_arc_measure - min_arc_measure + 0.00001)

def get_trans_freq_color(trans_count, min_trans_count, max_trans_count):
    """
    Gets transition frequency color

    Parameters
    ----------
    trans_count
        Current transition count
    min_trans_count
        Minimum transition count
    max_trans_count
        Maximum transition count

    Returns
    ----------
    color
        Frequency color for visible transition
    """
    transBaseColor = int(255 - 100 * (trans_count - min_trans_count)/(max_trans_count - min_trans_count + 0.00001))
    transBaseColorHex = str(hex(transBaseColor))[2:].upper()
    return "#" + transBaseColorHex + transBaseColorHex + "FF"

def aggregate_statistics(statistics, measure="frequency"):
    """
    Gets aggregated statistics

    Parameters
    ----------
    statistics
        Individual element statistics (including unaggregated performances)

    Returns
    ----------
    aggregated_statistics
        Aggregated statistics for arcs, transitions, places
    """
    min_trans_frequency, max_trans_frequency = find_min_max_trans_frequency(statistics)
    min_arc_frequency, max_arc_frequency = find_min_max_arc_frequency(statistics)
    min_arc_performance, max_arc_performance = find_min_max_arc_performance(statistics)
    aggregated_statistics = {}
    for elem in statistics.keys():
        if type(elem) is PetriNet.Arc:
            if measure == "frequency":
                freq = statistics[elem]["count"]
                arc_penwidth = get_arc_penwidth(freq, min_arc_frequency, max_arc_frequency)
                aggregated_statistics[elem] = {"label":str(freq),"penwidth":str(arc_penwidth)}
            elif measure == "performance":
                if statistics[elem]["performance"]:
                    aggr_stat = mean(statistics[elem]["performance"])
                    aggr_stat_hr = human_readable_stat(aggr_stat)
                    arc_penwidth = get_arc_penwidth(aggr_stat, min_arc_performance, max_arc_performance)
                    aggregated_statistics[elem] = {"label":aggr_stat_hr,"penwidth":str(arc_penwidth)}
        elif type(elem) is PetriNet.Transition:
            if measure == "frequency":
                if elem.label is not None:
                    freq = statistics[elem]["count"]
                    color = get_trans_freq_color(freq, min_trans_frequency, max_trans_frequency)
                    aggregated_statistics[elem] = {"label":elem.label+" ("+str(freq)+")", "color": color}
        elif type(elem) is PetriNet.Place:
            pass
    return aggregated_statistics
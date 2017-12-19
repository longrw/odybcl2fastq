import os, re
from odybcl2fastq import UserException
from collections import OrderedDict
from odybcl2fastq import config
import operator
import locale
import numpy
import json
import logging

MIN_UNDETER_CNT = 1000000

def get_summary(output_dir, instrument, sample_sheet_dir):
    """
    parse summary from Stats.json
    """
    stats_path = output_dir + '/Stats/Stats.json'
    if not os.path.exists(stats_path):
        raise UserException('Stats path does not exist: %s' % stats_path)
    with open(stats_path) as f:
        data = json.load(f)
    if not data:
        raise UserException('Stats file empty: %s' % stats_path)
    # parse stats for both hiseq and nextseq
    lanes = get_stats(data)
    lane_sum = []
    if instrument == 'nextseq':
        # no real lanes in nextseq, aggregate the stats

        print(lanes[1])
        lane_sum = get_lane_sum(lanes)
        lanes = aggregate_nextseq_lanes(lanes)
    elif instrument != 'hiseq':
        raise Exception('instrument unknonw: ' + instrument)
    # format lane summary tables
    lanes = format_lane_table(lanes)
    undetermined = format_undetermined(data['UnknownBarcodes'])
    summary_data = {
            'lane_sum': lane_sum,
            'lanes': lanes,
            'instrument': instrument,
            'stats_file': stats_path,
            'sample_sheet': get_sample_sheet(sample_sheet_dir),
            'fastq_url': config.FASTQ_URL,
            'fastq_dir': config.MOUNT_DIR,
            'undetermined': undetermined,
            'undetermined_file': 'Undetermined_SO',
            'sample_sheet_file': sample_sheet_dir
    }
    logging.info("summary_data for email: %s\n" % json.dumps(summary_data))
    return summary_data

def get_sample_sheet(sample_sheet_dir):
    data = ''
    # putting sample sheet in the email is a convenience so don't fail if path
    # for sample sheet is wrong
    if os.path.exists(sample_sheet_dir):
        with open(sample_sheet_dir, 'r') as ss:
            for line in ss:
                data += line + '<br>'
    return data

def get_stats(data):
    stats = OrderedDict()
    # get data on from each lane and samples in the lane
    for lane_info in data['ConversionResults']:
        lane = lane_info['LaneNumber']
        sam_num = 0
        lane_stats = {
                'samples': OrderedDict(),
                'clusters': lane_info['TotalClustersPF'],
                'reads': lane_info['Yield'],
                'sam_num': len(lane_info['DemuxResults'])
        }
        # loop through samples and collect sam_data
        for row in lane_info['DemuxResults']:
            sam = row['SampleId']
            lane_stats['samples'][sam] = get_sam_stats(sam, lane_stats['samples'], row)
        # include a row for undertermined stats
        if 'Undetermined' in lane_info:
            sam = 'undetermined'
            lane_stats['samples'][sam] = get_sam_stats(sam, lane_stats['samples'], lane_info['Undetermined'])
        stats[lane] = lane_stats
    return stats

def get_sam_stats(sam, sam_summary, row):
    if sam not in sam_summary:
        sam_stats = {
                'sample': sam,
                'index': [],
                'yield': [],
                'yield_q30': []
        }
        if 'IndexMetrics' in row:
            for i in row['IndexMetrics']:
                sam_stats['index'].append(i['IndexSequence'])
        else:
            sam_stats['index'].append('undetermined')
    else:
        sam_stats = sam_summary[sam]
    sam_stats['reads'] = float(row['NumberReads'])
    for r in row['ReadMetrics']:
        sam_stats['yield'].append(float(r['Yield']))
        sam_stats['yield_q30'].append(float(r['YieldQ30']))
    return sam_stats

def get_lane_sum(lanes):
    print(lanes[1])
    lane_sum = []
    for lane_num, info in lanes.items():
        reads = 0
        q = []
        for sam in info['samples'].values():
            reads += sam['reads']
        lane_sum.append(OrderedDict({
                'lane': lane_num,
                'reads': locale.format('%d', reads, True),
                '% Bases >= Q30': 'test'
        }))
    print(lane_sum)
    return lane_sum

def format_lane_table(lanes):
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    for lane_num, lane_info in lanes.items():
        lanes[lane_num]['reads'] = locale.format('%d', lane_info['reads'], True)
        for sam_name, sam_info in lane_info['samples'].items():
            row = OrderedDict()
            row['sample'] = sam_info['sample']
            row['index'] = ', '.join(sam_info['index'])
            row['reads'] = locale.format('%d', sam_info['reads'], True)
            row['% >= Q30'] = locale.format('%.2f',numpy.sum(sam_info['yield_q30'])/numpy.sum(sam_info['yield']) * 100, True)
            lanes[lane_num]['samples'][sam_name] = row
    return lanes

def aggregate_nextseq_lanes(lanes):
    lanes_new = {}
    agg = OrderedDict()
    agg_reads = 0
    # aggregate sample stats since there are no real lanes in nextseq
    for lane_num, lane_info in lanes.items():
        for sam_name, sam_info in lane_info['samples'].items():
            if sam_name not in agg:
                agg[sam_name] = {
                        'sample': sam_info['sample'],
                        'index': sam_info['index'],
                        'reads': 0,
                        'yield': [],
                        'yield_q30': []
                }
            agg[sam_name]['reads'] += sam_info['reads']
            agg_reads += sam_info['reads']
            agg[sam_name]['yield'].extend(sam_info['yield'])
            agg[sam_name]['yield_q30'].extend(sam_info['yield_q30'])
    # since nextseq has no lanes put aggregated results in a single "lane"
    lanes_new[1] = {
            'sam_num': lanes[1]['sam_num'],
            'samples': agg,
            'reads': agg_reads
    }
    return lanes_new

def format_undetermined(undeter):
    top = OrderedDict()
    for lane in undeter:
        sorted_undeter = sorted(lane['Barcodes'].items(), key=operator.itemgetter(1), reverse = True)
        for (index, cnt) in sorted_undeter:
            if cnt > MIN_UNDETER_CNT:
                locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
                top[index] = locale.format('%d', cnt, True)
    return dict(top)

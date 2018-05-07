import json
import logging
import requests
from odybcl2fastq import config
from odybcl2fastq.parsers.parse_runinfoxml import get_readinfo_from_runinfo, get_runinfo
from odybcl2fastq.parsers.samplesheet import SampleSheet

class BauerDB(object):
    def __init__(self, sample_sheet_path):
        self.api = config.BAUER_DB['api']
        self.sample_sheet_path = sample_sheet_path

    def insert_run(self, run):
        # insert run
        runinfo_file = run + 'RunInfo.xml'
        run_data = get_runinfo(runinfo_file)
        run_id = self.post_data('runs', run_data)

        # insert read
        reads = get_readinfo_from_runinfo(runinfo_file)
        for i, read in enumerate(reads.values()):
            read_data = {
                    'run': run_id,
                    'number': i,
                    'indexed':  (1 if read['IsIndexedRead'] == 'Y' else 0),
                    'length': read['NumCycles']
            }
            read_id = self.post_data('reads', read_data)

        # insert lanes
        sample_sheet = SampleSheet(self.sample_sheet_path)
        lane_ids = []
        for lane in sample_sheet.lanes:
            lane_data = {
                    'run': run_id,
                    'number': lane,
            }
            lane_ids.append(self.post_data('lanes', lane_data))

        # insert samples
        for sample_name, sample_row in sample_sheet.sections['Data'].items():
            sample_data = {
                    'name': sample_name,
                    'run': run_id,
                    'description': sample_row['Description'],
                    'index1': sample_row['index'],
                    'index2': sample_row['index2']
            }
            if 'Lane' in sample_row:
                lane = lane_ids[sample_row['Lane']]
            else:
                lane = lane_ids[0]
            sample_data['lane'] = lane
            sample_id = self.post_data('samples', sample_data)

    def post_data(self, endpoint, data):
        url = self.api + endpoint + '/'
        r = requests.post(url = url, data = data)
        r.raise_for_status()
        res = json.loads(r.text)
        item_id = res['id']
        logging.info('Loaded data for %s into id %d with data: %s' % (endpoint, item_id, json.dumps(data)))
        return item_id
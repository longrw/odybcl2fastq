import unittest
import os
import json
import gzip
from odybcl2fastq.run import run_cmd

class DemultiplexTests(unittest.TestCase):

    def setUp(self):
        self.sample_data_dir = (os.path.abspath( os.path.dirname( __file__ ) ) +
        '/sample_data/')

    def tearDown(self):
        pass

    def _load_json(self, path):
        obj = {}
        with open(path, 'r') as data:
            obj = json.load(data)
        return obj

    def test_demultiplex(self):
        cmd_path = 'tests/sample_data/cmd.json'
        cmd = self._load_json(cmd_path)
        code, demult_out, demult_err = run_cmd(cmd)
        self.assertTrue(code == 0, 'Error running command %s, %s' % (cmd, demult_err))
        fastq_file = 'MDT1_SI_GA_A11_1_S1_L001_R1_001.fastq.gz'
        fastq_control_path = 'tests/sample_data/' + fastq_file
        fastq_path = '/n/ngsdata/odybcl2fastq_test/171101_D00365_1013_AHYYTWBCXY/bambahmukku/' + fastq_file
        control = gzip.open(fastq_control_path, 'r')
        test = gzip.open(fastq_path, 'r')
        for i in range(7):
            control_ln = next(control)
            test_ln = next(test)
            self.assertTrue(control_ln == test_ln)

if __name__ == '__main__':
    unittest.main()

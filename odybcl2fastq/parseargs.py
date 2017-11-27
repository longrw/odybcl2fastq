#!/usr/bin/env python

# -*- coding: utf-8 -*-

'''
parse arguments to run bcl2fastq, quality metrics analyses
and email reporting

Created on  2017-04-19

@author: Adam Freedman <adamfreedman@fas.harvard.edu>
@copyright: 2017 The Presidents and Fellows of Harvard College. All rights reserved.
@license: GPL v2.0
'''
import sys, os, traceback
import logging
import json
import shutil
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from odybcl2fastq.parsers.makebasemask import extract_basemasks
from odybcl2fastq.emailbuilder.emailbuilder import buildmessage
from odybcl2fastq.parsers import parse_stats
from subprocess import Popen,PIPE
from odybcl2fastq.status_db import StatusDB
from odybcl2fastq.parsers.parse_sample_sheet import sheet_parse

BCL2FASTQ_LOG_DIR = '/n/informatics_external/seq/odybcl2fastq_log/'

def initArgs():
    '''
    Setup arguments with parameterdef for bcl2fastq args
    other than the run and outpur dirs, check envs, parse
    commandline, return args
    '''

    parameterdefs = [
        {
            'name'      : 'TEST',
            'switches'  : ['-t','--test'],
            'required'  : False,
            'help'      : 'run in test mode, log to std out, no not run cmd',
            'action'    : 'store_true',
        },
        {
            'name'      : 'BCL_PROC_THREADS',
            'switches'  : ['-p','--processing-threads'],
            'required'  : False,
            'help'      : 'number threads to process demultiplexed data',
            'default'   : 8,
            'type'      : int,
        },
        {
            'name'      : 'BCL_ADAPTER_STRINGENCY',
            'switches'  : ['--adapter-stringency'],
            'required'  : False,
            'help'      : 'minimum match rate to trigger adapter masking/trimming',
            'default'   : 0.9,
            'type'      : float,
        },
        {
            'name'      : 'BCL_BARCODE_MISMATCHES',
            'switches'  : ['--barcode-mismatches'],
            'required'  : False,
            'help'      : 'number allowed mismatches per index',
            'default'   : 0,
            'type'      : int,
        },
        {
            'name'      : 'BCL_CREATE_INDEXREAD_FASTQ',
            'switches'  : ['--create-fastq-for-index-reads'],
            'required'  : False,
            'action'    : 'store_true',
            'help'      : 'writes fastq files for index read(s)',
        },
        {
            'name'      : 'BCL_IGNORE_MISSING_BCLS',
            'switches'  : ['--ignore-missing-bcls'],
            'required'  : False,
            'help'      : 'missing or corrupt bcl files are ignored',
            'action'    : 'store_true',
        },
        {
            'name'      : 'BCL_IGNORE_MISSING_FILTER',
            'switches'  : ['--ignore-missing-filter'],
            'required'  : False,
            'help'      : 'missing or corrupt filter files are ignored',
            'action'    : 'store_true',
        },
        {
            'name'      : 'BCL_IGNORE_MISSING_POSITIONS',
            'switches'  : ['--ignore-missing-positions'],
            'required'  : False,
            'help'      : 'missing or corrupt positions files are ignored',
            'action'    : 'store_true',
        },
        {
            'name'      : 'BCL_MINIMUM_TRIMMED_READ_LENGTH',
            'switches'  : ['--minimum-trimmed-read-length'],
            'required'  : False,
            'help'      : 'minimum read length after adapter trimming',
            'default'   : 0,
            'type'      : int,
        },
        {
            'name'      : 'BCL_MASK_SHORT_ADAPTER_READS',
            'switches'  : ['--mask-short-adapter-reads'],
            'required'  : False,
            'help'      : 'controls adapter base masking if read below min length post trimming',
            'default'   : 22,
            'type'      : int,
        },
        {
            'name'      : 'BCL_TILES',
            'switches'  : ['--tiles'],
            'required'  : False,
            'help'      : 'regex for tile selection',
            'default'   : False,
            'type'      : str,
        },
        {
            'name'      : 'BCL_WITH_FAILED_READS',
            'switches'  : ['--with-failed-reads'],
            'required'  : False,
            'help'      : 'include all clusters, including non-PF ones',
            'default'   : False,
            'action'    : 'store_true',
        },
        {
            'name'      : 'BCL_WRITE_FASTQ_REVCOMP',
            'switches'  : ['--write-fastq-reverse-complement'],
            'required'  : False,
            'help'      : 'generate fastq files of reverse complements of actual data',
            'default'   : False,
            'action'    : 'store_true',
        },
        {
            'name'      : 'BCL_NO_BGZF',
            'switches'  : ['--no-bgzf-compression'],
            'required'  : False,
            'help'      : 'turn off bgzf compression and use gzip instead for fastq files',
            'default'   : False,
            'action'    : 'store_true',
        },
        {
            'name'      : 'BCL_NO_LANE_SPLITTING',
            'switches'  : ['--no-lane-splitting'],
            'required'  : False,
            'help'      : 'do not split fastq by lane',
            'default'   : False,
            'action'    : 'store_true',
        },
        {
            'name'      : 'BCL_FIND_ADAPTERS_SLIDING_WINDOW',
            'switches'  : ['--find-adapters-with-sliding-window'],
            'required'  : False,
            'help'      : 'use simple sliding window to detec adapters, indels not handled',
            'default'   : False,
            'action'    : 'store_true',
        },
        {
            'name'      : 'BCL_FASTQ_COMPRESSION_LEVEL',
            'switches'  : ['--fastq-compression-level'],
            'required'  : False,
            'help'      : 'use simple sliding window to detec adapters, indels not handled',
            'default'   : 4,
            'type'      : int,
            'choices'   : range(1,10),
        },
        {
            'name'      : 'BCL_RUNFOLDER_DIR',
            'switches'  : ['-R','--runfolder-dir'],
            'required'  : True,
            'help'      : 'path to run folder directory',
            'type'      : str,
        },
        {
            'name'      : 'BCL_OUTPUT_DIR',
            'switches'  : ['-o','--output-dir'],
            'required'  : True,
            'help'      : 'path to demultiplexed output',
            'type'      : str,
        },
        {
            'name'      : 'BCL_SAMPLE_SHEET',
            'switches'  : ['--sample-sheet'],
            'required'  : True,
            'type'      : str,
            'help'      : 'path to sample sheet (if need to call custom sheets, e.g. for a within lane mixed index length run)',
        },
        {
            'name'      : 'RUNINFO_XML',
            'switches'  : '--runinfoxml',
            'required'  : False,
            'type'      : str,
            'help'      : 'path to runinfo xml file',
        },

    ]

    # Check for environment variable values
    # Set to 'default' if they are found
    for parameterdef in parameterdefs:
        if os.environ.get(parameterdef['name'],None) is not None:
            parameterdef['default'] = os.environ.get(parameterdef['name'])

    # Setup argument parser
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('-V', '--version', action='version', version='bcl2fastq2.19')

    # sets up dict with switches as keys and names as values
    switches_to_names={}
    # Use the parameterdefs for the ArgumentParser
    for parameterdef in parameterdefs:
        switches = parameterdef.pop('switches')
        if not isinstance(switches, list):
            switches = [switches]

        # Gotta take it off for add_argument
        name = parameterdef.pop('name')
        parameterdef['dest'] = name
        if 'default' in parameterdef:
            parameterdef['help'] += '  [default: %s]' % parameterdef['default']
        parser.add_argument(*switches,**parameterdef)

        # Gotta put it back on for later
        parameterdef['name'] = name

        # add switch tuple as key, paramterdef name (= destination) as value
        if 'BCL' in parameterdef['name']: # this allows non BCL things to be excluded from switches to names so don't get incorrectly added to cmd line arg
            switches_to_names[tuple(switches)]=parameterdef['name']
    args = parser.parse_args()
    return args, switches_to_names

def get_submissions(sample_sheet, instrument):
    if instrument == 'nextseq':
        return sample_sheet['Header']['Description'].split(',')
    else:
        subs = set()
        for key, row in sample_sheet['Data'].items():
            if row['Description']:
                subs.add(row['Description'])
        return list(subs)

def post_processing(run, subs):
    # update minilims database
    stdb = StatusDB()
    analysis = stdb.insert_analysis(run, ', '.join(subs))
    stdb.link_run_and_subs(run, subs)

def bcl2fastq_build_cmd(args, switches_to_names, mask_list, instrument):
    argdict = vars(args)
    mask_switch = '--use-bases-mask'
    # each mask should be prefaced by the switch
    mask_opt = mask_switch + ' ' + (' ' + mask_switch + ' ').join(mask_list)
    cmdstrings=['bcl2fastq', mask_opt]
    runname = 'test' #TODO: call default? when is it overwritten?
    fout=open('%s.opts' % runname,'w')
    # keeps consistent order of writing
    switch_list=switches_to_names.keys()
    switch_list.sort()
    for switches in switch_list:
        switch=[switch for switch in switches if '--' in switch][0]
        argvalue=str(argdict[switches_to_names[switches]])
        fout.write('%s\t%s\n' % (switch,argvalue))
        # the bit below prevents boolean flags from having values in the cmd
        if argvalue != 'False':
            if argvalue == 'True':
                cmdstrings.append(switch)
            else:
                cmdstrings.append(' '.join([switch,argvalue]))
    fout.close()
    cmdstring=' '.join(cmdstrings)
    return cmdstring

def bcl2fastq_runner(cmd,args):
    logging.info("***** START bcl2fastq *****\n\n")
    run = os.path.basename(args.BCL_RUNFOLDER_DIR)
    output_log = get_output_log(run)
    demult_run = Popen(cmd,shell=True,stderr=PIPE,stdout=PIPE)
    demult_out,demult_err=demult_run.communicate()
    # append to output to log for the run
    with open(output_log, 'a+') as f:
        f.write(demult_err + "\n\n")
    logging.info("***** END bcl2fastq *****\n\n")
    if demult_run.returncode!=0:
        message = 'run %s failed\n see logs here: %s\n%s\n' % (run, output_log,
                demult_err)
        success = False
    else:
        message = 'run %s completed successfully\nsee logs here: %s\n' % (run, output_log)
        success = True
    return success, message

def write_new_sample_sheet(new_samples, sample_sheet, output_suffix):
    new_sample_sheet = sample_sheet.replace('.csv', ('_' + output_suffix + '.csv'))
    input = open(sample_sheet, 'r')
    output = open(new_sample_sheet, 'wb')
    for line in input:
        if not line.startswith('[Data]'):
            output.write(line)
        else:
            output.write(line)
            break
    # print data headers
    output.write(next(input))
    # write new samples to sheet
    new_lines = [(','.join(row.values()) + "\r\n") for row in new_samples]
    output.writelines(new_lines)
    return new_sample_sheet

def bcl2fastq_process_runs():
    args, switches_to_names = initArgs()
    test = ('TEST' in args and args.TEST)
    run = os.path.basename(args.BCL_RUNFOLDER_DIR)
    setup_logging(run, test)
    logging.info("***** START Odybcl2fastq *****\n\n")
    logging.info("Beginning to process run: %s\n args: %s\n" % (run, json.dumps(vars(args))))
    sample_sheet = sheet_parse(args.BCL_SAMPLE_SHEET)
    mask_lists, mask_samples, instrument =  extract_basemasks(sample_sheet['Data'], args.RUNINFO_XML)
    jobs_tot = len(mask_lists)
    if jobs_tot > 1:
        logging.info("This run contains different masks in the same lane and will require %i bcl2fastq jobs" % jobs_tot)
    job_cnt = 1
    sample_sheet_dir = args.BCL_SAMPLE_SHEET
    output_dir = args.BCL_OUTPUT_DIR
    for mask, mask_list in mask_lists.items():
        output_suffix = None
        # if more than one bcl2fastq cmd needed suffix output dir and sample sheet
        if jobs_tot > 1:
            output_suffix = mask.replace(',', '_')
            args.BCL_OUTPUT_DIR = output_dir + '/' + output_suffix
            args.BCL_SAMPLE_SHEET = write_new_sample_sheet(mask_samples[mask], sample_sheet_dir, output_suffix)
        cmd = bcl2fastq_build_cmd(args,
                switches_to_names, mask_list, instrument)
        logging.info("\nJob %i of %i:" % (job_cnt, jobs_tot))
        if test:
            logging.info("Test run, command not run: %s" % cmd)
        else:
            logging.info('Launching bcl2fastq...%s\n' % cmd)
            success, message = bcl2fastq_runner(cmd,args)
            logging.info('message = %s' % message)
            summary_data = {}
            if success: # get data from run to put in the email
                summary_data = parse_stats.get_summary(args.BCL_OUTPUT_DIR, instrument, args.BCL_SAMPLE_SHEET)
                summary_data['run'] = run
                # update lims
                subs = get_submissions(sample_sheet, instrument)
                post_processing(run, subs)
            fromaddr = 'afreedman@fas.harvard.edu'
            toemaillist=['mportermahoney@g.harvard.edu']
            logging.info('Sending email summary to %s\n' % json.dumps(toemaillist))
            buildmessage(message, run, summary_data, fromaddr, toemaillist)
        job_cnt += 1
    logging.info("***** END Odybcl2fastq *****\n\n")

def get_output_log(run):
    return BCL2FASTQ_LOG_DIR + run + '.log'

def setup_logging(run, test):
    # take level from env or INFO
    level = os.getenv('LOGGING_LEVEL', logging.INFO)
    logging.basicConfig(
            filename=get_output_log(run),
            level=level,
            format='%(asctime)s %(filename)s %(message)s'
    )
    if test:
        logging.getLogger().addHandler(logging.StreamHandler())

if __name__ == "__main__":
    try:
        sys.exit(bcl2fastq_process_runs())
    except Exception as e:
        logging.exception(e)
        raise

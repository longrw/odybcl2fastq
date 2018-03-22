from collections import OrderedDict
import logging
import odybcl2fastq.util as util
import re

def sheet_parse(samplesheet=None):
    defaults_by_section = {
        'Header': {
        'IEMFileVersion': None,
        'InvestigatorName': None,
        'ExperimentName': None,
        'Date': None,
        'Workflow': None,
        'Application': None,
        'Assay': None,
        'Description': None,
        'Chemistry': None,},

        'Reads': {
        'read1_length': None,
        'read2_length': None},

        'Settings': {
        'Adapter': None,
        'AdapterRead2': None,
        'MaskAdapter': None,
        'MaskAdapterRead2': None,
        'FindAdaptersWithIndels': 1,
        'Read1EndWithCycle': None,
        'Read2EndWithCycle': None,
        'Read1StartFromCycle': None,
        'Read2StartFromCycle': None,
        'Read1UMILength': None,
        'Read2UMILength': None,
        'Read1UMIStartFromCycle': None,
        'Read2UMIStartFromCycle': None,
        'TrimUMI': 0,
        'ExcludeTiles': None,
        'CreateFastqForIndexReads': 0,
        'ReverseComplement': 0},

        'Data': OrderedDict(),
        }
    ssheet_open = open(samplesheet,'r')
    defaults_section = ''
    for line in ssheet_open:
        linelist = line.strip().split(',')
        if linelist[0] != '':
            if line[0] == '[':
                defaults_section = linelist[0][1:-1]
            else:
                if defaults_section in ['Settings','Header']:
                    defaults_by_section[defaults_section][linelist[0]] = linelist[1]

                elif defaults_section == 'Reads':
                    if defaults_by_section['Reads']['read1_length'] == None:
                        defaults_by_section['Reads']['read1_length'] = linelist[0]
                    elif linelist[0] != '':
                        defaults_by_section['Reads']['read2_length'] = linelist[0]

                else:
                    if 'Sample_ID' in linelist or 'SampleID' in linelist:
                        # TODO: lowercase all fields?
                        data_fields=[field.replace('SampleID','Sample_ID').replace('Index', 'index') for field in linelist if field != '']
                    else:
                        data_dict=OrderedDict(zip(data_fields,linelist[:len(data_fields)]))
                        if 'Lane' in data_dict.keys():
                            name = '%s:%s' % (data_dict['Lane'],data_dict['Sample_ID'])
                        else:
                            name = '%s:%s' % (data_dict['Sample_Project'],data_dict['Sample_ID'])

                        defaults_by_section['Data'][name] = data_dict

    for section_key in ['Settings','Header','Reads']:
        for data_key in defaults_by_section[section_key].keys():
            if defaults_by_section[section_key][data_key] == None:
                defaults_by_section[section_key].pop(data_key)

    if len(defaults_by_section['Header']) == 0:
        #raise ValueError('No header information in sample sheet')
        logging.warning('odbcl2fastq WARNING: no header information in sample sheet')
    if len(defaults_by_section['Settings']) == 0:
        #raise ValueError('No settings information provided in sample sheet')
        logging.warning('odybcl2fastq WARNING: no settings information provided in sample sheet')

    if len(defaults_by_section['Reads']) == 0:
        #raise ValueError('No read information provided in sample sheet')
        logging.warning('odybcl2fastq WARNING: no read information provided in sample sheet')
    if len(defaults_by_section['Data']) == 0:
         raise ValueError('No data for samples present')
    return defaults_by_section

def get_instrument(sample_data):
    if 'Lane' in sample_data.itervalues().next():
        instrument = 'hiseq'
    else:
        instrument = 'nextseq'
    return instrument

def validate_sample_sheet(sample_sheet, sample_sheet_path):
    corrected, sample_sheet['Data'] = validate_sample_names(sample_sheet['Data'])
    if corrected:
        # copy orig sample sheet as backup and record
        util.copy(sample_sheet_path, sample_sheet_path.replace('.csv', '_orig.csv'))
        # write a corrected sheet
        corrected_sample_sheet = write_new_sample_sheet(sample_sheet['Data'].values(), sample_sheet_path, 'corrected')
        # copy corrected to sample sheet path, leave corrected file as record
        util.copy(corrected_sample_sheet, sample_sheet_path)

def validate_sample_names(data):
    corrected = False
    proj_by_sample = {}
    for sam, line in data.items():
        cols_to_validate = ['Sample_ID', 'Sample_Name', 'Sample_Project']
        for col in cols_to_validate:
            # remove any whitespace
            if util.contains_whitespace(line[col]):
                corrected = True
                tmp = line[col]
                line[col] = line[col].replace(' ', '_')
                logging.info('Sample_Sheet corrected, whitespace removed: %s to %s' % (tmp, line[col]))
            # remove any non alphanumeric chars
            if not util.alphanumeric(line[col]):
                corrected = True
                tmp = line[col]
                line[col] = re.sub(r'[^\w-]', '', line[col])
                if not line[col]:
                    raise Exception('For sample_sheet, %s: %s was all non alphanumeric' % (col, line[col]))
                logging.info('Sample_Sheet corrected, non alphanumeric removed: %s to %s' % (tmp, line[col]))
        # if sample project is used, each sample id must belong to only one
        if line['Sample_Project']:
            if not line['Sample_ID'] in proj_by_sample:
                proj_by_sample[line['Sample_ID']] = set()
            proj_by_sample[line['Sample_ID']].add(line['Sample_Project'])
        data[sam] = line
    # rename samples that belong to multiple projects
    for id, projs in proj_by_sample.items():
        if len(projs) > 1:
            sam_proj_corrected, data = rename_samples(id, data)
            corrected = corrected and sam_proj_corrected
    return corrected, data

def rename_samples(id, data):
    corrected = False
    # rename all samples with id by prefixing with submission
    for sam, line in data.items():
        if line['Sample_ID'] == id:
            sub = line['Description']
            new_name = '%s_%s' % (sub, line['Sample_Name'])
            logging.info('renaming sample name: %s to %s' % (line['Sample_ID'],
                new_name))
            line['Sample_ID'] = '%s_%s' % (sub, line['Sample_ID'])
            line['Sample_Name'] = new_name
            corrected = True
        data[sam] = line
    return corrected, data

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
    output.close()
    input.close()
    return new_sample_sheet



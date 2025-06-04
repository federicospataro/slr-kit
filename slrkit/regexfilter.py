import csv
import re
import argparse
import pathlib
from pathlib import Path


def init_argparser():
    """Initialize the command line parser."""
    parser = ArgParse()
    parser.add_argument('input_terms_file', action='store', help="csv file containing 3 columns (first attribute:id, second attribute:term, third attribute: label)\nthis program requires a tab separated csv file", input=True,
            suggest_suffix='_terms.csv')
    parser.add_argument("input_regex_file", type = str, help ="csv file containing 2 columns (first attribute: regex; second attribute: regex description)\nthis program requires a tab separated csv file"
        , default="regex.csv")

    return parser



def csv_file_dictreader(file_to_read : str):
    """Read a csv file and save each row in a dict of a list
    keyword argument:
        file_to_read -- string of the file's name
    """
    item_list = []
    with open(file_to_read, 'r') as infile:
        csv_reader = csv.DictReader(infile, delimiter = '\t')
        for item in csv_reader:
            item_list.append(item)
    return item_list


def csv_file_dictwriter(name : str, list_to_write : list):
    """Write each dict of the input list in a new csv file.
    Fields: id, term, label
    """
    with open(name, "w") as outfile:
        writer = csv.DictWriter(outfile, delimiter = "\t", fieldnames = ['id','term','label'])
        writer.writerow({'id' : 'id', 'term': 'term', 'label' : 'label'})
        for item in list_to_write:
            writer.writerow(item)  


def regex_match_finder(regexes_list : list, terms_list : list):
    """Search for regexes in terms and edit each dict.
    Assign 'regex-noise' or an empty string to the key 'label'.
    Return number of term labelled as 'regex-noise'.
    """
    regex_noised = 0
    for term_dict in terms_list:
        term = term_dict['term']    
        for regex_dict in regexes_list:
            regex = regex_dict['regex']
            if term_dict['label'] == REGEX_NOISE_LABEL or term_dict['label'] == '':
                if re.search(regex, term, re.IGNORECASE):
                    term_dict['label'] = REGEX_NOISE_LABEL
                    regex_noised += 1
                    break
                else:
                    term_dict['label'] = ''   
    return regex_noised


def run_regexfilter(args):
    input_regex_file = str(args.input_regex_file)
    input_terms_file = str(args.input_terms_file)
    regexes = csv_file_dictreader(input_regex_file)
    terms = csv_file_dictreader(input_terms_file)
    regex_noised = regex_match_finder(regexes, terms)
    output_str = Path(input_terms_file).stem + '_Regexnoised' + Path(input_terms_file).suffix 
    csv_file_dictwriter(output_str, terms)


def main():
    parser = init_argparser()
    args = parser.parse_args()
    
    run_regexfilter(args)


if __name__ == '__main__':
    main()
import re
import sys
import requests
import json
import time

import pandas as pd

from slrkit_utils.argument_parser import ArgParse
from pathlib import Path



def init_argparser():
    """Initialize the command line parser."""
    parser = ArgParse()
    parser.add_argument('terms_file', action='store', type=Path,
                    help='path to the terms csv file with the terms to elaborate', input=True,
                    suggest_suffix='_terms.csv')
    parser.add_argument('--score_mode', action='store_true',
                    help='true or false')
    parser.add_argument('model', action='store', type=str,
                    help='name of the llm model to use')
    parser.add_argument('url', action='store', type=str,
                    help='http://localhost:11434/api/generate  for Ollama')
    parser.add_argument('token', action='store', type=str,
                    help='access token to LLM')
    parser.add_argument('threshold', action='store', type=int,
                    help='threshold above which a term is considered garbage (between 1 and 10)', default=7)

    return parser


def base_prompt():
    return """Garbage terms are incomplete or meaningless n-grams, such as fragments like "of a" "in a" or "set of" which depend on additional context to be meaningful, malformed phrases or partial expressions, unnatural n-grams that appear to be cut off or syntactically incomplete; valid terms are well-formed concepts like "machine learning" "language processing" "natural language understanding" even if they contain common words because they are well-formed concepts; return only the clearly garbage terms from the list, separated by commas; be conservative and do not classify a term as garbage unless it is clearly malformed or lacks standalone meaning; identify the garbage terms from the given list: """

def score_prompt():
    return """Garbage terms are terms that by themselves do not have a meaningful meaning, and that should be inserted into a sentence to gain value. Or garbage terms are poorly formed n-grams that carry articles in front or after the words.
For each term below, assign a score from 1 to 10 indicating how likely it is to be a garbage term, where 1 means "definitely not garbage" and 10 means "clearly garbage". Answer (without adding comments) returning the results in the format: term1:score,term2:score,term3:score
The terms you need to score are as follows: """


def run_prompt(prompt_content, url, model, token):

    local=False
    if ("localhost" in url) or ("127.0.0.1" in url):
        local=True

    splitted = prompt_content.split('@')
    
    final_response = ""

    i=0
    for i in range(1,len(splitted)):
        p=splitted[0]+splitted[i]

        if local:
            headers = {'Content-Type': 'application/json'}
            data = {'model': model,'prompt': p, 'stream': False}
        else:
            headers = {'content-type': 'application/json', 'Authorization': 'Bearer '+token}
            data = {'model': model, 'messages': [{'role': 'user', 'content': p}]}

        response = requests.post(url, data=json.dumps(data), headers=headers)
        response_json = json.loads(response.text)

        if local:
            content = response_json["response"]
        else:
            content = response_json['choices'][0]['message']['content']

        content = content.replace("```json", "").replace("```", "")

        final_response = final_response + content

        time.sleep(7)

    return final_response


def read_terms(file_name):
    words_dataset = pd.read_csv(file_name, delimiter='\t', encoding='utf-8')

    terms = words_dataset[
        words_dataset['label'].isna() | (words_dataset['label'].astype(str).str.strip() == '')
    ]['term'].tolist()

    term_str = "@\n"
    cont = 0
    j = 0

    for term in terms:
        
        if len(term.split()) >= 2:  # Only n grams
            term_str += term + ","
            cont += 1
            j += 1

        if j == 500:
            term_str += "\n@\n"
            j = 0

    return term_str


def build_prompt(score_mode, file_name):
    
    if score_mode:
        return score_prompt() + read_terms(file_name)
    
    return base_prompt() + read_terms(file_name)


def assign_labels(score_mode, content, file_name, threshold):
    
    words_dataset = pd.read_csv(file_name, delimiter='\t', encoding='utf-8')

    if score_mode:
        term_value_pairs = [pair.split(':') for pair in term_value_string.split(',')]
        garbage_list = [term for term, value in term_value_pairs if int(value) >= threshold]
    else:
        garbage_list = [term.strip() for term in content.split(',')]
    
    words_dataset.loc[words_dataset['term'].isin(garbage_list), 'label'] = 'garbage'
    words_dataset.to_csv(file_name, sep='\t', index=False)


def run_garbage(args):

    prompt = build_prompt(args.score_mode, args.terms_file)
    print("Prompt:\n"+prompt)
    print("Starting LLM...")
    content = run_prompt(prompt, args.url, args.model, args.token)
    assign_labels(args.score_mode, content, args.terms_file, args.threshold)
    print("Done")


def main():
    parser = init_argparser()
    args = parser.parse_args()
    
    run_garbage(args)


if __name__ == '__main__':
    main()
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
                    suggest_suffix='_tedfkljrms.csv')
    parser.add_argument('postproc_file', action='store', type=Path,
                    help='path to the postprocess csv file with the terms to replace', input=True,
                    suggest_suffix='_postproc.csv')
    parser.add_argument('model', action='store', type=str,
                    help='name of the llm model to use')
    parser.add_argument('url', action='store', type=str,
                    help='http://localhost:11434/api/generate  for Ollama')
    parser.add_argument('token', action='store', type=str,
                    help='access token to LLM')
    parser.add_argument('prompt', action='store', type=str,
                    help='prompt used for asking to llm', default="""I give you a series of terms that can be single or n gram of multiple words (separated by _).
You have to identify which of these terms are synonyms and have the same meaning.
It is not always true that synonyms exist, but if there are you have to find them and they must be correct.
Respond in json format (without adding other comments) grouping together the terms that are synonyms. For example: 
[
  ["data_mining", "text_mining"],
  ["machine_learning", "supervised_learning"]
]
You do NOT have to return all the terms divided into various groups, but only group those that are strongly synonymous.
If n-grams contain the same word within them, it does not mean that they are synonymous.
These are the terms between which you have to find synonyms: """)

    return parser


def run_prompt(prompt_content, url, model, token):

    local=False
    if ("localhost" in url) or ("127.0.0.1" in url):
        local=True
    
    if local:
        headers = {'Content-Type': 'application/json'}
        data = {'model': model,'prompt': prompt_content, 'stream': False}
    else:
        headers = {'content-type': 'application/json', 'Authorization': 'Bearer '+token}
        data = {'model': model, 'messages': [{'role': 'user', 'content': prompt_content}]}

    response = requests.post(url, data=json.dumps(data), headers=headers)
    response_json = json.loads(response.text)

    if local:
        content = response_json["response"]
    else:
        content = response_json['choices'][0]['message']['content']

    content = content.replace("```json", "").replace("```", "")

    return content


def read_terms(file_name):
    words_dataset = pd.read_csv(file_name, delimiter='\t', encoding='utf-8')

    terms = words_dataset[
        words_dataset['label'].astype(str).str.strip().isin(['keyword', 'relevant'])
    ]['term'].tolist()

    term_str = ""
    i=0
    for i in range(len(terms)):
        term_str = term_str + terms[i] + ","

    return term_str



def build_prompt(file_name, prompt):
    return prompt + read_terms(file_name)


def replace_synonyms(content, file_name):
    new_file = file_name

    synonyms = json.loads(content)

    df = pd.read_csv(file_name, sep="\t", encoding="utf-8")

    df['abstract_filtered_new'] = df['abstract_filtered']

    for synonym_group in synonyms:
        all_synonyms = "_".join(synonym_group)

        for replacement in synonym_group:
            df['abstract_filtered'] = df['abstract_filtered'].apply(
                lambda x: re.sub(r'\b' + re.escape(replacement) + r'\b', all_synonyms, x)
            )
    
    df.rename(columns={'abstract_filtered': 'abstract_filtered_old'}, inplace=True)
    df.rename(columns={'abstract_filtered_new': 'abstract_filtered'}, inplace=True)

    df.to_csv(new_file, sep="\t", index=False, encoding="utf-8")


def run_synonyms(args):
    prompt = build_prompt(args.terms_file, args.prompt)
    print("Prompt:\n"+prompt)
    print("Starting LLM...")
    content = run_prompt(prompt, args.url, args.model, args.token)
    print(content)
    replace_synonyms(content, args.postproc_file)
    print("Done")


def main():
    parser = init_argparser()
    args = parser.parse_args()
    
    run_synonyms(args)


if __name__ == '__main__':
    main()
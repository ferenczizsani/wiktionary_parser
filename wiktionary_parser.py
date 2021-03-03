#!/usr/bin/env python3

"""Wiktionary Parser

Usage:
    wiktionary_parser.py (wordpairs|definitions|examples|all) --lang=<wikicode> [--input=<file>] [--output=<path>]

Options:
    -h --help                         Show this screen.
    -i <file> --input=<file>          Input file of Hungarian or Finnish Wiktionary dump.
    -o <path> --output=<path>         Path of the folder to save output [default: output/].
    -l <wikicode> --lang=<wikicode>   Language code of the Wiktionary to be parsed. Either fi or hu.
"""

import sys, os, re
import xml.etree.ElementTree as ET
from docopt import docopt
from collections import defaultdict
import urllib.request
import subprocess


def download_wiktionary(lang):
    data_folder = os.path.join(os.path.dirname(__file__), 'data')
    wik_file = '{}wiktionary-latest-pages-meta-current.xml'.format(lang)
    wik_xml_path = os.path.join(data_folder, wik_file) 
    try:
        os.makedirs(data_folder)
    except OSError as error:
        # folder already exists
        pass
    if not os.path.exists(wik_xml_path):
        if not os.path.exists(os.path.join(data_folder, wik_file + '.bz2')):
            print('Downloading Wiktionary...')
            urllib.request.urlretrieve("http://dumps.wikimedia.org/{}wiktionary/latest/".format(lang) + wik_file + '.bz2', os.path.join(data_folder, wik_file + '.bz2'))
        print('Decompressing Wiktionary dump...')
        subprocess.run(['bzip2', '-d', os.path.join(data_folder, wik_file + '.bz2')])
    return wik_xml_path 


def tag_namespace(elem):
    if elem.tag[0] == "{":
        return elem.tag[1:elem.tag.index("}")]


def read_dump(path):
    mydoc = ET.parse(path)
    root = mydoc.getroot()
    ns = tag_namespace(root)
    nsmap = {'wiki' : ns}
    pages = root.findall('wiki:page', nsmap)
    for page in pages:
        title = page.find('wiki:title', nsmap)
        revision = page.find('wiki:revision', nsmap)
        if revision:
            t = revision.findall('wiki:text', nsmap)
            if len(t) == 1:
                text = t[0].text
                if text:
                    yield title.text, text


def wikpos2ud(line, lang):
    if not line:
        return None
    posud = { 'fi' : {
            'substantiivi' : 'NOUN',
            'substantiivit' : 'NOUN',
            'verbi' : 'VERB',
            'adjektiivi' : 'ADJ',
            'adverbi' : 'ADV',
            'numeraali' : 'NUM',
            'artikkeli' : 'DET',
            'postpositio' : 'ADP',
            'prepositio' : 'ADP',
            'pronomini' : 'PRON',
            'partikkeli' : 'PART',
            'erisnimi' : 'PROPN',
            'interjektio' : 'INTJ',
        },
        'hu' : {
            'fn' : 'NOUN',         'p' : 'NOUN',
            'noun' : 'NOUN',       'ige' : 'VERB',
            'verb' : 'VERB',       'mell' : 'ADJ',
            'adj' : 'ADJ',         'hat' : 'ADV',
            'adv' : 'ADV',         'szn' : 'NUM',
            'ord' : 'NUM',         'num' : 'NUM',
            'prep' : 'ADP',        'kérd' : 'PRON',
            'nm' : 'PRON',         'pron' : 'PRON',
            'geo' : 'PROPN',       'proper noun' : 'PROPN',
            'prop' : 'PROPN',      'ksz' : 'CCONJ',
            'conj' : 'CCONJ',      'interjektio' : 'INTJ',
            }
        }
    return posud[lang].get(line, 'X') 


def save_pairs(wordpairs, lang, output_file=None):
    with open(os.path.join(output_file, 'wordpairs_{}.tsv'.format(lang)), 'w') as f:
        for pos, data in wordpairs.items():
            for tp in data:
                if len(tp) == 2:
                    if lang == 'fi':
                        hu = tp[0]
                        fi = tp[1]
                    else:
                        fi = tp[0]
                        hu = tp[1]
                    f.write('\t'.join([fi, hu, pos]) + '\n')


def save_data(lang, defs, examples, words, output_path):
    save_pairs(words, lang, output_path)
    save_sentences(defs, lang, 'definitions', output_path)
    save_sentences(examples, lang, 'examples', output_path)


def save_sentences(dataset, lang, definition_or_example, output_path):
    filename = '{}_{}.tsv'.format(definition_or_example, lang)
    filepath = os.path.join(output_path, filename)
    with open(filepath, 'w') as f:
        for pos, data in dataset.items():
            for word, sents in data.items():
                for sentence in sents:
                    f.write('\t'.join([pos, word, sentence]) + '\n')


def clean_line(line, mode):
    line = re.sub(r'\[\[[^\|]*(\|([^\]]*))\]\]', r'\2', line)
    common_chars = ["\(''[^)]*''\)", '\{\{[^}]*\}\}', "'''", '\[\[', '\]\]', '</?nowiki/?>', '</?span( [^>]*)?>', '</?tt>', '</?ref([^>]*)?>', '</?su[pb]>', '}}', '{{', '</br>', "''", '<!--.*-->', '\(\)', '^\s*:+', '^\s*,']
    if mode == 'ex':
        for ch in ['#:+ ', '#:+', '</?small>', '</?table>', '</?td( [^>]*)?>', '</?tr>', '</?u>', '\[', '\]']:
            line = re.sub(ch, '', line)
    if mode == 'tr':
        for ch in ['# ', '#\**']:
            line = re.sub(ch, '', line)
    for ch in common_chars:
        line = re.sub(ch, '', line)
    line = re.sub('\s*\.$', '', line)
    return line.strip()


def fi_get_translation(line, title, lang_header, udpos, translations, definitions, wordpairs):
    if re.match(r'^# ?\{\{[^}]*\}\}$', line):
        return
    line = clean_line(line, 'tr')
    if lang_header == '==Suomi==' and line and udpos:
        if 'Malline:' in title:
            return
        if line:
            if title not in definitions[udpos]:
                definitions[udpos][title] = set()
            definitions[udpos][title].add(line)
    elif lang_header == '==Unkari==':
        line = re.split(r',\s*(?![^()]*\))', line)
        trs = [x.strip() for x in line if x.strip()]
        translations.extend(trs)
        if title and translations:
            for trans in translations:
                if ';' in trans:
                    for wordtr in trans.split(';'):
                        wordtr = wordtr.strip()
                        if udpos:
                            wordpairs[udpos].add(tuple([title, wordtr]))
                else:
                    if udpos:
                        wordpairs[udpos].add(tuple([title, trans]))
    return translations, definitions, wordpairs
   

def create_dict(line, udpos, title, output_dict):
    line = clean_line(line, 'ex')
    if line and udpos:
        # erase emojis and unknown characters
        line = ''.join([c if len(c.encode('utf-8')) < 4 else '' for c in line])
        if line:
            if title not in output_dict[udpos]:
                output_dict[udpos][title] = set()
            output_dict[udpos][title].add(line)
    return output_dict

def hu_get_translation_definition(line, udpos, title, entry_lang, translations, wordpairs, definitions):
    line = clean_line(line, 'tr')
    if entry_lang == 'fin':
        line = re.split('(?:,|;)\s*(?![^()]*\))', line)
        trs = [x.strip() for x in line if x.strip()]
        translations.extend(trs)
        if title and udpos:
            for tr in translations:
                wordpairs[udpos].add(tuple([title, tr]))
    elif entry_lang == 'hun':
        definitions = create_dict(line, udpos, title, definitions)
    return translations, wordpairs, definitions


def hu_get_lang_pos(match_obj):
    entry_lang = match_obj.group(1)
    pos = match_obj.group(4).lower()
    if pos.endswith('2'):
        pos = pos[:-1]
    udpos = wikpos2ud(pos, 'hu')
    return entry_lang, udpos


def hu_get_relevant_section(text, langcodes):
    sections = []
    languages = ['{{fin', '{{hun']
    txt = re.split('(' + '|'.join(langcodes) + ')', text)
    langc = None
    for textblock in txt:
        if not textblock:
            continue
        if textblock in languages:
            langc = textblock
        elif langc:
            sections.append(langc + textblock)
            langc = None
    return sections


def fi_get_relevant_section(text):
    sections = []
    languages = ['==Suomi==\n', '==Unkari==\n']
    for lang in languages:
        if lang in text:
            lang_headers = re.findall(r'==\w+==\n', text)
            langind = lang_headers.index(lang)
            lang_headers = lang_headers[langind:langind+2]
            nextlang = lang_headers[1] if len(lang_headers) > 1 else None
            if nextlang:
                relevant_section = ''.join(text.split(lang)[1]).split(nextlang)[0]
            else:
                relevant_section = text.split(lang)[1]
            sections.append(lang + relevant_section)
    return sections


def extract_hu_dict(text, title, langcodes, wordpairs, definitions, example_sents):
    if any([x in title for x in ['Függelék', 'Wikiszótár']]):
        return
    sections = hu_get_relevant_section(text, langcodes)
    entry_lang = None
    udpos = None
    for section in sections:
        translations = []
        for line in section.split('\n'):
            # synonyms
            if line.startswith('{{finsyn') or line.startswith('{{hunsyn'):
                break
            if line.startswith('[[Kategória:'):
                continue
            # part-of-speech
            match_obj = re.match('\{\{((fin)|(hun))(\w+)((\|)?.*)?\}\}', line)
            if match_obj:
                entry_lang, udpos = hu_get_lang_pos(match_obj)
            elif re.match(r'\{\{Fn\}\}', line):
                udpos = wikpos2ud('fn', 'hu')
            elif re.match(r'\{\{fi-(?!decl)', line):
                pos = re.split('\||-|\}', line.split('{{fi-')[1])[0]
                udpos = wikpos2ud(pos, 'hu')
            elif re.match(r'\{\{.*', line):
                continue
            # example sentences
            elif line.startswith('#:'):
                if entry_lang == 'hun':
                    example_sents = create_dict(line, udpos, title, example_sents)
            # translation or definition
            elif line.startswith('#'):
                translations, wordpairs, definitions = hu_get_translation_definition(line, udpos, title, entry_lang, translations, wordpairs, definitions)
    return wordpairs, definitions, example_sents


def extract_fi_dict(text, title, wordpairs, definitions, example_sents):
    relevant_sections = fi_get_relevant_section(text)
    udpos = None
    for relevant_section in relevant_sections:
        translations = []
        section_lines = relevant_section.split('\n')
        lang_header = section_lines[0]
        for line in section_lines[1:]:
            # part-of-speech
            pos = re.match(r'===(\w+)===', line)
            if pos:
                udpos = wikpos2ud(pos.group(1).lower(), 'fi')
            # example sentence
            elif line.startswith('#:'):
                line = clean_line(line, 'ex')
                if lang_header == '==Suomi==' and line:
                    if udpos:
                        if title not in example_sents[udpos]:
                                example_sents[udpos][title] = set()
                        example_sents[udpos][title].add(line)
            # translation or definition
            elif line.startswith('# ') or (line.startswith('#') and not any([line.startswith(x) for x in ['#*', '##']])):
                result = fi_get_translation(line, title, lang_header, udpos, translations, definitions, wordpairs)
                if result and len(result) == 3:
                    translations, definitions, wordpairs = result
    return wordpairs, definitions, example_sents


def extract_dict(path, lang):
    wordpairs = defaultdict(set)
    definitions = defaultdict(dict)
    example_sents = defaultdict(dict)
    with open('lang_hun.tsv') as f:
        langcodes = [code.strip()[:-2] for code in f.readlines() if code.strip()]
    for title, text in read_dump(path):
        if lang == 'fi':
            wordpairs, definitions, example_sents = extract_fi_dict(text, title, wordpairs, definitions, example_sents)
        elif lang == 'hu':
            result = extract_hu_dict(text, title, langcodes, wordpairs, definitions, example_sents)
            if result:
                wordpairs, definitions, example_sents = result
    return definitions, example_sents, wordpairs


def main():
    arguments = docopt(__doc__)
    lang = arguments['--lang']
    if lang not in ['hu', 'fi']:
        raise ValueError('lang must be `fi` or `hu`')
    path = arguments['--input']
    if not path:
        path = download_wiktionary(lang)
    output_path = arguments['--output']
    print('Output path is: ', output_path)
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    print('Extracting information from Wiktionary...')
    definitions, examples, wordpairs = extract_dict(path, lang)
    if arguments['all']:
        save_data(lang, definitions, examples, wordpairs, output_path)
    elif arguments['wordpairs']:
        save_pairs(wordpairs, lang, output_path)
    elif arguments['definitions']:
        save_sentences(definitions, lang, 'definitions', output_path)
    elif arguments['examples']:
        save_sentences(examples, lang, 'examples', output_path)
    print('Done.')

if __name__ == '__main__':
    main()



# Wiktionary Parser

### Description

This script parses the Finnish and Hungarian Wiktionaries, and extracts bilingual word pairs from them. It also collects definitions and example sentences.


### Usage

```
wiktionary_parser.py (wordpairs|definitions|examples|all) --lang=<wikicode> [--input=<file>] [--output=<path>]
```

The script supports 4 actions:
- `wordpairs`: extracting Finnish-Hungarian word pairs from the given Wiktionary edition.
- `definitions`: extracting definitions for words in the language of the Wiktionary edition (e.g. if the Wiktionary edition is Finnish, the collected definitions are also in Finnish). 
- `examples`: extracting example sentences for words in the language of the Wiktionary edition.
- `all`: getting the output of all three actions described above.

Options:
- `lang`: the language of the Wiktionary from which the data should be extracted. The script supports only `hu` and `fi`.
- `input`: the Wiktionary dump which is to be used. If not given, the script first looks for the `.xml` dump file in the `data/` directory, if not found, it downloads the latest Wiktionary dump for the given language.
- `output`: if given, the output is saved to this directory. Default output path is `output/`.

### Output 

Output is saved to the path given with the `--output` option. If not given,the default output path is the `output/` folder.

The bilingual dictionary is saved as `wordpairs_<wikicode>.tsv` and has three values separated by tabs:

```
FIN_WORD    <tab>   HUN_WORD    <tab>   UD_POS_TAG
```

The definitions and example sentences are saved similarly, as `definitions_<wikicode>.tsv` and `examples_<wikicode>.tsv` respectively.

```
UD_POS_TAG  <tab>  WORD <tab>   SENTENCE 
```


### License

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

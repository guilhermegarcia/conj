# Data license

The verb database (`src/conj/data/conj.sqlite.gz`) is a separate work from
the code. It is licensed under the
[Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/)
(CC BY-SA 4.0). If you redistribute the database or anything derived from it,
you must give attribution and use the same license.

## Sources

- **Wiktionary** (<https://en.wiktionary.org>): conjugation tables, auxiliaries
  and English glosses for French, Italian, Spanish, Portuguese and English verbs.
  © Wiktionary contributors, CC BY-SA 4.0 (dual-licensed under the GFDL).
- **Wiktextract / kaikki.org** (<https://kaikki.org>): the machine-readable
  extraction of Wiktionary used as input. Cite as:
  Tatu Ylonen (2022). *Wiktextract: Wiktionary as Machine-Readable Structured
  Data.* Proceedings of LREC 2022, pp. 1317–1325.
- **wordfreq** (<https://github.com/rspeer/wordfreq>), by Robyn Speer: word
  frequencies used at build time to rank verbs. Data CC BY-SA 4.0.

## What `conj-build` changes

- It keeps only verbs that have a conjugation table, or English principal parts.
- It drops forms tagged as archaic, dialectal, obsolete, poetic and similar.
  For Italian it keeps only the first, standard variant in each cell. For
  Spanish it drops voseo (*vos*) forms and keeps the *tú* ones.
- It converts Wiktionary's stress-marked Italian spelling (*córro*, *pàrla*)
  to standard orthography (*corro*, *parla*).
- It stores no compound or periphrastic tenses. `conj` builds those at run time
  from the auxiliary's paradigm and the participle.

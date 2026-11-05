#!/usr/bin/env python3
"""Check the shared source style for the native HELP database."""
import argparse
from pathlib import Path
import re

LABELS={'syntax':'Syntax','usage':'Syntax','purpose':'Explanation','explanation':'Explanation',
        'options':'Options','examples':'Examples'}
MARKER=re.compile(r'^\s*///([123])\s*(.*?)\s*$')


def format_text(source):
    sections=[]; current=None; body=[]
    for line in source.replace('\x1a','').splitlines():
        match=MARKER.match(line)
        if match:
            if current is not None:sections.append((current,body))
            current=(int(match[1]),match[2].upper());body=[]
        elif current is not None:body.append(line)
        elif line.strip():raise ValueError('text before the first HELP topic')
    if current is not None:sections.append((current,body))
    result=[]
    for (level,title),lines in sections:
        cleaned=[]
        for line in lines:
            line=line.expandtabs(8).strip()
            if not line:
                if cleaned and cleaned[-1]:cleaned.append('')
                continue
            match=re.fullmatch(r'([A-Za-z]+)\s*:\s*(.*)',line)
            if match and match[1].lower() in LABELS:
                cleaned.append(LABELS[match[1].lower()]+':')
                if match[2]:cleaned.extend(['',match[2]])
            else:cleaned.append(line)
        while cleaned and not cleaned[-1]:cleaned.pop()
        # Bare command-first topics use the same labels as existing Syntax topics.
        first=title.split()[0]
        if level==1 and cleaned and (cleaned[0]==first or cleaned[0].startswith(first+' ')):
            try:boundary=cleaned.index('')
            except ValueError:boundary=len(cleaned)
            cleaned=['Syntax:','']+cleaned[:boundary]+(
                ['','Explanation:','']+cleaned[boundary+1:] if boundary<len(cleaned) else [])
        if level>1 and title in ('OPTIONS','EXAMPLES') and cleaned:
            label=title.capitalize()+':'
            if cleaned[0]!=label:cleaned=[label,'']+cleaned
        # Separate labels and paragraphs uniformly, without rewriting literals.
        spaced=[]
        for line in cleaned:
            if line in ('Syntax:','Explanation:','Options:','Examples:'):
                if spaced and spaced[-1]:spaced.append('')
                spaced.extend([line,''])
            elif line or (spaced and spaced[-1]):spaced.append(line)
        while spaced and not spaced[-1]:spaced.pop()
        result.append('    '*(level-1)+'///'+str(level)+title)
        result.extend('    '+line if line else '' for line in spaced)
        result.append('')
    return '\n'.join(result).rstrip()+'\n'


def substance(source):
    """Ignore only presentation labels/spacing and topic-title case."""
    words=[]
    for line in source.replace('\x1a','').splitlines():
        marker=MARKER.match(line)
        if marker:
            words.append('///'+marker[1]+marker[2].upper());continue
        line=line.strip()
        match=re.fullmatch(r'([A-Za-z]+)\s*:\s*(.*)',line)
        if match and match[1].lower() in LABELS:line=match[2]
        words.extend(line.split())
    return words


def check(path):
    raw=path.read_bytes()
    source=raw.decode()
    if b'\r' in raw or b'\t' in raw or b'\x1a' in raw:
        raise ValueError(f'{path}: source must use LF, spaces and host EOF')
    if source!=format_text(source):
        raise ValueError(f'{path}: inconsistent HELP markers, headings, spacing or indentation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path)
    check(parser.parse_args().file)
    print('PASS: shared HELP source style')

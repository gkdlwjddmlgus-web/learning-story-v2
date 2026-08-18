from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT=Path.cwd(); path=ROOT/'.streamlit'/'secrets.toml'


def bool_text(value:str)->str:
    v=value.strip().lower()
    if v in {'true','1','yes','on'}: return 'true'
    if v in {'false','0','no','off'}: return 'false'
    raise ValueError('true 또는 false를 입력해주세요.')


def upsert(text:str,key:str,value:str)->str:
    pattern=rf'(?m)^\s*{re.escape(key)}\s*=.*$'
    line=f'{key} = {value}'
    if re.search(pattern,text): return re.sub(pattern,line,text,count=1)
    return text.rstrip()+('\n' if text.strip() else '')+line+'\n'


def main():
    if len(sys.argv)<2:
        print('사용법: python set_dev_ai_mock.py true [delay]  또는  python set_dev_ai_mock.py false')
        raise SystemExit(1)
    enabled=bool_text(sys.argv[1])
    delay=float(sys.argv[2]) if len(sys.argv)>=3 else 0.25
    path.parent.mkdir(parents=True,exist_ok=True)
    text=path.read_text(encoding='utf-8') if path.exists() else ''
    text=upsert(text,'DEV_AI_MOCK',enabled)
    text=upsert(text,'DEV_AI_MOCK_DELAY',str(max(0.0,min(delay,10.0))))
    path.write_text(text,encoding='utf-8')
    print(f'DEV_AI_MOCK = {enabled}')
    print(f'DEV_AI_MOCK_DELAY = {max(0.0,min(delay,10.0))}')
    print('기존 DATABASE_URL/GEMINI_API_KEY 값은 변경하지 않았습니다.')

if __name__=='__main__': main()

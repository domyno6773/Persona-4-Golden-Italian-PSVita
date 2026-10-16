"""Small, explicit allowlist for assets adapted by the existing Vita UI tools."""
import re
import struct

TEXTURES = {
    'font/game_helpx2.spr',
    'init_free.bin/init/camp.arc/c_main01x2.spr',
    'init_free.bin/init/camp.arc/calender.spr',
    'init_free.bin/init/camp.arc/event_skip.spr',
    'memcard/mcpanel.arc/p4g_savespr01.spr',
    'scheduler/date_change.bin/date_change01.spr',
    'title/animch.arc/peraniland_01spr.spr',
    'title/artch.arc/arttitle.spr',
    'title/channelmain.arc/tv_listings02spr.spr',
    'title/lesson.pack/edogawatitle.spr',
    'title/livech.arc/livetitle.spr',
    'title/musicch.arc/misic_ch.spr',
    'title/musicch.arc/heyheihoo_spr01.spr',
    'title/quiz.arc/quiz.spr',
    'title/quiz.pack/quiztitle.spr',
    'title/title.bin/p4g_menu01spr.spr',
    'title/title.bin/press_any_buttonmoji.tmx',
}


def approved_texture(path):
    path=path.lower()
    return (path in TEXTURES
            or bool(re.fullmatch(r'font/picture/picture[0-9a-f]+\.tmx',path))
            or bool(re.fullmatch(r'title/quiz.pack/telop_0[012]_(in|out)\.spr',path)))


def fixed_text_ranges(data,path):
    """Return text slots only; numeric record prefixes/tails stay native."""
    lower=path.lower()
    if len(data)<16:return []
    size,count,ext,reserved=struct.unpack_from('<IIII',data)
    if not count or size%count or 16+size>len(data) or ext or reserved:return []
    stride=size//count
    if '/cmptable.bin/' in lower and lower.endswith('.ctd') and stride==64:
        return [(16+i*stride,64) for i in range(count)]
    if '/fcltable.bin/' in lower and lower.endswith('.ftd'):
        name=lower.rsplit('/',1)[-1]
        if stride in (34,102) or name in {'fcllogformattext.ftd','fcllogconjunctiontext.ftd','fclsuggesttypename.ftd'}:
            return [(16+i*stride,stride) for i in range(count)]
        if name.startswith('fclhelptable_') and stride==48:
            return [(16+i*stride+8,34) for i in range(count)]
    return []


def preserve_adapted_text(vita,current,path):
    ranges=fixed_text_ranges(vita,path)
    if not ranges:return None
    if len(vita)!=len(current) or vita[:16]!=current[:16]:
        raise ValueError('Adapted text table has incompatible native header/layout: '+path)
    out=bytearray(vita)
    for offset,size in ranges:
        slot=current[offset:offset+size]
        if b'\0' not in slot:raise ValueError('Unterminated fixed text slot: '+path)
        out[offset:offset+size]=slot
    return bytes(out)


def check_adapted_text(vita,current,path):
    ranges=fixed_text_ranges(vita,path)
    if not ranges:return False
    assert len(vita)==len(current) and vita[:16]==current[:16],'Fixed text table layout changed'
    masked=bytearray(current)
    for offset,size in ranges:
        assert b'\0' in current[offset:offset+size],'Unterminated fixed text slot'
        masked[offset:offset+size]=vita[offset:offset+size]
    assert bytes(masked)==vita,'Numeric data or footer changed in text table'
    return True


def community_text_ranges(data,path):
    name=path.lower().rsplit('/',1)[-1]
    if not name.startswith('cmm') or not name.endswith('.dat') or len(data)<8:return []
    size,count=struct.unpack_from('<II',data)
    if not count or 8+size>len(data):return []
    if name in {'cmmpc_param_help.dat','cmmpc_param_name.dat'}:
        return [(8+i*14,14) for i in range(size//14)]
    if name=='cmmbooktable.dat':
        return [(8+i*84+12,72) for i in range(count)]
    if name=='cmmcommunitymaxwork.dat':
        return [(8+i*66,64) for i in range(count)]
    if name in {'cmmname.dat','cmmplace.dat','cmmarcanasphelp.dat','cmmclubname.dat',
                'cmmmailorder_text.dat','cmmmailorder_name.dat','cmmmembername.dat','cmmfixstring.dat'}:
        return [(8,size)]
    return []

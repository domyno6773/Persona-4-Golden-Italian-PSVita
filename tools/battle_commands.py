"""Localize the Golden battle menu by changing native 4bpp text pixels only."""
import struct
from PIL import Image

COMMAND_PATH='battle/panel/btlpanel.bin/p4p_com01x2.spr'
EDITED_SPRITES=(4,34,53)+tuple(range(69,77))+tuple(range(81,89))+(94,)+tuple(range(118,124))+(128,129,134,135,147)


def sprite_info(data,index):
    nt,ns,to,so=struct.unpack_from('<HHII',data,0x14)
    if not 0<=index<ns:raise ValueError('SPR sprite index outside directory')
    _,off=struct.unpack_from('<II',data,so+index*8)
    texture=struct.unpack_from('<I',data,off+0x14)[0]
    box=struct.unpack_from('<4I',data,off+0x54)
    if texture>=nt:raise ValueError('SPR texture index outside directory')
    return texture,box


def texture_info(data,index):
    nt,ns,to,so=struct.unpack_from('<HHII',data,0x14)
    if index>=nt:raise ValueError('SPR texture index outside directory')
    _,off=struct.unpack_from('<II',data,to+index*8)
    if data[off+8:off+12]!=b'TMX0':raise ValueError('Missing TMX wrapper')
    w,h=struct.unpack_from('<HH',data,off+0x12)
    return off,w,h,data[off+0x16]


def alpha_atlas(data,index=3):
    off,w,h,fmt=texture_info(data,index)
    if fmt!=0x14:raise ValueError('Expected Vita 4bpp command texture')
    pal=data[off+0x40:off+0x80]
    alphas=[min(255,pal[i*4+3]*2) for i in range(16)]
    pix=data[off+0x80:off+0x80+w*h//2]
    return Image.frombytes('L',(w,h),bytes(a for b in pix for a in (alphas[b&15],alphas[b>>4])))


def allowed_pixel_masks(native):
    if struct.unpack_from('<HH',native,0x14)!=(13,193):
        raise ValueError('Unknown Vita Golden battle SPR layout')
    off,w,h,fmt=texture_info(native,3)
    if (w,h,fmt)!=(512,512,0x14):raise ValueError('Unknown native command atlas')
    masks={}
    for index in EDITED_SPRITES:
        tid,(x0,y0,x1,y1)=sprite_info(native,index)
        if tid!=3 or not (0<=x0<x1<=w and 0<=y0<y1<=h):
            raise ValueError('Unknown command text slot')
        for y in range(y0,y1):
            for x in range(x0,x1):
                pos=off+0x80+(y*w+x)//2
                masks[pos]=masks.get(pos,0)|(0xf0 if x&1 else 0x0f)
    return masks


def check_command_pixels(native,patched):
    if len(native)!=len(patched):raise ValueError('Command SPR size changed')
    masks=allowed_pixel_masks(native)
    for pos,(a,b) in enumerate(zip(native,patched)):
        if (a^b)&(~masks.get(pos,0)&255):
            raise ValueError(f'Command metadata, palette, icon or unrelated pixels changed at {pos:#x}')
    return True


def preserve_command_texture(native,current,path):
    if path.lower()!=COMMAND_PATH:return None
    check_command_pixels(native,current)
    return current


def localize_commands(native,pc):
    allowed_pixel_masks(native)
    if struct.unpack_from('<HH',pc,0x14)!=(13,193):
        raise ValueError('Unknown PC Italian command SPR layout')
    po,pw,ph,pfmt=texture_info(pc,3)
    if (pw,ph,pfmt)!=(1024,1024,0):raise ValueError('Unknown PC command atlas')
    source=Image.frombytes('RGBA',(pw,ph),pc[po+0x40:po+0x40+pw*ph*4]).getchannel('A')
    # PC TMX stores fully opaque pixels as 128, while Pillow uses 255.
    if 0<source.getextrema()[1]<=128:source=source.point(lambda a:min(255,a*2))
    off,w,h,fmt=texture_info(native,3);pal=native[off+0x40:off+0x80]
    white=[i for i in range(16) if pal[i*4:i*4+3]==b'\xff\xff\xff']
    if not white:raise ValueError('Missing native white glyph palette')
    table=[min(white,key=lambda i:abs(min(255,pal[i*4+3]*2)-a)) for a in range(256)]
    result=bytearray(native);original=alpha_atlas(native);previews=[]
    for index in EDITED_SPRITES:
        tid,box=sprite_info(native,index)
        if sprite_info(pc,index)!=(tid,box):raise ValueError('PC sprite coordinates differ from Vita')
        x0,y0,x1,y1=box
        glyphs=source.crop(tuple(x*2 for x in box)).resize((x1-x0,y1-y0),Image.Resampling.LANCZOS)
        for y in range(y0,y1):
            for x in range(x0,x1):
                idx=table[glyphs.getpixel((x-x0,y-y0))]
                pos=off+0x80+(y*w+x)//2
                result[pos]=(result[pos]&0x0f)|(idx<<4) if x&1 else (result[pos]&0xf0)|idx
        previews.append((index,original.crop(box),glyphs))
    check_command_pixels(native,result)
    return bytes(result),previews

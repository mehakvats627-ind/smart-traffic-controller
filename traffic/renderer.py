"""Headless Pygame top-down intersection renderer."""
import os
from io import BytesIO
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

def render(snapshot, width=1000, height=500):
    pygame.init()
    surface=pygame.Surface((width,height))
    surface.fill((19,31,35))
    road=(47,53,57); lane=(222,211,181); green=(68,208,125); amber=(244,157,70); red=(239,74,77)
    cx,cy=width//2,height//2; half=100
    pygame.draw.rect(surface,road,(cx-half,0,half*2,height)); pygame.draw.rect(surface,road,(0,cy-half,width,half*2))
    for x in (cx-50,cx+45):
        for y in range(0,height,38): pygame.draw.line(surface,lane,(x,y),(x,y+18),2)
    for y in (cy-50,cy+45):
        for x in range(0,width,38): pygame.draw.line(surface,lane,(x,y),(x+18,y),2)
    for offset in range(-65,70,15):
        pygame.draw.line(surface,(238,236,223),(cx-half-12,cy+offset),(cx-half+10,cy+offset),5)
        pygame.draw.line(surface,(238,236,223),(cx+half-10,cy+offset),(cx+half+12,cy+offset),5)
        pygame.draw.line(surface,(238,236,223),(cx+offset,cy-half-12),(cx+offset,cy-half+10),5)
        pygame.draw.line(surface,(238,236,223),(cx+offset,cy+half-10),(cx+offset,cy+half+12),5)
    font=pygame.font.SysFont("segoeui",16,bold=True)
    for label,pos in (("N",(cx,24)),("E",(width-24,cy)),("S",(cx,height-26)),("W",(24,cy))):
        surface.blit(font.render(label,True,(236,226,204)),pos)
    colors={"Car":(80,166,239),"Bus":(244,183,61),"Truck":(225,79,86),"Ambulance":(222,104,221)}
    for i,v in enumerate(snapshot.get("vehicles",[])):
        a=v["approach"]; step=i%5
        p=min(82,14+step*14+max(0,5-v["remaining"])*5)
        if a=="North": rect=(cx-65+(i%3)*28,cy-half-p,18,28)
        elif a=="South": rect=(cx+40+(i%3)*26,cy+half+p-28,18,28)
        elif a=="West": rect=(cx-half-p,cy-65+(i%3)*25,28,18)
        else: rect=(cx+half+p-28,cy+38+(i%3)*25,28,18)
        pygame.draw.rect(surface,colors[v["kind"]],rect,border_radius=5)
    phases={"North":(cx-116,cy-116),"East":(cx+105,cy-116),"South":(cx+105,cy+100),"West":(cx-116,cy+100)}
    px,py=phases.get(snapshot.get("phase"),(cx,cy)); color=green if snapshot.get("transition")=="green" else amber if snapshot.get("transition")=="yellow" else red
    pygame.draw.circle(surface,color,(px,py),9)
    output=BytesIO()
    pygame.image.save(surface,output,"intersection.png")
    pygame.quit()
    return output.getvalue()

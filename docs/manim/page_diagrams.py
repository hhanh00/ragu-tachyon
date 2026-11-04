"""Page-by-page static diagrams; pnpm docs:manim --page <chapter-slug>."""
from manim import *
import numpy as np
from concept_diagrams import label, math, arrow, box, heading, INK, MUTED, BLUE, TEAL, ORANGE, PURPLE, PALE
config.background_color = WHITE
config.frame_width = 16
config.frame_height = 9


def axes_at(cx,cy,w=5.8,h=3.9,xr=(-3,3,1),yr=(-2,2,1)):
    return Axes(x_range=list(xr),y_range=list(yr),x_length=w,y_length=h,tips=False,
                axis_config={'color':'#9aaabb','include_ticks':False}).move_to([cx,cy,0])


def path_curve(ax, fn, interval, color=BLUE):
    return ax.plot(fn,x_range=interval,color=color,stroke_width=4)

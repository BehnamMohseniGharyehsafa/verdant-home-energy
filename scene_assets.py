"""Procedural architecture assets; no downloaded models or browser scripts."""
import math
import numpy as np


def modern_ev(a):
    paint, dark, glass = "#86afc4", "#1c2e3a", "#294856"
    # Swept fastback body: a continuous, tapered set of transverse sections.
    rings = []
    for y, half, lower, belt, crown in [(.02,.72,.29,.65,.74),(.38,.94,.26,.79,.87),
            (1.0,.97,.27,.84,.93),(2.6,.97,.27,.85,.93),(3.36,.89,.29,.83,.89),(3.66,.72,.33,.68,.76)]:
        rings.append([(14.08-half,y,lower),(14.08-half,y,belt),
                      (14.08-half*.8,y,crown),(14.08+half*.8,y,crown),
                      (14.08+half,y,belt),(14.08+half,y,lower)])
    body=a.m(paint)
    body.face(list(reversed(rings[0])))
    body.face(rings[-1])
    for low,high in zip(rings,rings[1:]):
        for i in range(6):
            j=(i+1)%6
            body.face([low[i],low[j],high[j],high[i]])
    # Panoramic roof and raked front/rear glass, with structural pillars.
    canopy=[(13.32,.91,.89),(14.84,.91,.89),(14.74,1.6,1.48),(13.42,1.6,1.48),
            (13.42,2.37,1.49),(14.74,2.37,1.49),(14.88,3.12,.94),(13.28,3.12,.94)]
    for indices in [(0,1,2,3),(3,2,5,4),(4,5,6,7),(0,3,4,7),(1,6,5,2)]:
        a.m(glass).face([canopy[i] for i in indices])
    for x1,x2 in [(13.30,13.42),(14.86,14.74)]:
        a.m(paint).tube([(x1,.97,.93),(x2,1.63,1.5),(x2,2.38,1.51),(x1,3.1,.96)],.035)
        a.m(dark).tube([(x1+.025,2.04,.91),(x2,2.04,1.5)],.042)
    for x in (13.105,15.035):
        a.box(x,1.45,.83,.025,.27,.035,dark,.012)
        a.box(x,2.5,.84,.025,.24,.035,dark,.012)
        a.box(x,1.15,1,.16,.25,.11,paint,.04)
    # Turbine alloys, rubber sidewalls, central caps and visible brake discs.
    for x in (13.12,15.04):
        for y in (.78,2.92):
            a.m("#15232b").cylinder((x-.12,y,.39),(x+.12,y,.39),.35,28)
            outer=x+(-.135 if x<14 else .135)
            a.m("#92a6b1").cylinder((outer,y,.39),(outer+.008,y,.39),.265,28)
            a.m("#253642").cylinder((outer-.012,y,.39),(outer+.012,y,.39),.225,24)
            for angle in np.linspace(0,2*math.pi,5,endpoint=False):
                a.m("#d5e0e0").face([(outer,y+.05*math.cos(angle),.39+.05*math.sin(angle)),
                    (outer,y+.25*math.cos(angle+.25),.39+.25*math.sin(angle+.25)),
                    (outer,y+.23*math.cos(angle+.60),.39+.23*math.sin(angle+.60))])
            a.m("#c5d9df").cylinder((outer-.015,y,.39),(outer+.015,y,.39),.07,16)
    # Full-width LED signature, sculpted bumper, light bar and charging port.
    a.box(13.36,.004,.68,1.44,.025,.035,"#d9f8fa",.015)
    for x in (13.34,14.62):
        a.box(x,.015,.59,.2,.035,.065,"#e4faff",.025)
    a.box(13.56,-.01,.34,1.04,.055,.16,dark,.04)
    a.box(13.42,3.65,.73,1.32,.025,.035,"#ed6868",.015)
    a.box(13.59,3.67,.43,.98,.025,.12,dark,.02)
    a.box(14.99,2.64,.9,.025,.2,.15,dark,.025)


def tree(a,x,y,height,seed):
    rng=np.random.default_rng(seed)
    bark=a.m("#70634f")
    trunk=[(x,y,-.06),(x+.07,y+.02,height*.45),(x-.08,y+.03,height*.78)]
    bark.cylinder(trunk[0],trunk[1],.115,12)
    bark.cylinder(trunk[1],trunk[2],.075,10)
    palette=["#385e45","#426c4d","#527d54","#668c5c","#739765","#466e4b"]
    for i in range(17):
        angle=i*2.39996
        radius=rng.uniform(.35,1.05)
        center=(x+radius*math.cos(angle),y+radius*math.sin(angle),height-.25+rng.uniform(-.55,.6))
        start=(x+.03,y,height*.47+rng.uniform(0,.55))
        fork=(x+radius*.5*math.cos(angle),y+radius*.5*math.sin(angle),center[2]-.35)
        bark.cylinder(start,fork,.025+(.012 if i<5 else 0),8)
        bark.cylinder(fork,center,.018,7)
        a.m(palette[i%len(palette)]).sphere(center,rng.uniform(.43,.65),
            scales=(1.05,.85,rng.uniform(.8,1.2)),resolution=5)
        # Small irregular outer sprays break up the rounded canopy silhouette.
        for j in range(3):
            delta=rng.normal(0,.38,3)
            a.m(palette[(i+j+2)%len(palette)]).sphere(np.array(center)+delta,.18,
                scales=(1.2,.8,.65),resolution=3)
    for angle in np.linspace(0,2*math.pi,5,endpoint=False):
        bark.cylinder((x,y,.08),(x+.35*math.cos(angle),y+.35*math.sin(angle),-.03),.04,8)


STREET_LIGHTS=((.1,-3.05),(16.0,-3.05))


def streets(a):
    a.box(-1.8,-6.4,-.35,19.5,4.2,.22,"#515f57")
    a.box(-1.8,-6.35,-.115,19.5,2.8,.035,"#3c4850")
    a.box(-1.8,-3.55,-.11,19.5,.65,.07,"#a9b1a6")
    for x in np.arange(-1.4,17,2.0):
        a.box(float(x),-5.02,-.074,.95,.07,.008,"#cbd0bd")
    for x,y in STREET_LIGHTS:
        a.m("#4c626a").cylinder((x,y,-.04),(x,y,3.7),.055,12)
        a.m("#637c80").tube([(x,y,3.65),(x,y-.3,3.92),(x,y-.95,3.92)],.055)
        a.box(x-.17,y-1.15,3.82,.34,.53,.10,"#72888b",.06)
        a.box(x-.12,y-1.10,3.807,.24,.43,.018,"#aabfc4",.03)


def grid_infrastructure(a):
    # Illustrative network: transmission lattice -> substation -> LV meter -> house.
    a.box(18,-3.8,-.35,13,14.4,.2,"#40594b",.25)
    x,y=26.5,6.2
    steel=a.m("#8098a2")
    levels=[(0,1.45),(2.2,1.05),(4.4,.7),(6.6,.45),(9.5,.22)]
    for (za,wa),(zb,wb) in zip(levels,levels[1:]):
        for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            steel.cylinder((x+sx*wa,y+sy*wa,za),(x+sx*wb,y+sy*wb,zb),.042,8)
        for axis in (0,1):
            for sign in (-1,1):
                corners=lambda w,z:[(x-w,y+sign*w,z),(x+w,y+sign*w,z)] if axis==0 else [(x+sign*w,y-w,z),(x+sign*w,y+w,z)]
                low,high=corners(wa,za),corners(wb,zb)
                steel.cylinder(low[0],high[1],.025,7)
                steel.cylinder(low[1],high[0],.025,7)
    for z,width in [(6.2,2.2),(8,2.7),(9.5,1.9)]:
        steel.cylinder((x-width,y,z),(x+width,y,z),.05,9)
        for sign in (-1,1):
            end=x+sign*width
            steel.cylinder((x,y,z-.65),(end,y,z),.027,8)
            for zz in np.arange(z-.4,z,.08):
                a.m("#d1c9ac").cylinder((end,y,zz),(end,y,zz+.025),.09,10)
            a.m("#4e6a7d").tube([(end+4*t,y+2*t,z-.42-.5*math.sin(math.pi*t)) for t in np.linspace(0,1,15)],.025)
    # Transformer yard includes HV bushings, tank, radiators and fenced perimeter.
    a.box(22.8,-.9,.02,2.1,2.1,.2,"#aab3a7",.08)
    a.box(23.0,-.7,.24,1.65,1.5,1.25,"#7b9694",.08)
    for xx in np.arange(23.02,24.65,.16):
        a.box(float(xx),-.82,.32,.07,.13,.95,"#526f73",.02)
    for xx in (23.25,23.8,24.35):
        for z in np.arange(1.5,2.0,.10):
            a.m("#c7c7ab").cylinder((xx,.05,z),(xx,.05,z+.045),.09,10)
    a.m("#547d9d").tube([(25.8,5.8,5.7),(24.5,3.4,3.8),(23.8,.05,2.0)],.045)
    for xx in np.arange(22.4,25.4,.42):
        for yy in (-1.35,1.5):
            a.m("#849c91").cylinder((float(xx),yy,0),(float(xx),yy,.9),.018,6)
    for z in (.25,.65):
        a.m("#91a399").line([(22.4,-1.35,z),(25.3,-1.35,z),(25.3,1.5,z),(22.4,1.5,z),(22.4,-1.35,z)])
    a.box(17.1,.35,.05,.6,.45,1.15,"#aebeb8",.06)
    a.box(17.17,.30,.78,.44,.025,.25,"#66b7b4",.03)
    a.m("#5d9cc9").tube([(23.8,-.6,.2),(23.8,-2.1,.12),(17.4,-2.1,.12),
        (17.4,.25,.5),(16.6,.25,.15),(12.4,.25,.15)],.055)


"""Detailed Python-authored VTK/WebGL home with pickable controls.

Materials are batched, surface normals are supplied explicitly, and live
updates patch actors without rebuilding the static house or resetting its camera.
"""
from collections import OrderedDict
from functools import lru_cache
import math
import numpy as np
import dash_vtk as vtk
from dash import Patch
from energy import ROOMS, DEVICES
from scene_assets import modern_ev, tree, streets, grid_infrastructure, STREET_LIGHTS

FLOORS = {"living": (0, 0, 7, 4.2), "kitchen": (7, 0, 12, 4.2),
          "bedroom": (0, 4.2, 4.5, 9), "bathroom": (4.5, 4.2, 7, 9),
          "office": (7, 4.2, 12, 9), "garage": (12, 4, 16, 9)}
DEVICE_POSITIONS = {"washer": (7.8, 1.0, 1.65), "dishwasher": (9.25, 1.0, 1.65),
                    "oven": (10.65, 1.0, 1.65), "water": (6.3, 7.8, 1.8),
                    "office": (9.25, 7.3, 1.8), "ev": (15.4, 3.1, 1.8)}
GREEN, CYAN, AMBER = "#b8ee88", "#5ae1ed", "#ffda85"
CAMERAS = {"orbit": [21, -27, 24], "front": [1, -34, 12], "top": [0, -.01, 35], "inside": [14, -20, 22]}
# Stable actor positions prevent VTK lifecycle races when envelope modes change.
STATIC_OPACITIES = (1, .48, .46, .7, .18, .1, .14, .2, .25)


def rgb(color):
    return [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def xyz(point):
    return [round(float(point[0]) - 7.5, 5), round(float(point[1]) - 4, 5), round(float(point[2]) - 1.7, 5)]


class Mesh:
    def __init__(self):
        self.points, self.polys, self.normals, self.lines = [], [], [], []
        self.colors=[]

    def face(self, vertices, normals=None):
        start = len(self.points) // 3
        a, b, c = np.asarray(vertices[:3], dtype=float)
        normal = np.cross(b - a, c - a)
        length = np.linalg.norm(normal)
        normal = normal / length if length > 1e-12 else np.array([0., 0., 1.])
        for i, vertex in enumerate(vertices):
            self.points.extend(float(v) for v in vertex)
            self.normals.extend(round(float(v),6) for v in (normals[i] if normals is not None else normal))
        self.polys.extend([len(vertices), *range(start, start + len(vertices))])

    def line(self, points):
        start = len(self.points) // 3
        for point in points:
            self.points.extend(float(v) for v in point)
            self.normals.extend([0, 0, 1])
        self.lines.extend([len(points), *range(start, start + len(points))])

    def box(self, x, y, z, w, d, h):
        p = [(x, y, z), (x+w, y, z), (x+w, y+d, z), (x, y+d, z),
             (x, y, z+h), (x+w, y, z+h), (x+w, y+d, z+h), (x, y+d, z+h)]
        for face in [(0,3,2,1), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]:
            self.face([p[i] for i in face])

    def rounded(self, x, y, z, w, d, h, radius=.1):
        radius = min(radius, w / 2, d / 2)
        loops = []
        bevel = min(.04, h / 5, radius / 2)
        for level, inset in [(z, bevel), (z+bevel, 0), (z+h-bevel, 0), (z+h, bevel)]:
            loop, r = [], max(.005, radius-inset)
            for cx, cy, angle in [(x+w-radius, y+d-radius, 0), (x+radius, y+d-radius, 90),
                                   (x+radius, y+radius, 180), (x+w-radius, y+radius, 270)]:
                for j in range(7):
                    theta = math.radians(angle+j*15)
                    loop.append((cx+r*math.cos(theta), cy+r*math.sin(theta), level))
            loops.append(loop)
        self.face(list(reversed(loops[0])))
        self.face(loops[-1])
        for low, high in zip(loops, loops[1:]):
            for i in range(len(low)):
                n = (i+1) % len(low)
                self.face([low[i], low[n], high[n], high[i]])

    def sphere(self, center, radius, scales=(1,1,1), resolution=12):
        center = np.array(center)
        for i in range(resolution):
            a1, a2 = math.pi*i/resolution, math.pi*(i+1)/resolution
            for j in range(resolution*2):
                b1, b2 = math.pi*j/resolution, math.pi*(j+1)/resolution
                normals = [np.array([math.sin(a)*math.cos(b), math.sin(a)*math.sin(b), math.cos(a)])
                           for a,b in [(a1,b1),(a2,b1),(a2,b2),(a1,b2)]]
                self.face([center+radius*n*np.array(scales) for n in normals], normals)

    def cylinder(self, a, b, radius, resolution=20):
        a, b = np.array(a,dtype=float), np.array(b,dtype=float)
        axis = b-a
        axis /= np.linalg.norm(axis)
        u = np.cross(axis, [0,0,1] if abs(axis[2]) < .9 else [0,1,0])
        u /= np.linalg.norm(u)
        v = np.cross(axis,u)
        normals = [math.cos(t)*u+math.sin(t)*v for t in np.linspace(0,2*math.pi,resolution,endpoint=False)]
        low, high = [a+radius*n for n in normals], [b+radius*n for n in normals]
        self.face(list(reversed(low)))
        self.face(high)
        for i in range(resolution):
            j = (i+1) % resolution
            self.face([low[i],low[j],high[j],high[i]], [normals[i],normals[j],normals[j],normals[i]])

    def tube(self, points, radius=.025):
        for a,b in zip(points,points[1:]):
            if np.linalg.norm(np.array(b)-np.array(a)) > 1e-6:
                self.cylinder(a,b,radius,10)

    def extend(self,mesh,color):
        offset=len(self.points)//3
        self.points.extend(mesh.points); self.normals.extend(mesh.normals)
        self.colors.extend([int(c*255) for c in rgb(color)]*(len(mesh.points)//3))
        for source,target in [(mesh.polys,self.polys),(mesh.lines,self.lines)]:
            cursor=0
            while cursor<len(source):
                count=source[cursor]
                target.extend([count,*[i+offset for i in source[cursor+1:cursor+1+count]]])
                cursor+=count+1


def representation(mesh, rep_id, color, opacity=1, pickable=False, local=False, ambient=.32):
    points = mesh.points if local else [v for p in np.array(mesh.points).reshape(-1,3) for v in xyz(p)]
    arrays=[vtk.DataArray(name="Normals",values=mesh.normals,numberOfComponents=3,registration="setNormals")]
    if mesh.colors:
        arrays.append(vtk.DataArray(name="RGB",type="Uint8Array",values=mesh.colors,numberOfComponents=3,registration="setScalars"))
    return vtk.GeometryRepresentation(id=rep_id, actor={"pickable":pickable},
        mapper={"scalarVisibility":bool(mesh.colors),"colorMode":2}, property={"color":rgb(color), "opacity":opacity,
        "ambient":ambient, "diffuse":.72, "specular":.22, "specularPower":35,
        "interpolation":2, "lineWidth":2.2}, children=[vtk.PolyData(points=points,
        polys=mesh.polys, lines=mesh.lines, children=[vtk.PointData(arrays)])])


class Architecture:
    def __init__(self):
        self.materials = OrderedDict()

    def m(self, color, opacity=1):
        return self.materials.setdefault((color,opacity),Mesh())

    def box(self,x,y,z,w,d,h,color,rounded=0):
        mesh = self.m(color)
        if rounded:
            mesh.rounded(x,y,z,w,d,h,rounded)
        else:
            mesh.box(x,y,z,w,d,h)


def roof_height(y):
    return 4.4-abs(y-4.5)*1.5/4.8


@lru_cache(maxsize=6)
def architecture(mode="exterior",district=False):
    a = Architecture()
    inside = mode == "interior"
    wall = a.m("#ede8dc", .18 if mode == "xray" else 1)
    dark, metal, wood, glass = "#29343c", "#697b82", "#ac8561", "#9ac6cf"
    a.box(-1.8,-2.3,-.35,19.5,12.9,.22,"#557863",.5)
    a.box(-.25,-.25,-.15,12.5,9.5,.15,"#c7c5b9",.06)
    a.box(12,-.6,-.12,4.5,9.7,.12,"#a8b2ac",.08)
    for x in np.arange(12.1,16.4,.55):
        for y in np.arange(-.4,3.9,.6):
            a.box(float(x),float(y),.005,.53,.58,.018,"#b9c1b9")
    for x in np.arange(.2,6.6,.65):
        a.box(float(x),-1.4,-.02,.62,1.1,.035,"#b9afa0")
    for y in (-2,-1.5,-1):
        a.box(6.05,y,-.04,1.1,.36,.055,"#d0d1c3",.03)
    for room,(x1,y1,x2,y2) in FLOORS.items():
        if room in ("bathroom","garage"):
            a.box(x1,y1,.01,x2-x1,y2-y1,.04,"#a6b7b8" if room == "bathroom" else "#a7ada7")
        else:
            for i,y in enumerate(np.arange(y1,y2,.21)):
                a.box(x1,float(y),.015,x2-x1,min(.195,y2-y),.03,
                      ["#c8ad87","#c2a57c","#d1b794","#bfa17b"][i%4])
    # The full envelope has wall segments around genuine window/door openings.
    if inside:
        wall.box(0,-.14,.05,12,.18,.38)
        wall.box(11.9,0,.05,.18,4.2,.4)
    else:
        for x,w in [(0,.55),(5.35,.5),(6.95,.75),(11.4,.6)]:
            wall.box(x,-.16,.05,w,.23,2.85)
        wall.box(0,-.16,2.45,12,.23,.45)
        wall.box(7.7,-.16,.05,3.7,.23,.65)
        for x,w,bottom,height in [(.55,4.8,.08,2.32),(7.7,3.7,.74,1.64)]:
            a.box(x,-.185,bottom,w,.12,.07,dark)
            a.box(x,-.185,bottom+height-.07,w,.12,.07,dark)
            for xx in (x,x+w/2,x+w-.055):
                a.box(xx,-.185,bottom,.055,.12,height,dark)
            a.m(glass,.48).box(x+.06,-.11,bottom+.07,w-.12,.025,height-.14)
        a.box(5.9,-.18,.08,1,.12,2.35,"#866d55",.025)
        for z in np.arange(.18,2.3,.17):
            a.box(5.92,-.191,float(z),.96,.015,.012,"#6c5a49")
        a.box(6.7,-.23,.95,.045,.055,.33,"#d5dfd9",.012)
        wall.box(11.95,0,.05,.22,9.05,2.85)
    wall.box(-.16,0,.05,.22,9.05,1.65 if inside else 2.85)
    wall.box(0,8.9,.05,12,.22,.76)
    wall.box(0,8.9,2.3,12,.22,.6)
    for x,w in [(0,.6),(3.7,1.05),(6.2,1.1),(11.3,.7)]:
        wall.box(x,8.9,.76,w,.22,1.54)
    for x,w in [(.6,3.1),(4.75,1.45),(7.3,4)]:
        a.m(glass,.46).box(x,8.97,.82,w,.035,1.42)
        for xx in (x,x+w/2,x+w-.05):
            a.box(xx,8.88,.76,.05,.2,1.54,dark)
        for zz in (.76,2.25):
            a.box(x,8.88,zz,w,.2,.05,dark)
    if not inside:
        for x in np.arange(11.45,12.01,.085):
            a.box(float(x),-.235,.05,.065,.05,2.8,wood)
        for y in (-.28,9.16):
            a.box(-.2,y,2.78,12.4,.13,.15,dark)
    for x,y,w,d in [(0,4.13,2.8,.14),(3.8,4.13,4.3,.14),(9.2,4.13,2.8,.14),
                    (6.93,0,.14,2.6),(6.93,3.5,.14,.7),(4.43,4.2,.14,2.8),
                    (4.43,8,.14,1),(6.93,4.2,.14,2.9),(6.93,8.1,.14,.9)]:
        a.box(x,y,.05,w,d,1.05 if inside else 2.65,"#e8e0d2")
        a.box(x,y,.06,w,d,.09,"#f7f1e4")
    # Furnishings have rounded upholstery and bevelled edges.
    a.box(1,.8,.055,4.8,2.65,.025,"#e0d7c3",.15)
    a.box(1.4,2.85,.12,3.7,.97,.47,"#68847a",.2)
    a.box(1.4,3.55,.5,3.7,.24,.55,"#5b786d",.12)
    for x in (1.4,4.87):
        a.box(x,2.85,.4,.24,.97,.45,"#5b786d",.1)
    for x in (1.7,2.75,3.8):
        a.box(x,3,.58,.95,.57,.12,"#96aa94",.08)
    for x,color in [(1.85,"#dfd7bc"),(4.18,"#c2b195")]:
        a.box(x,3.48,.72,.5,.13,.42,color,.07)
    a.box(5.4,1.9,.12,.9,.95,.48,"#ae9679",.18)
    a.box(5.4,2.65,.5,.9,.2,.55,"#ae9679",.1)
    a.box(2.65,1.32,.37,1.8,.9,.08,"#947b5c",.2)
    for x in (2.8,4.1):
        a.box(x,1.55,.08,.08,.4,.3,dark)
    a.box(3.12,1.53,.46,.46,.3,.035,"#e6e8dc",.015)
    a.box(.7,.15,.08,3.6,.45,.45,wood,.05)
    a.box(1.25,.36,.57,2.4,.09,1,dark,.035)
    a.box(1.31,.30,.63,2.28,.015,.85,"#26434d",.015)
    # Kitchen: actual washer door, dishwasher handle, oven glass and hob.
    for x in np.arange(7.25,11.6,.72):
        a.box(float(x),.16,.06,.69,.66,.8,"#69857c",.025)
        a.box(float(x+.14),.11,.68,.37,.025,.025,metal,.01)
    a.box(7.2,.1,.88,4.5,.8,.085,"#eee9dc",.025)
    a.box(11,.9,.06,.7,2.7,.8,"#69857c",.035)
    a.box(10.96,.85,.88,.8,2.85,.085,"#eee9dc",.025)
    a.box(7.35,.075,.12,.85,.07,.72,"#e6e9e2",.035)
    a.m(dark).cylinder((7.78,.04,.45),(7.78,.005,.45),.25,32)
    a.m("#63838b").cylinder((7.78,-.005,.45),(7.78,-.025,.45),.19,32)
    a.box(8.8,.075,.12,.84,.07,.72,"#c6cec6",.025)
    a.box(8.94,.005,.73,.55,.045,.035,dark,.01)
    a.box(10.2,.07,.12,.82,.07,.72,dark,.035)
    a.box(10.28,.025,.21,.66,.025,.43,"#456370",.025)
    a.box(10.28,-.005,.70,.66,.035,.035,metal,.012)
    a.box(10.18,.24,.97,.82,.48,.015,dark,.02)
    for x in (10.36,10.8):
        for y in (.36,.61):
            a.m(metal).cylinder((x,y,.98),(x,y,.99),.09,16)
    a.box(7.25,2.75,.05,.9,.85,1.95,"#cbd3ce",.09)
    a.box(8.7,2,.06,1.7,.9,.83,wood,.04)
    a.box(8.57,1.88,.91,1.96,1.13,.08,"#ece5d5",.045)
    for x in (8.85,9.75):
        a.box(x,3.13,.13,.43,.43,.5,"#536f62",.12)
    # Bedroom, bathroom and office.
    a.box(.6,5.45,.055,3.2,3,.02,"#c0c4c1",.12)
    a.box(1.15,5.9,.1,2.2,2.75,.4,"#ad9475",.08)
    a.box(1.12,8.5,.12,2.27,.16,1.2,"#ae9c85",.09)
    a.box(1.2,5.95,.51,2.1,2.5,.2,"#f1eadb",.1)
    a.box(1.21,5.94,.72,2.08,1.55,.065,"#78939c",.08)
    for x in (1.4,2.5):
        a.box(x,7.85,.73,.68,.46,.14,"#f4efde",.13)
    for x in (.3,3.6):
        a.box(x,7.85,.1,.6,.65,.55,wood,.05)
    a.box(4.7,6.5,.07,.95,2,.56,"#e8ece7",.25)
    a.box(4.8,6.65,.63,.74,1.7,.025,"#8dbac3",.25)
    a.box(5.9,8,.08,.87,.66,.76,"#81998e",.04)
    a.box(5.94,7.98,.87,.81,.69,.065,"#f0efe5",.04)
    a.m("#bfcfd1",.7).box(6,8.85,1.05,.7,.04,1)
    a.box(6,5.1,.1,.6,.9,.4,"#e3e9e3",.22)
    a.m("#d8e0d7").cylinder((6.5,7,.13),(6.5,7,1.5),.28,28)
    a.box(8,7.6,.77,2.9,.9,.09,wood,.035)
    for x in (8.1,10.65):
        a.box(x,7.67,.05,.1,.7,.72,dark)
    a.box(8.85,8,.95,1.15,.07,.68,dark,.045)
    a.box(8.9,7.96,1,1.05,.012,.56,"#6ba6b3",.02)
    a.box(9,7.65,.88,.7,.23,.02,dark,.02)
    a.box(8.95,6.5,.35,.8,.8,.15,"#54786e",.15)
    a.box(8.95,6.47,.5,.8,.12,.65,"#54786e",.08)
    a.m(metal).cylinder((9.35,6.9,.08),(9.35,6.9,.37),.06)
    a.box(11.35,5,.05,.4,3.2,1.6,wood,.03)
    for i,y in enumerate(np.arange(5.1,8,.18)):
        a.box(11.27,float(y),.9,.48,.13,.4+(i%3)*.08,["#8aaba0","#b9c5bc","#b89371"][i%3])
    # Garage facade: battery and charger stay visible with the roof in place.
    a.box(12,8.9,.05,4,.2,2.7,"#d7ddd3")
    a.box(15.9,4,.05,.18,5,.6 if inside else 2.7,"#d7ddd3")
    if not inside:
        for x,w in [(12,.9),(15.6,.4)]:
            a.box(x,3.95,.05,w,.2,2.7,"#d7ddd3")
        a.box(12.9,3.95,2.38,2.7,.2,.37,"#d7ddd3")
        a.box(12.95,3.98,.08,2.6,.08,2.3,"#7a8989")
        for z in np.arange(.13,2.35,.15):
            a.box(12.97,3.91,float(z),2.56,.025,.015,"#9aa8a4")
    a.box(12.14,3.70,.58,.62,.24,1.5,"#edf2e9",.1)
    a.box(12.22,3.65,.75,.46,.035,1.1,dark,.045)
    a.box(15.55,3.73,.18,.48,.38,1.7,dark,.09)
    a.box(15.62,3.68,1.23,.34,.04,.4,"#6e9e99",.035)
    # Contemporary fastback EV with panoramic glazing and turbine alloys.
    modern_ev(a)
    a.m("#334a48").tube([(15.72-.9*t,3.64-1.15*t,1.2-.85*math.sin(math.pi*t)) for t in np.linspace(0,1,20)],.035)
    a.box(10.8,-1,.12,1.18,.56,.93,"#c4ccc3",.06)
    a.m(dark).cylinder((11.35,-1.015,.59),(11.35,-1.05,.59),.34,32)
    for angle in np.linspace(0,2*math.pi,9,endpoint=False):
        a.m(metal).line([(11.35,-1.065,.59),(11.35+.28*math.cos(angle),-1.065,.59+.28*math.sin(angle))])
    # Slate gable roof, structural infill and 13 x 400 W rooftop PV modules.
    if not inside:
        roof = a.m("#3a474f",.10 if mode == "xray" else 1)
        for ya,yb in [(-.3,4.5),(4.5,9.3)]:
            roof.face([(-.3,ya,roof_height(ya)),(12.3,ya,roof_height(ya)),
                       (12.3,yb,roof_height(yb)),(-.3,yb,roof_height(yb))])
        for x in (-.12,12):
            a.m("#e4dfd2",.18 if mode == "xray" else 1).face([(x,0,2.88),(x,9,2.88),(x,4.5,4.4)])
        tiles = a.m("#5a6770",.14 if mode == "xray" else .7)
        for y in np.arange(-.25,9.3,.37):
            tiles.line([(-.25,float(y),roof_height(y)+.008),(12.25,float(y),roof_height(y)+.008)])
        for x in np.arange(-.2,12.3,.68):
            tiles.line([(float(x),-.3,roof_height(-.3)+.008),(float(x),4.5,4.41),(float(x),9.3,roof_height(9.3)+.008)])
        for row,count in [(0,7),(1,6)]:
            for col in range(count):
                x,y,w,d = 1+col*1.4,.55+row*1.83,1.22,1.65
                quad = lambda off: [(x,y,roof_height(y)+off),(x+w,y,roof_height(y)+off),
                                     (x+w,y+d,roof_height(y+d)+off),(x,y+d,roof_height(y+d)+off)]
                a.m("#a7b8ba",.2 if mode=="xray" else 1).face(quad(.07))
                x+=.035; y+=.035; w-=.07; d-=.07
                a.m("#203f5b",.2 if mode=="xray" else 1).face(quad(.085))
                cells = a.m("#658aa2",.25 if mode=="xray" else 1)
                for i in range(1,7):
                    xx=x+i*w/7
                    cells.line([(xx,y,roof_height(y)+.09),(xx,y+d,roof_height(y+d)+.09)])
                for j in range(1,11):
                    yy=y+j*d/11
                    cells.line([(x,yy,roof_height(yy)+.09),(x+w,yy,roof_height(yy)+.09)])
        a.box(11.95,3.9,2.77,4.2,5.3,.18,"#586b68")
    # Branched broadleaf trees with irregular clustered foliage.
    for seed,(x,y,height) in enumerate([(-.9,7.8,3.7),(16.8,8.9,3.5),(-.9,-.8,2.2)]):
        tree(a,x,y,height,seed+42)
    streets(a)
    if district:
        grid_infrastructure(a)
    for y in np.arange(4,8.9,.55):
        a.box(16.3,float(y),.03,.38,.5,.65,"#618369",.15)
    for x,y in [(5.9,3.5),(.5,5.1),(10.5,6),(16.3,3.4)]:
        a.m("#927b64").cylinder((x,y,.05),(x,y,.42),.18,18)
        a.m("#65917a").sphere((x,y,.65),.33,scales=(.8,.8,1.3),resolution=8)
    return a


def icon_lines(kind):
    square=[[(-.6,-.65),(.6,-.65),(.6,.65),(-.6,.65),(-.6,-.65)]]
    circle=lambda r,cy=0:[(r*math.cos(t),cy+r*math.sin(t)) for t in np.linspace(0,2*math.pi,28)]
    if kind == "light":
        return [circle(.4,.2),[(-.22,-.25),(-.22,-.48),(.22,-.48),(.22,-.25)],[(-.16,-.65),(.16,-.65)]]
    if kind == "washer":
        return square+[circle(.38,-.1),[(-.6,.4),(.6,.4)]]
    if kind == "dishwasher":
        return square+[[(-.6,.35),(.6,.35)],[(-.35,.05),(.35,.05)],[(-.35,-.25),(.35,-.25)]]
    if kind == "oven":
        return square+[[(-.6,.32),(.6,.32)],[(-.35,-.4),(.35,-.4),(.35,.05),(-.35,.05),(-.35,-.4)]]
    if kind == "ev":
        return [[(-.65,-.3),(-.48,.25),(.48,.25),(.65,-.3),(-.65,-.3)],[(-.5,-.3),(-.5,-.55)],[(.5,-.3),(.5,-.55)],[(.08,.65),(-.14,.35),(.12,.35),(-.06,.05)]]
    if kind == "water":
        return [[(0,.65),(-.4,-.03),(-.36,-.4),(0,-.58),(.36,-.4),(.4,-.03),(0,.65)]]
    return [[(-.65,-.25),(.65,-.25),(.65,.6),(-.65,.6),(-.65,-.25)],[(0,-.25),(0,-.6)],[(-.35,-.6),(.35,-.6)]]


@lru_cache(maxsize=6)
def batches(mode,district=False):
    """A stable set of material batches across all envelope modes."""
    groups=OrderedDict((opacity,Mesh()) for opacity in STATIC_OPACITIES)
    for (color,opacity),mesh in architecture(mode,district).materials.items():
        groups[opacity].extend(mesh,color)
    # Keep unused material slots mounted, with valid geometry below the ground.
    # Removing/reordering actors can race VTK's asynchronous render/picking work.
    for mesh in groups.values():
        if not mesh.points:
            stub=Mesh(); stub.box(0,0,-.2,.001,.001,.001)
            mesh.extend(stub,"#ffffff")
    return groups


def badge(kind,position):
    x,y,z=position
    mesh,glyph=Mesh(),Mesh()
    transform=lambda u,v:(x+u,y+v*.42,z+v*.91)
    mesh.face([transform(.43*math.cos(t),.43*math.sin(t)) for t in np.linspace(0,2*math.pi,36,endpoint=False)])
    for line in icon_lines(kind):
        glyph.line([(xx,yy-.014,zz+.008) for xx,yy,zz in [transform(u*.38,v*.38) for u,v in line]])
    return mesh,glyph


def flow_actor(snapshot,channel,dot,district=False):
    paths={"solar":[(6.6,2.4,4),(10,3.5,2),(12.45,3.5,1.5)],
           "battery":[(12.45,3.5,1.5),(9.5,2,1.2),(6,2,.5)],
           "ev":[(12.5,3.4,1),(15.7,3.4,1.3),(14.8,2.7,.9)],
           "grid":[(17,-.2,.25),(14,-.4,.35),(6,-.4,.4)]}
    powers={"solar":snapshot.get("pv",0),"battery":snapshot.get("discharge",0)+snapshot.get("charge",0),
            "ev":snapshot.get("appliances",{}).get("ev",0),"grid":snapshot.get("import",0)+snapshot.get("export",0)}
    if district:
        paths["grid"]=[(23.8,-.6,.3),(17.4,-2.1,.3),(12.4,.25,.3)]
    path=paths[channel]
    if (channel=="battery" and snapshot.get("charge",0)>0) or (channel=="grid" and snapshot.get("export",0)>0):
        path=list(reversed(path))
    t=((snapshot.get("phase",0)+dot/3)%1)*2
    segment=min(1,int(t)); fraction=t-segment
    point=np.array(path[segment])*(1-fraction)+np.array(path[segment+1])*fraction
    return {"pickable":False,"position":xyz(point),"visibility":powers[channel]>.015}


@lru_cache(maxsize=3)
def dynamic_templates(prefix):
    snapshot = {}
    result=[]
    for room,info in ROOMS.items():
        x,y=info["xy"]
        on=snapshot.get("lighting_levels",{}).get(room,65)>0
        light,glyph=badge("light",(x,y,2.5))
        light.sphere((x,y,2.21),.11,resolution=8)
        result.append(representation(light,f"{prefix}:light:{room}",AMBER if on else "#57666c",pickable=True,ambient=.9))
        result.append(representation(glyph,f"{prefix}-light-glyph-{room}","#233332" if on else "#b7c6ca",ambient=1))
        pool=Mesh()
        x1,y1,x2,y2=FLOORS[room]
        pool.box(x1+.15,y1+.15,.075,x2-x1-.3,y2-y1-.3,.006)
        pool.sphere((x,y,2.21),.18,scales=(1,1,.8),resolution=6)
        result.append(representation(pool,f"{prefix}-pool-{room}",AMBER,opacity=.15 if on else 0,ambient=1))
    for key,position in DEVICE_POSITIONS.items():
        body,glyph=badge(key,position)
        active=snapshot.get("appliances",{}).get(key,0)>.001
        result.append(representation(body,f"{prefix}:device:{key}",CYAN if active else "#526b76",pickable=True,ambient=.95))
        result.append(representation(glyph,f"{prefix}-device-glyph-{key}","#152c35" if active else "#d9e5e6",ambient=1))
    fill=Mesh(); fill.box(-.14,-.015,0,.28,.03,.85)
    battery=representation(fill,prefix+"-battery-fill",GREEN,local=True,ambient=1)
    battery.actor={"pickable":False,"position":xyz((12.46,3.60,.85)),"scale":[1,1,max(.001,snapshot.get("soc",5)/10)]}
    result.append(battery)
    flow=Mesh()
    for channel in ("solar","battery","ev","grid"):
        for dot in range(3):
            flow.extend(particle_mesh(),CYAN if channel=="solar" else GREEN)
    flow.points=flow_points(snapshot,prefix=="grid")
    result.append(representation(flow,prefix+"-flow-motion",GREEN,local=True,ambient=1))
    bulbs,pools=Mesh(),Mesh()
    for x,y in STREET_LIGHTS:
        bulbs.box(x-.12,y-1.10,3.80,.24,.43,.022)
        pools.sphere((x,y-1.2,-.066),1,scales=(1.5,1.0,.005),resolution=10)
    result.append(representation(bulbs,prefix+"-street-led",AMBER,ambient=1))
    result.append(representation(pools,prefix+"-street-glow",AMBER,opacity=.30,ambient=1))
    return result


@lru_cache(maxsize=1)
def particle_mesh():
    mesh=Mesh(); mesh.sphere((0,0,0),.085,resolution=4)
    return mesh


def flow_points(snapshot,district=False):
    unit=np.asarray(particle_mesh().points).reshape(-1,3)
    points=[]
    for channel in ("solar","battery","ev","grid"):
        for dot in range(3):
            actor=flow_actor(snapshot,channel,dot,district)
            center=np.array(actor["position"] if actor["visibility"] else [0,0,-2.1])
            vertices=unit+center if actor["visibility"] else unit*0+center
            points.extend(round(float(v),5) for v in vertices.ravel())
    return points


def dynamic_values(snapshot,zoom=1):
    values = []
    night=snapshot.get("sky",{}).get("street_on",False)
    response_factor=(1-snapshot.get("dr_dim",50)/100)**.5 if snapshot.get("dr_active",False) else 1
    for room in ROOMS:
        on = snapshot.get("lighting_levels", {}).get(room, 65) > 0
        values.extend([
            ({"pickable": True,"scale":[zoom]*3}, {"color": rgb(AMBER if on else "#57666c"), "ambient": .9}),
            ({"pickable": False,"scale":[zoom]*3}, {"color": rgb("#233332" if on else "#b7c6ca"), "ambient": 1}),
            ({"pickable": False,"scale":[zoom]*3}, {"opacity": response_factor*(.48 if night else .32)*(snapshot.get("lighting_levels",{}).get(room,65)/100)**.5 if on else 0, "ambient": 1}),
        ])
    for key in DEVICE_POSITIONS:
        active = snapshot.get("appliances", {}).get(key, 0) > .001
        values.extend([
            ({"pickable": True,"scale":[zoom]*3}, {"color": rgb(CYAN if active else "#526b76"), "ambient": .95}),
            ({"pickable": False,"scale":[zoom]*3}, {"color": rgb("#152c35" if active else "#d9e5e6"), "ambient": 1}),
        ])
    values.append(({"pickable": False, "position": [v*zoom for v in xyz((12.46,3.60,.85))],
                    "scale": [zoom,zoom,zoom*max(.001,snapshot.get("soc",5)/10)],
                    "visibility": snapshot.get("battery_enabled", True)}, {}))
    values.append(({"pickable":False,"scale":[zoom]*3},{}))
    values.extend([({"pickable":False,"scale":[zoom]*3,"visibility":night},{"ambient":1}),
                   ({"pickable":False,"scale":[zoom]*3,"visibility":night},{"opacity":.32,"ambient":1})])
    return values


def scene_children(prefix,mode="exterior",snapshot=None,zoom=1):
    snapshot=snapshot or {}
    mode=mode if mode in ("exterior","interior","xray") else "exterior"
    data=batches(mode,prefix=="grid")
    dynamic=[]
    for item,(actor,properties) in zip(dynamic_templates(prefix),dynamic_values(snapshot,zoom)):
        dynamic.append(vtk.GeometryRepresentation(id=item.id,actor=actor,mapper=item.mapper,
            property={**item.property,**properties},children=item.children))
    fixed=[representation(mesh,f"{prefix}-material-{i}","#ffffff",opacity)
            for i,(opacity,mesh) in enumerate(data.items())]
    for item in fixed:
        item.actor={"pickable":False,"scale":[zoom]*3}
        item.property.update(ambient=.10 if snapshot.get("sky",{}).get("street_on",False) else .32,
                             diffuse=.28 if snapshot.get("sky",{}).get("street_on",False) else .72)
    return fixed+dynamic


def scene_patch(prefix,mode,snapshot,controls_changed=True,zoom=1):
    patch=Patch(); start=len(batches(mode,prefix=="grid"))
    if controls_changed:
        for i in range(start):
            patch[i]["props"]["actor"]["scale"]=[zoom]*3
            night=snapshot.get("sky",{}).get("street_on",False)
            patch[i]["props"]["property"]["ambient"]=.10 if night else .32
            patch[i]["props"]["property"]["diffuse"]=.28 if night else .72
    for i,(actor,properties) in enumerate(dynamic_values(snapshot,zoom)):
        if i not in (30,31) and not controls_changed:
            continue
        patch[start+i]["props"]["actor"]=actor
        for key,value in properties.items():
            patch[start+i]["props"]["property"][key]=value
    patch[start+31]["props"]["children"][0]["props"]["points"]=flow_points(snapshot,prefix=="grid")
    return patch


def house_view(prefix="home",mode="exterior"):
    return vtk.View(id=prefix+"-scene",children=[] if prefix=="grid" else scene_children(prefix,mode),
        pickingModes=[] if prefix=="grid" else ["click","hover"],cameraPosition=CAMERAS["orbit"],cameraViewUp=[0,0,1],
        background=[.075,.125,.15],cameraParallelProjection=False,
        style={"width":"100%","height":"100%"},className="vtk-house")

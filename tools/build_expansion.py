"""Build the original Ruralive expansion as self-contained glTF binary files."""
import argparse
import io
import json
import math
import random
import struct
from pathlib import Path

import numpy as np
from PIL import Image

TAU = math.tau
PALETTE = {
    "rubber": (33, 36, 42), "steel": (139, 158, 170), "chrome": (191, 207, 214),
    "glass": (72, 137, 156), "red": (189, 42, 45), "blue": (37, 89, 169),
    "orange": (233, 123, 38), "cream": (238, 221, 183), "yellow": (241, 183, 45),
    "brown": (109, 65, 43), "hide": (138, 98, 65), "dark": (42, 27, 24),
    "skin": (198, 137, 103), "skin-dark": (124, 79, 62), "denim": (44, 61, 97),
    "purple": (130, 68, 149), "leaf": (53, 120, 64), "leaf-light": (102, 155, 62),
    "stone": (119, 111, 102), "snow": (222, 236, 242), "sand": (213, 174, 112),
    "water": (39, 126, 166), "foam": (205, 239, 239), "lava": (245, 74, 15),
    "venus": (212, 162, 96), "saturn": (201, 175, 125), "ring": (152, 123, 103),
    "sun": (255, 146, 30), "star": (255, 210, 122), "void": (8, 6, 16),
    "wing": (148, 194, 182), "dino": (92, 131, 62), "dino-back": (158, 99, 48),
}


def quaternion(axis, angle):
    s = math.sin(angle / 2)
    return [a * s for a in axis] + [math.cos(angle / 2)]


def grid(n, m, surface):
    vertices, indices = [], []
    for j in range(m + 1):
        for i in range(n + 1):
            u, v = i / n, j / m
            point, normal = surface(u, v)
            vertices.append((*point, *normal, u, v))
    for j in range(m):
        for i in range(n):
            a = j * (n + 1) + i
            b = a + n + 1
            indices.extend((a, b, a + 1, a + 1, b, b + 1))
    return vertices, indices


def sphere(u, v):
    t, p = TAU * u, math.pi * v
    xyz = (math.sin(p) * math.cos(t), math.cos(p), math.sin(p) * math.sin(t))
    return xyz, xyz


def torus(u, v):
    a, b = TAU * u, TAU * v
    n = (math.cos(a) * math.cos(b), math.sin(b), math.sin(a) * math.cos(b))
    return (math.cos(a) + .18 * n[0], .18 * n[1], math.sin(a) + .18 * n[2]), n


def solid(top_radius, bottom_radius):
    vertices, indices = [], []
    n = 12
    for i in range(n + 1):
        a = TAU * i / n
        x, z = math.cos(a), math.sin(a)
        dy = (bottom_radius - top_radius) / 2
        length = math.sqrt(1 + dy * dy)
        normal = (x / length, dy / length, z / length)
        for r, y, v in ((bottom_radius, -1, 0), (top_radius, 1, 1)):
            vertices.append((x*r, y, z*r, *normal, i/n, v))
    for i in range(n):
        a = 2*i
        indices.extend((a, a+1, a+2, a+2, a+1, a+3))
    for y, r in ((-1, bottom_radius), (1, top_radius)):
        if not r:
            continue
        start = len(vertices)
        vertices.append((0, y, 0, 0, y, 0, .5, .5))
        for i in range(n):
            a = TAU * i / n
            x, z = math.cos(a), math.sin(a)
            vertices.append((r*x,y,r*z,0,y,0,(1+x)/2,(1+z)/2))
        for i in range(n):
            a, b = start+1+i, start+1+(i+1)%n
            indices.extend((start,b,a) if y > 0 else (start,a,b))
    return vertices, indices


def box():
    vertices, indices = [], []
    for axis in range(3):
        for sign in (-1, 1):
            n = [0, 0, 0]
            n[axis] = sign
            start = len(vertices)
            for x, y in ((-1,-1),(1,-1),(1,1),(-1,1)):
                p = list(n)
                p[(axis+1)%3], p[(axis+2)%3] = x,y
                vertices.append((*p,*n,(x+1)/2,(y+1)/2))
            indices.extend(start+i for i in ((0,1,2,0,2,3) if sign > 0 else (0,2,1,0,3,2)))
    return vertices, indices


sphere_vertices, sphere_faces = grid(12, 8, sphere)
sphere_faces = [index for i in range(0, len(sphere_faces), 3)
                for index in (sphere_faces[i], sphere_faces[i+2], sphere_faces[i+1])]
SHAPES = {"ball": (sphere_vertices, sphere_faces), "ring": grid(20, 6, torus),
          "box": box(), "tube": solid(1, 1), "cone": solid(0, 1),
          "taper": solid(.55, 1)}
X, Y, Z = (1,0,0), (0,1,0), (0,0,1)


class Model:
    def __init__(self, name, clip):
        self.name = name
        self.data = bytearray()
        self.geometry = {}
        self.material = {}
        self.mesh = {}
        self.g = {key: [] for key in ("nodes", "meshes", "materials", "textures", "images",
                                      "bufferViews", "accessors")}
        self.g.update(asset={"version":"2.0", "generator":"Ruralive expansion"}, scene=0,
                      scenes=[{"nodes":[0]}])
        self.g["animations"] = [{"name":clip, "samplers":[], "channels":[]}]
        self.node(name, parent=None)
        self.time = self.accessor([0., .5, 1., 1.5, 2.], "SCALAR", 5126, bounds=True)

    def view(self, data, target=None):
        self.data.extend(b'\0' * (-len(self.data) % 4))
        v = {"buffer":0,"byteOffset":len(self.data),"byteLength":len(data)}
        if target:
            v["target"] = target
        self.data.extend(data)
        self.g["bufferViews"].append(v)
        return len(self.g["bufferViews"])-1

    def accessor(self, values, kind, comp, target=None, bounds=False):
        rows = [(x,) if isinstance(x,(int,float)) else x for x in values]
        flat = [v for row in rows for v in row]
        fmt = {5126:"f", 5123:"H", 5121:"B"}[comp]
        a = {"bufferView":self.view(struct.pack("<" + fmt*len(flat),*flat),target),
             "componentType":comp,"count":len(rows),"type":kind}
        if bounds:
            a["min"] = [min(col) for col in zip(*rows)]
            a["max"] = [max(col) for col in zip(*rows)]
        self.g["accessors"].append(a)
        return len(self.g["accessors"])-1

    def mat(self, name):
        if name in self.material:
            return self.material[name]
        color = PALETTE[name]
        rng = random.Random(name)
        tex = Image.new("RGB", (32,32))
        pixels = []
        for y in range(32):
            for x in range(32):
                if name in {"saturn","ring","venus","sun","lava","water","foam"}:
                    v = 13*math.sin(y*.8+math.sin(x*.32)*1.6) + 8*math.cos(y*.37)
                elif name in {"denim","hide","brown","leaf","leaf-light","dino"}:
                    v = 10*math.sin(x*.6 + .35*math.cos(y*.48)) + 5*(y%2)
                else:
                    v = 3*math.sin(x*.7+y*.53)
                v += rng.randrange(-10,11)
                pixels.append(tuple(max(0,min(255,round(c+v))) for c in color))
        tex.putdata(pixels)
        buf = io.BytesIO()
        tex.save(buf,format="JPEG",quality=78,optimize=True)
        index = len(self.g["materials"])
        self.g["images"].append({"name":name,"bufferView":self.view(buf.getvalue()),"mimeType":"image/jpeg"})
        self.g["textures"].append({"source":index})
        metal = name in {"steel","chrome"}
        mat = {"name":name,"doubleSided":True,
               "pbrMetallicRoughness":{"baseColorTexture":{"index":index},
                                       "metallicFactor":.68 if metal else 0,
                                       "roughnessFactor":.27 if metal or name in {"glass","water"} else .82}}
        if name in {"sun","star","lava"}:
            mat["emissiveTexture"] = {"index":index}
            mat["emissiveFactor"] = [.9,.65,.35]
        self.g["materials"].append(mat)
        self.material[name] = index
        return index

    def mesh_id(self, shape, color):
        key = (shape,color)
        if key not in self.mesh:
            if shape not in self.geometry:
                verts, faces = SHAPES[shape]
                self.geometry[shape] = {
                    "attributes":{
                        "POSITION":self.accessor([v[:3] for v in verts],"VEC3",5126,34962,True),
                        "NORMAL":self.accessor([v[3:6] for v in verts],"VEC3",5126,34962),
                        "TEXCOORD_0":self.accessor([v[6:] for v in verts],"VEC2",5126,34962)},
                    "indices":self.accessor(faces,"SCALAR",5123,34963),
                }
            self.mesh[key] = len(self.g["meshes"])
            self.g["meshes"].append({"primitives":[{**self.geometry[shape],"material":self.mat(color)}]})
        return self.mesh[key]

    def node(self, name, shape=None, color=None, pos=(0,0,0), scale=(1,1,1),
             axis=Y, angle=0, parent=0):
        n = {"name":name}
        if pos != (0,0,0):
            n["translation"] = pos
        if scale != (1,1,1):
            n["scale"] = scale
        if angle:
            n["rotation"] = quaternion(axis,angle)
        if shape:
            n["mesh"] = self.mesh_id(shape,color)
        i = len(self.g["nodes"])
        self.g["nodes"].append(n)
        if parent is not None:
            self.g["nodes"][parent].setdefault("children",[]).append(i)
        return i

    def track(self, node, path, values):
        animation = self.g["animations"][0]
        i = len(animation["samplers"])
        animation["samplers"].append({"input":self.time,"output":self.accessor(
            values,"VEC4" if path=="rotation" else "VEC3",5126)})
        animation["channels"].append({"sampler":i,"target":{"node":node,"path":path}})

    def swing(self, node, axis, amount, rest=0):
        self.track(node,"rotation",[quaternion(axis,rest+a) for a in (0,amount,0,-amount,0)])

    def spin(self, node, axis=Y):
        self.track(node,"rotation",[quaternion(axis,TAU*i/4) for i in range(5)])

    def bob(self, node, amplitude):
        x,y,z = self.g["nodes"][node].get("translation",(0,0,0))
        self.track(node,"translation",[(x,y+d,z) for d in (0,amplitude,0,-amplitude,0)])

    def pulse(self, node, amount):
        scale = self.g["nodes"][node].get("scale",(1,1,1))
        self.track(node,"scale",[[s*(1+d) for s in scale] for d in (0,amount,0,-amount,0)])

    def save(self, directory):
        if not self.g["animations"][0]["channels"]:
            raise ValueError("missing animation")
        self.g["buffers"] = [{"byteLength":len(self.data)}]
        j = json.dumps(self.g,separators=(",",":")).encode()
        j += b' ' * (-len(j)%4)
        b = self.data + b'\0' * (-len(self.data)%4)
        glb = struct.pack("<4sII",b"glTF",2,28+len(j)+len(b))
        glb += struct.pack("<I4s",len(j),b"JSON") + j
        glb += struct.pack("<I4s",len(b),b"BIN\0") + b
        (directory / f"{self.name}.glb").write_bytes(glb)


def local_matrix(node):
    x, y, z, w = node.get("rotation", (0, 0, 0, 1))
    matrix = np.eye(4)
    matrix[:3, :3] = (
        (1 - 2*(y*y + z*z), 2*(x*y - z*w), 2*(x*z + y*w)),
        (2*(x*y + z*w), 1 - 2*(x*x + z*z), 2*(y*z - x*w)),
        (2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x*x + y*y)),
    )
    matrix[:3, :3] *= node.get("scale", (1, 1, 1))
    matrix[:3, 3] = node.get("translation", (0, 0, 0))
    return matrix


def skin_character(m, pelvis):
    """Bake the visible parts into one skinned mesh with one joint weight per vertex."""
    nodes = m.g["nodes"]
    mesh_keys = {index: key for key, index in m.mesh.items()}
    joints, binds, parts = [], [], {}
    parents = {child: i for i, node in enumerate(nodes) for child in node.get("children", [])}

    def world(i):
        local = local_matrix(nodes[i])
        return world(parents[i]) @ local if i in parents else local

    def visit(i):
        joint = len(joints)
        joints.append(i)
        bind = world(i)
        binds.append(np.linalg.inv(bind).flatten(order="F").tolist())
        children = nodes[i].get("children", [])
        nodes[i]["children"] = [child for child in children if "mesh" not in nodes[child]]
        if not nodes[i]["children"]:
            del nodes[i]["children"]
        for child in children:
            part = nodes[child]
            if "mesh" not in part:
                visit(child)
                continue
            shape, material = mesh_keys[part.pop("mesh")]
            matrix = bind @ local_matrix(part)
            normal_matrix = np.linalg.inv(matrix[:3, :3]).T
            verts, faces = SHAPES[shape]
            data = parts.setdefault(material, ([], [], [], [], []))
            positions, normals, uvs, weights, indices = data
            indices.extend(len(positions) + index for index in faces)
            for vertex in verts:
                positions.append((matrix @ (*vertex[:3], 1))[:3])
                normal = normal_matrix @ vertex[3:6]
                normals.append(normal / np.linalg.norm(normal))
                uvs.append(vertex[6:])
                weights.append((joint, 0, 0, 0))

    visit(pelvis)
    primitives = []
    for material, (positions, normals, uvs, joints_per_vertex, indices) in parts.items():
        primitives.append({
            "attributes": {
                "POSITION": m.accessor(positions, "VEC3", 5126, 34962, True),
                "NORMAL": m.accessor(normals, "VEC3", 5126, 34962),
                "TEXCOORD_0": m.accessor(uvs, "VEC2", 5126, 34962),
                "JOINTS_0": m.accessor(joints_per_vertex, "VEC4", 5121, 34962),
                "WEIGHTS_0": m.accessor([(1, 0, 0, 0)] * len(positions), "VEC4", 5126, 34962),
            },
            "indices": m.accessor(indices, "SCALAR", 5123, 34963),
            "material": m.mat(material),
        })
    mesh = len(m.g["meshes"])
    m.g["meshes"].append({"primitives": primitives})
    skin = len(m.g.setdefault("skins", []))
    m.g["skins"].append({"skeleton": pelvis, "joints": joints,
                         "inverseBindMatrices": m.accessor(binds, "MAT4", 5126)})
    nodes[m.node("skinned character")].update(mesh=mesh, skin=skin)


def bar(m, name, a, b, radius, color, parent=0, shape="tube"):
    d = [b[i]-a[i] for i in range(3)]
    length = math.sqrt(sum(x*x for x in d))
    axis = (d[2],0,-d[0])
    norm = math.hypot(axis[0],axis[2])
    axis = tuple(x/norm for x in axis) if norm else X
    return m.node(name,shape,color,tuple((a[i]+b[i])/2 for i in range(3)),
                  (radius,length/2,radius),axis,math.acos(max(-1,min(1,d[1]/length))),parent)


def human(m, name, origin=(0,0,0), skin="skin", outfit="blue", hair="dark", skirt=False,
          seated=False, cave=False, helmet=False, parent=0):
    pelvis = m.node(name+" pelvis",pos=(origin[0],origin[1]+(.63 if seated else .89),origin[2]),parent=parent)
    m.node("hips","ball","hide" if cave else "denim",(0,.03,0),(.19,.14,.12),parent=pelvis)
    spine = m.node(name+" spine",pos=(0,.11,0),parent=pelvis)
    m.node("tunic" if cave else "top","taper",outfit,(0,.18,0),(.24,.23,.145),Z,math.pi,parent=spine)
    if skirt:
        m.node("skirt","taper",outfit,(0,-.16,0),(.27,.19,.18),parent=pelvis)
    head = m.node(name+" head",pos=(0,.53,0),parent=spine)
    m.node("face","ball",skin,(0,.09,0),(.115,.149,.108),parent=head)
    m.node("hair","ball","cream" if helmet else hair,(0,.165,-.016),
           (.137,.124,.124) if helmet else (.119,.095,.108),parent=head)
    for side in (-1,1):
        m.node("eye","ball","dark",(side*.042,.108,.098),(.012,.012,.011),parent=head)
    m.node("nose","ball",skin,(0,.077,.106),(.023,.026,.022),parent=head)
    for side, label in ((-1,"L"),(1,"R")):
        shoulder = m.node("shoulder."+label,pos=(side*.215,.29,0),parent=spine)
        m.node("sleeve","ball",outfit,(side*.026,-.05,0),(.079,.125,.078),parent=shoulder)
        m.node("upper arm","ball",skin,(side*.038,-.125,0),(.051,.145,.056),parent=shoulder)
        elbow = m.node("elbow."+label,pos=(side*.045,-.235,0),axis=X,angle=-.28,parent=shoulder)
        m.node("forearm","ball",skin,(0,-.105,0),(.048,.127,.047),parent=elbow)
        m.node("hand","ball",skin,(0,-.219,0),(.052,.064,.037),parent=elbow)
        hip = m.node("hip."+label,pos=(side*.105,-.04,0),parent=pelvis)
        m.node("thigh","ball",skin if cave else "denim",(0,-.19,0),(.084,.226,.085),parent=hip)
        knee = m.node("knee."+label,pos=(0,-.42,0),parent=hip)
        m.node("shin","ball",skin if cave else "denim",(0,-.17,0),(.063,.199,.067),parent=knee)
        m.node("shoe","ball","hide" if cave else "rubber",(0,-.367,.055),(.077,.058,.135),parent=knee)
        m.swing(shoulder,X,side*(.12 if seated else .36),-1.02 if seated else 0)
        m.swing(hip,X,side*(.12 if seated else .52),-1.31 if seated else 0)
        m.swing(knee,X,.10 if seated else .22,1.32 if seated else .27)
    m.swing(head,Y,.19 if seated else .11)
    if not seated:
        m.bob(pelvis,.028)
    skin_character(m, pelvis)


def car(name, paint, truck=False, driver=False):
    m = Model(name,"Wheels and steering" if driver else "Wheel Roll")
    chassis=m.node("chassis",pos=(0,.43,0))
    m.node("painted body","box",paint,(0,0,0),(.83,.25,1.68),parent=chassis)
    m.node("front hood","box",paint,(0,.24,.97),(.8,.13,.68),parent=chassis)
    m.node("passenger cabin","box","glass" if not driver else "rubber",(0,.49,-.19),(.69,.32,.70),parent=chassis) if not driver else None
    m.node("roof" if not driver else "rear deck","box",paint,(0,.81 if not driver else .31,-.24 if not driver else -1.13),(.72,.055,.72 if not driver else .39),parent=chassis)
    if truck:
        m.node("cargo enclosure","box",paint,(0,.72,-1.02),(.79,.49,.66),parent=chassis)
    for z in (-1.72,1.72):
        m.node("bumper","box","steel",(0,-.09,z),(.82,.075,.078),parent=chassis)
        for x in (-.59,.59):
            m.node("lamp","box","cream" if z>0 else "red",(x,.14,z),(.17,.09,.06),parent=chassis)
    for x in (-.88,.88):
        for z in (-1.13,1.13):
            axle=m.node("wheel",pos=(x,.32,z))
            m.node("tire","tube","rubber",scale=(.315,.12,.315),axis=Z,angle=math.pi/2,parent=axle)
            m.node("hub","tube","chrome",scale=(.17,.125,.17),axis=Z,angle=math.pi/2,parent=axle)
            m.node("hub spoke","box","steel",(math.copysign(.13,x),0,0),(.013,.14,.024),parent=axle)
            m.spin(axle,X)
    if driver:
        seat=m.node("driver seat",pos=(-.29,.0,-.24),scale=(.72,.72,.72),parent=chassis)
        human(m,"driver",outfit="red",seated=True,parent=seat)
        m.node("steering wheel","ring","rubber",(-.3,.68,.39),(.16,.11,.16),axis=X,angle=1.13,parent=chassis)
    return m


def cycle(name, motor=False, rider=False):
    m=Model(name,"Ride" if rider else "Wheel Roll")
    for z in (-.77,.77):
        w=m.node("wheel axle",pos=(0,.38,z))
        m.node("tire","ring","rubber",scale=(.35,.20 if motor else .085,.35),axis=Z,angle=math.pi/2,parent=w)
        m.node("hub","tube","steel",scale=(.055,.10,.055),axis=Z,angle=math.pi/2,parent=w)
        for i in range(6):
            a=i*TAU/6
            bar(m,"spoke",(0,0,0),(0,.34*math.cos(a),.34*math.sin(a)),.012,"chrome",w)
        m.spin(w,X)
    for a,b in [((0,.38,-.77),(0,.82,-.20)),((0,.82,-.20),(0,.79,.56)),
                ((0,.79,.56),(0,.40,.77)),((0,.39,-.11),(0,.82,-.20)),
                ((0,.39,-.11),(0,.79,.56)),((0,.39,-.11),(0,.38,-.77))]:
        bar(m,"frame",a,b,.059 if motor else .028,"red")
    m.node("saddle","ball","rubber",(0,.88,-.23),(.13,.052,.28 if motor else .16))
    bar(m,"handlebars",(-.32,.95,.62),(.32,.95,.62),.032,"steel")
    if motor:
        m.node("engine","box","steel",(0,.49,.0),(.19,.19,.25))
        m.node("fuel tank","ball","red",(0,.81,.19),(.22,.16,.32))
        m.node("headlight","ball","cream",(0,.82,.73),(.14,.13,.09))
    if rider:
        human(m,"rider",(0,.26,-.18),outfit="purple",seated=True,helmet=True)
    return m


def creature(name, dinosaur=False, rabbit=False):
    m=Model(name,"Hop" if rabbit else "Trot")
    body=m.node("body pivot",pos=(0,.67 if not rabbit else .29,0))
    color="dino" if dinosaur else "hide"
    m.node("body","ball",color,scale=(.23,.29,.48),parent=body)
    head=m.node("neck and head",pos=(0,.24,.32),parent=body)
    m.node("neck","ball",color,(0,.02,.10),(.13,.28,.15),X,-.28,head)
    m.node("head","ball",color,(0,.22,.22),(.17,.16,.26),parent=head)
    for side in (-1,1):
        m.node("eye","ball","dark",(side*.135,.25,.34),(.03,.034,.037),parent=head)
        if rabbit:
            m.node("ear","ball","brown",(side*.093,.43,.17),(.045,.23,.052),Z,side*.20,head)
    if not dinosaur and not rabbit:
        m.node("mane","ball","dark",(0,.17,.015),(.13,.30,.10),X,-.22,head)
        m.node("muzzle","ball","brown",(0,.16,.43),(.119,.104,.13),parent=head)
        for side in (-1,1):
            m.node("ear","ball","hide",(side*.091,.42,.17),(.036,.10,.041),Z,side*.14,head)
    m.swing(head,X,.14)
    tail=m.node("tail",pos=(0,.11,-.40),parent=body)
    bar(m,"tail",(0,0,-.64 if dinosaur else -.27),(0,0,0),.11,color,tail,"cone")
    m.swing(tail,Y,.35)
    if dinosaur:
        for z in (-.43,-.24,-.04,.15):
            m.node("dorsal crest","cone","dino-back",(0,.34,z),(.095,.14,.12),parent=body)
    for side in (-1,1):
        for front in (-1,1):
            leg=m.node("leg pivot",pos=(side*.16,-.10,front*.28),parent=body)
            length=.48 if not rabbit else .12
            m.node("leg","taper",color,(0,-length/2,0),(.071,length/2,.073),Z,math.pi,leg)
            m.node("foot","ball","dark",(0,-length,.036),(.065,.054,.11),parent=leg)
            m.swing(leg,X,side*front*.48)
    m.bob(body,.036)
    return m


def insect(name, mosquito=False, butterfly=False):
    m=Model(name,"Wingbeat")
    abdomen=m.node("abdomen","ball","dark",(0,.62,-.14),(.11,.11,.32 if mosquito else .20))
    m.node("thorax","ball","brown",(0,.63,.10),(.15,.13,.16))
    m.node("head","ball","dark",(0,.65,.28),(.12,.10,.13))
    for sign in (-1,1):
        m.node("eye","ball","red",(sign*.09,.68,.32),(.065,.065,.075))
        wing=m.node("wing hinge",pos=(sign*.10,.69,.10))
        m.node("outer wing","ball","orange" if butterfly else "wing",(sign*.26,0,.02),(.28,.023,.20 if butterfly else .085),parent=wing)
        if butterfly:
            m.node("hindwing","ball","purple",(sign*.18,0,-.15),(.21,.024,.17),parent=wing)
        m.swing(wing,Z,sign*.94)
        for z in (-.16,0,.15):
            bar(m,"leg",(sign*.09,.58,z),(sign*(.36 if mosquito else .22),.33,z-.12),.014,"dark")
    if mosquito:
        bar(m,"proboscis",(0,.65,.35),(0,.56,.71),.013,"dark")
    m.pulse(abdomen,.075)
    return m


def plant(name, cactus=False, flower=False):
    m=Model(name,"Breeze")
    branch=m.node("rooted stem")
    if cactus:
        m.node("stem","ball","leaf",(0,.63,0),(.19,.65,.19),parent=branch)
        for sign,y in ((-1,.55),(1,.83)):
            bar(m,"arm",(0,y,0),(sign*.32,y,0),.09,"leaf",branch)
            m.node("shoot","ball","leaf-light",(sign*.34,y+.15,0),(.094,.22,.09),parent=branch)
        for i in range(20):
            a=i*2.399
            m.node("areole","ball","cream",(.186*math.cos(a),.22+i*.043,.186*math.sin(a)),(.016,.018,.016),parent=branch)
    else:
        bar(m,"stem",(0,0,0),(0,1.34,0),.033,"leaf",branch)
        for i in range(6):
            a=i*2.399
            m.node("leaf","ball","leaf-light",(.17*math.cos(a),.26+i*.125,.17*math.sin(a)),(.25,.034,.105),Y,-a,branch)
        if flower:
            m.node("disc","ball","brown",(0,1.41,0),(.19,.07,.19),parent=branch)
            for i in range(12):
                a=TAU*i/12
                m.node("petal","ball","yellow",(.26*math.cos(a),1.39,.26*math.sin(a)),(.158,.039,.067),Y,-a,branch)
        else:
            for i in range(10):
                a=TAU*i/10
                m.node("canopy leaf","ball","leaf",(.34*math.cos(a),1.29,.34*math.sin(a)),(.48,.054,.12),Y,-a,branch)
    m.swing(branch,Z,.11)
    return m


def space(name, kind):
    m=Model(name,"Rotation" if kind != "star" else "Pulse")
    if kind=="black-hole":
        m.node("event horizon","ball","void",scale=(.61,.61,.61))
        d=m.node("accretion disk")
        for i in range(5):
            r=.68+.15*i
            m.node("hot orbit","ring",("lava","sun","orange","ring","purple")[i],
                   scale=(r,.07+i*.018,r),axis=X,angle=.23,parent=d)
        for i in range(12):
            a=TAU*i/12
            m.node("hot knot","ball","sun",(1.05*math.cos(a),.11*math.sin(a),1.05*math.sin(a)),(.11,.044,.064),parent=d)
        m.spin(d)
        return m
    orb=m.node("rotating sphere","ball",kind)
    if kind=="saturn":
        frame=m.node("tilted ring plane",axis=Z,angle=.39)
        for i in range(5):
            r=1.24+.20*i
            m.node("ring band","ring","ring" if i%2 else "saturn",scale=(r,.025,r),parent=frame)
        moon=m.node("moon orbit",parent=frame)
        m.node("moon","ball","stone",(2.38,.08,0),(.13,.13,.13),parent=moon)
        m.spin(moon)
    if kind in {"sun","star"}:
        rays=m.node("corona")
        for i in range(16):
            a=TAU*i/16
            bar(m,"flare",(math.cos(a),math.sin(a),0),
                (math.cos(a)*(1.23+i%3*.10),math.sin(a)*(1.23+i%3*.10),0),
                .11,kind,rays,"cone")
        m.spin(rays,Z)
        m.pulse(orb,.055)
    m.spin(orb)
    return m


def terrain(name, kind):
    m=Model(name,{"river":"Current","wave":"Wave Break","volcano":"Eruption",
                  "cave":"Drips","sand":"Wind","mountain":"Cloud Drift"}[kind])
    if kind in {"river","wave","sand"}:
        def surface(u,v):
            x,z=(u-.5)*5,(v-.5)*4.2
            if kind=="wave":
                y=.20+1.48*math.exp(-((z-.18)*2)**2)*(.85+.15*math.cos(x*1.6))
            elif kind=="sand":
                y=.25+.18*math.sin(x*1.6+z*.53)+.08*math.sin(z*2-x)
            else:
                y=.055+.025*math.sin(z*2+x*3)
            return (x,y,z),Y
        SHAPES[name]=grid(18,18,surface)
        land=m.node("surface",name,"sand" if kind=="sand" else "water")
        if kind=="wave":
            for i in range(11):
                x=(i-5)*.46
                crest=m.node("foam crest","ball","foam",(x,1.49+.22*math.cos(x*1.6),.36),(.32,.155,.22))
                m.pulse(crest,.19)
                m.bob(crest,.13)
            m.swing(land,X,.11)
        elif kind=="river":
            for sign in (-1,1):
                for j in range(6):
                    m.node("river bank","ball","stone",(sign*(2.28+.21*math.sin(j)),.04,(j-2.5)*.74),(.49,.21,.53))
            for i in range(10):
                p=m.node("surface current","ball","foam",((i%4-1.5)*.66,.092,(i//4-1)*.84),(.068,.012,.28))
                x,y,z=m.g["nodes"][p]["translation"]
                m.track(p,"translation",[(x,y,z+d) for d in (0,.15,.35,.15,0)])
        else:
            for i in range(18):
                rng=random.Random(i)
                x,z=rng.uniform(-2.3,2.3),rng.uniform(-1.9,1.9)
                p=m.node("windblown grain","ball","cream",(x,.54,z),(.025,.025,.025))
                m.track(p,"translation",[(x+d,.54+h,z) for d,h in ((0,0),(.20,.09),(.34,.02),(.18,.04),(0,0))])
        return m
    if kind=="mountain":
        for x,y,z,r in ((-.98,.67,.1,1.05),(.45,1.00,-.4,1.40),(1.45,.52,.40,.89)):
            m.node("rock peak","cone","stone",(x,y,z),(r,y,r*.82))
            m.node("snow cap","cone","snow",(x,y*1.69,z),(r*.31,y*.31,r*.255))
        cloud=m.node("cloud bank",pos=(-.28,1.56,.32))
        for i in range(5):
            m.node("cloud","ball","snow",((i-2)*.26,.06*math.sin(i),0),(.30,.12,.17),parent=cloud)
        m.track(cloud,"translation",[(-.28+d,1.56,.32) for d in (0,.38,.65,.38,0)])
    elif kind=="cave":
        m.node("cave bed","box","stone",(0,-.13,0),(1.63,.15,1.38))
        for j in range(3):
            for i in range(9):
                a=math.pi*i/8
                m.node("limestone arch","ball","stone",(1.38*math.cos(a),1.40*math.sin(a),.82-j*.69),(.41,.44,.48))
        for i in range(5):
            x=(i-2)*.44
            m.node("stalactite","cone","stone",(x,1.29,-.44),(.105,.28,.12),Z,math.pi)
            p=m.node("water drop","ball","water",(x,.91,-.44),(.033,.066,.033))
            m.track(p,"translation",[(x,y,-.44) for y in (.91,.71,.33,.10,.91)])
            m.track(p,"scale",[(.033*a,.066*a,.033*a) for a in (0.01,1,1,.08,.01)])
    else:
        m.node("basalt cone","taper","stone",(0,.73,0),(1.58,.73,1.48))
        m.node("crater rim","ring","dark",(0,1.47,0),(.63,.22,.60))
        m.node("lava lake","tube","lava",(0,1.47,0),(.52,.032,.50))
        for i in range(9):
            a=i*2.399
            p=m.node("lava bomb","ball","lava",(.18*math.cos(a),1.50,.18*math.sin(a)),(.056,.081,.056))
            m.track(p,"translation",[(r*math.cos(a),y,r*math.sin(a)) for r,y in
                                     ((.18,1.50),(.29,1.96+i*.05),(.52,1.85),(.78,1.18),(.18,1.50))])
            m.track(p,"scale",[(.056*f,.081*f,.056*f) for f in (.05,1,1,.10,.05)])
    return m


def everyday(name, kind):
    m=Model(name,{"spoon":"Turntable","gear":"Mesh","experiment":"Reaction",
                  "drum":"Beat","guitar":"String Vibration"}[kind])
    if kind=="spoon":
        m.node("handle","taper","steel",(0,.11,-.34),(.06,.47,.035),X,math.pi/2)
        m.node("spoon bowl","ball","chrome",(0,.10,.29),(.18,.045,.28))
        m.spin(0)
    elif kind=="gear":
        for x,r,direction in ((-.37,.47,1),(.47,.36,-1)):
            axle=m.node("gear axle",pos=(x,.65,0))
            m.node("gear hub","tube","steel",scale=(r,.115,r),axis=X,angle=math.pi/2,parent=axle)
            count=12 if direction==1 else 9
            for i in range(count):
                a=TAU*i/count
                m.node("tooth","box","chrome",(r*math.cos(a),r*math.sin(a),0),
                       (.089,.056,.11),Z,a,axle)
            m.track(axle,"rotation",[quaternion(Z,direction*TAU*i/4) for i in range(5)])
    elif kind=="experiment":
        m.node("worktop","box","stone",(0,.07,0),(.83,.07,.47))
        m.node("flask body","ball","glass",(-.35,.42,0),(.25,.27,.25))
        m.node("liquid","ball","purple",(-.35,.34,.05),(.21,.15,.23))
        m.node("flask neck","tube","glass",(-.35,.69,0),(.084,.16,.084))
        m.node("beaker","tube","glass",(.31,.31,0),(.21,.17,.21))
        m.node("liquid surface","tube","blue",(.31,.49,0),(.18,.018,.18))
        for i in range(7):
            x=-.35+.05*math.sin(i)
            p=m.node("reaction bubble","ball","cream",(x,.83+i*.085,.02),(.037,.037,.037))
            m.bob(p,.09+i*.007)
            m.pulse(p,.25)
    elif kind=="drum":
        m.node("shell","tube","red",(0,.40,0),(.39,.33,.39))
        for y in (.09,.72):
            m.node("rim","ring","steel",(0,y,0),(.38,.08,.38))
        m.node("drum head","tube","cream",(0,.73,0),(.385,.023,.385))
        for side in (-1,1):
            stick=m.node("drumstick pivot",pos=(side*.27,1.02,-.27))
            bar(m,"drumstick",(0,0,0),(0,-.16,.54),.024,"sand",stick)
            m.swing(stick,X,side*.38)
    else:
        for y,sx,sy in ((.39,.31,.36),(.74,.24,.27)):
            m.node("soundboard","ball","brown",(0,y,0),(sx,sy,.12))
        m.node("sound hole","ball","dark",(0,.67,.111),(.098,.098,.022))
        m.node("fretboard","box","hide",(0,1.17,.035),(.079,.48,.052))
        m.node("headstock","box","brown",(0,1.73,.032),(.105,.114,.064))
        for i in range(7):
            m.node("fret","box","steel",(0,.89+i*.098,.092),(.076,.006,.007))
        for i in range(6):
            x=(i-2.5)*.020
            string=bar(m,"string",(x,.34,.133),(x,1.72,.124),.004,"chrome")
            m.swing(string,Z,.011)
    return m


def models():
    yield car("city-hatchback", "red")
    yield car("utility-pickup", "blue",truck=True)
    yield car("open-car-with-driver", "orange",driver=True)
    yield cycle("city-bicycle")
    yield cycle("road-motorcycle",motor=True)
    yield cycle("motorcycle-with-rider",motor=True,rider=True)
    for name,skin,outfit,hair,skirt,cave in [
        ("woman-in-dress","skin-dark","purple","dark",True,False),
        ("woman-in-workwear","skin","orange","brown",False,False),
        ("man-in-denim","skin","blue","dark",False,False),
        ("man-in-outdoor-jacket","skin-dark","leaf","dark",False,False),
        ("cavewoman","skin","hide","brown",True,True),
        ("caveman","skin-dark","brown","dark",False,True),
    ]:
        m=Model(name,"Walk in Place")
        human(m,"character",skin=skin,outfit=outfit,hair=hair,skirt=skirt,cave=cave)
        yield m
    yield creature("chestnut-horse")
    yield creature("wild-rabbit",rabbit=True)
    yield creature("crested-dinosaur",dinosaur=True)
    yield insect("housefly")
    yield insect("mosquito",mosquito=True)
    yield insect("butterfly",butterfly=True)
    yield plant("desert-cactus",cactus=True)
    yield plant("sunflower",flower=True)
    yield plant("young-palm")
    for name,kind in [("planet-venus","venus"),("planet-saturn","saturn"),
                      ("solar-star","sun"),("variable-star","star"),("black-hole","black-hole")]:
        yield space(name,kind)
    for name,kind in [("sand-dunes","sand"),("rocky-river","river"),("snowy-mountains","mountain"),
                      ("limestone-cave","cave"),("erupting-volcano","volcano"),("giant-breaking-wave","wave")]:
        yield terrain(name,kind)
    for name,kind in [("steel-spoon","spoon"),("mechanical-gears","gear"),
                      ("chemical-reaction-bench","experiment"),("snare-drum","drum"),
                      ("acoustic-guitar","guitar")]:
        yield everyday(name,kind)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("rigged/expansion"))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    entries=[]
    for model in models():
        model.save(args.output)
        file=f"{model.name}.glb"
        entries.append({"file":file,"animation":model.g["animations"][0]["name"],
                        "bytes":(args.output/file).stat().st_size})
    (args.output/"manifest.json").write_text(json.dumps(
        {"license":"LicenseRef-Ruralive-Models-1.0","models":entries}, indent=2)+"\n")


if __name__=="__main__":
    main()

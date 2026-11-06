"""Original CC0 places and birds for Ruralive Set Film."""
import json
import math
from pathlib import Path
from random import Random

from build_expansion import Model, PALETTE, X, Y, Z, TAU, bar

PALETTE.update({
    "island-green": (69, 127, 61), "island-black": (59, 53, 59),
    "ocean-blue": (32, 110, 145), "lagoon-blue": (51, 164, 159),
    "terracotta": (162, 76, 55), "plaster": (220, 209, 186),
    "wood": (142, 99, 67), "bird-white": (225, 224, 215),
    "bird-grey": (119, 129, 142), "bird-black": (44, 47, 57),
})


def island(style):
    m = Model(style + "-island", "Island Breeze")
    rng = Random(style)
    m.node("surrounding water", "tube", "ocean-blue", scale=(3.2, .055, 2.55))
    base = "island-black" if style == "volcanic" else "stone" if style == "rocky" else "sand"
    if style == "atoll":
        m.node("shallow lagoon", "tube", "lagoon-blue", (0, .066, 0), (1.88, .012, 1.46))
        for i in range(21):
            a = TAU * i / 21
            m.node("coral sand bank", "ball", "sand",
                   (1.78*math.cos(a), .075, 1.32*math.sin(a)),
                   (.41, .15+rng.random()*.05, .36))
    else:
        m.node("coastline", "ball", base, (0, .09, 0), (2.09, .28, 1.61))
        m.node("island interior", "ball", "island-green" if style == "tropical" else base,
               (-.08, .27, -.08), (1.68, .33, 1.25))
    if style in ("tropical", "atoll"):
        positions = ((-.66,.40,-.40), (.75,.34,.33), (.30,.36,-.55)) if style == "tropical" else (
            (-1.73,.15,.34), (1.60,.17,-.60))
        for x, y, z in positions:
            tree = m.node("palm sway", pos=(x, y, z))
            bar(m, "palm trunk", (0,0,0), (.13,.78,0), .043, "wood", tree)
            for j in range(7):
                a = TAU*j/7
                m.node("palm frond", "ball", "leaf" if j % 2 else "leaf-light",
                       (.13+.22*math.cos(a),.78,.22*math.sin(a)), (.30,.028,.080), Y,-a,tree)
            m.swing(tree,Z,.10)
    elif style == "volcanic":
        m.node("volcanic cone","taper","island-black",(-.18,.75,-.16),(.89,.60,.76))
        lake = m.node("lava in caldera","tube","lava",(-.18,1.36,-.16),(.44,.020,.37))
        m.pulse(lake,.075)
        for i in range(6):
            smoke = m.node("steam plume","ball","stone",(-.18+i*.07,1.45+i*.13,-.16),
                           (.1+i*.025,.10+i*.025,.09+i*.025))
            m.bob(smoke,.09)
    else:
        for i in range(10):
            x,z=rng.uniform(-1.3,1.3),rng.uniform(-.85,.85)
            m.node("coastal rock","ball","stone",(x,.47,z),(.27,.24+rng.random()*.22,.22))
        gull = m.node("gull path",pos=(0,1.35,0))
        m.node("distant gull","ball","bird-white",(1,0,0),(.24,.031,.075),parent=gull)
        m.spin(gull)
    for i in range(12):
        a = TAU * i / 12
        foam = m.node("surf","ball","foam",(2.18*math.cos(a),.064,1.69*math.sin(a)),
                      (.24,.012,.055),Y,a)
        m.pulse(foam,.24)
    return m


def bird(name, plumage, accent):
    m=Model(name,"Flight")
    m.node("body","ball",plumage,(0,0,.01),(.125,.12,.31))
    m.node("head","ball",plumage,(0,.09,.25),(.098,.091,.102))
    bar(m,"beak",(0,.07,.30),(0,.04,.45),.038,accent,shape="cone")
    m.node("tail","ball",plumage,(0,-.025,-.32),(.12,.033,.21),X,.13)
    for sign in (-1,1):
        m.node("eye","ball","dark",(sign*.080,.111,.29),(.017,.019,.021))
        hinge=m.node("wing pivot",pos=(sign*.09,.02,.045))
        span=.44 if name=="coastal-gull" else .37 if name=="rock-pigeon" else .52
        m.node("inner wing","ball",plumage,(sign*span*.47,0,0),(span*.52,.035,.147),Y,sign*.25,hinge)
        m.node("outer wing","ball",accent,(sign*span*.97,-.01,-.084),(span*.40,.022,.089),Y,sign*.47,hinge)
        m.swing(hinge,Z,sign*.82)
    m.bob(0,.04)
    return m


def house(name, cut=False, modern=False):
    m=Model(name,"House Details")
    w=1.72 if modern else 1.49
    wall="plaster" if modern else "cream"
    roof="steel" if modern else "terracotta"
    m.node("foundation","box","stone",(0,.02,0),(w+.1,.06,1.25))
    for y in (.12,1.37) if modern else (.12,):
        m.node("floor slab","box","wood",(0,y,0),(w,.052,1.19))
    height=2.66 if modern else 1.58
    for x in (-w,w):
        m.node("side wall","box",wall,(x,height*.5,0),(.065,height*.5,1.19))
    m.node("rear wall","box",wall,(0,height*.5,-1.15),(w,height*.5,.064))
    if not cut:
        for x in (-1.22,1.22):
            m.node("front masonry","box",wall,(x,height*.5,1.15),(.25,height*.5,.064))
        m.node("front header","box",wall,(0,height-.17,1.15),(1.10,.17,.064))
        for x in (-.70,.70):
            m.node("window frame","box","wood",(x,.90,1.15),(.35,.33,.049))
            m.node("window pane","box","glass",(x,.90,1.207),(.29,.27,.018))
        door=m.node("door hinge",pos=(-.27,.67,1.14))
        m.node("front door","box","wood",(.27,0,0),(.27,.54,.043),parent=door)
        m.swing(door,Y,.20)
        if modern:
            m.node("flat roof","box",roof,(0,height+.075,0),(w+.16,.084,1.34))
        else:
            for sign in (-1,1):
                m.node("pitched roof","box",roof,(sign*.78,height+.28,0),(.96,.075,1.34),
                       Z,-sign*.39)
    else:
        # Exposed façade plane and furnished rooms, with a continuous open walking area.
        for level in range(2 if modern else 1):
            y=level*1.25
            m.node("sofa base","box","blue",(-.85,y+.31,-.50),(.52,.16,.26))
            m.node("sofa back","box","blue",(-.85,y+.53,-.72),(.52,.23,.075))
            m.node("tabletop","box","wood",(.68,y+.56,-.52),(.40,.046,.27))
            for x in (.36,.99):
                for z in (-.70,-.33):
                    m.node("table leg","tube","wood",(x,y+.33,z),(.027,.22,.027))
            m.node("bed frame","box","wood",(.94,y+.27,.37),(.38,.11,.49))
            m.node("bed linen","box","snow",(.94,y+.39,.37),(.37,.058,.48))
        if modern:
            for i in range(7):
                m.node("stair tread","box","wood",(-1.08,.20+i*.17,.98-i*.15),(.36,.055,.11))
        lamp=m.node("interior lamp","ball","sun",(-.56,1.20,-.44),(.085,.10,.085))
        m.pulse(lamp,.075)
    return m


def well():
    m=Model("stone-well","Bucket Lift")
    for row in range(4):
        for i in range(15):
            a=TAU*(i+.5*(row%2))/15
            m.node("stone course","box","stone",(.66*math.cos(a),.11+row*.16,.66*math.sin(a)),
                   (.17,.077,.13),Y,-a)
    m.node("water down the shaft","tube","water",scale=(.55,.04,.55))
    for x in (-.76,.76):
        bar(m,"wood support",(x,0,0),(x,1.64,0),.058,"wood",shape="box")
    bar(m,"spindle",(-.82,1.37,0),(.82,1.37,0),.063,"wood")
    bucket=m.node("bucket and rope")
    bar(m,"rope",(0,.72,0),(0,1.36,0),.014,"hide",bucket)
    m.node("bucket","taper","steel",(0,.61,0),(.14,.16,.14),Z,math.pi,bucket)
    m.bob(bucket,.26)
    return m


def main():
    out=Path("rigged/places")
    out.mkdir(parents=True,exist_ok=True)
    models=[island(style) for style in ("tropical","atoll","rocky","volcanic")]
    models.extend(bird(*row) for row in (
        ("coastal-gull","bird-white","bird-black"),
        ("rock-pigeon","bird-grey","purple"),
        ("golden-eagle","hide","yellow")))
    models.extend(house(name,cut,modern) for name,cut,modern in (
        ("cottage-exterior",False,False),("cottage-section",True,False),
        ("modern-house-exterior",False,True),("modern-house-section",True,True)))
    models.append(well())
    entries=[]
    for model in models:
        model.save(out)
        file=model.name+".glb"
        entries.append({"file":file,"bytes":(out/file).stat().st_size,
                        "animation":model.g["animations"][0]["name"]})
    (out/"manifest.json").write_text(json.dumps({"license":"CC0-1.0","models":entries},indent=2)+"\n")


if __name__=="__main__":
    main()

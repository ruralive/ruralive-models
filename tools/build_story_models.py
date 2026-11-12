"""Original props and cast for The Echo of Vael and The Margin of Mira."""
import json
import math
from pathlib import Path

from build_expansion import PALETTE, X, Y, Z, TAU, bar
from build_motion_props import Prop, box, sphere, lift
from build_farm_and_worksite import character

PALETTE.update({
    "pewter": (152, 158, 160), "porcelain": (220, 216, 205),
    "graphite": (43, 45, 47), "paper-white": (228, 225, 213),
    "story-teal": (45, 208, 183), "story-red": (229, 44, 53),
    "story-gold": (237, 184, 71),
})


def turn(m, name, material, origin, radius, parent=0, axis=Y):
    return m.node(name,"ring",material,origin,(radius,.07,radius),axis,
                  math.pi/2 if axis == X else 0,parent)


def ring_city():
    m=Prop("vael-ring-city","Orbital Rotation",18)
    core=m.node("city turntable")
    for r in (1.05,1.65,2.25):
        turn(m,"transit ring","pewter",(0,.11,0),r,core)
        for i in range(24):
            a=i*TAU/24
            h=.13+.35*(.5+.5*math.sin(i*2.17+r))
            x,z=r*math.cos(a),r*math.sin(a)
            tower=m.node("city tower","box","porcelain",(x,h+.15,z),(.086,h,.088),Y,-a,core)
            box(m,"window stack","graphite",(0,.1,.093),(.046,.085,.009),tower)
    sphere(m,"central dome","glass",(0,.25,0),(.43,.32,.43),core)
    m.rotate(core,Y,lambda t:TAU*t)
    return m


def vehicle(name, bus=False):
    m=Prop(name,"Cruise in Place",5)
    root=m.node("suspension")
    box(m,"underframe","graphite",(0,.28,0),(.65,.11,1.87),root)
    box(m,"floor","pewter",(0,.47,0),(.67,.074,1.85),root)
    box(m,"roof","porcelain",(0,1.62,0),(.69,.08,1.84),root)
    for z in (-1.64,-.85,0,.85,1.64):
        for x in (-.63,.63):
            box(m,"window pillar","porcelain",(x,1.06,z),(.032,.54,.041),root)
    box(m,"windscreen","glass",(0,1.15,1.84),(.64,.44,.028),root)
    box(m,"front panel","graphite",(0,.64,1.85),(.66,.15,.034),root)
    for x in (-.43,.43):
        sphere(m,"headlight","story-teal" if not bus else "cream",(x,.62,1.89),(.12,.057,.035),root)
    for z in (-1.28,-.69,-.1,.49,1.08):
        for x in (-.40,.40):
            box(m,"passenger seat","graphite",(x,.63,z),(.17,.13,.19),root)
            box(m,"seat back","pewter",(x,.91,z-.17),(.17,.20,.035),root)
    if bus:
        for x in (-.68,.68):
            for z in (-1.17,1.17):
                axle=m.node("wheel axle",pos=(x,.23,z))
                m.node("tire","tube","rubber",scale=(.23,.095,.23),axis=Z,angle=math.pi/2,parent=axle)
                box(m,"wheel hub","steel",(math.copysign(.098,x),0,0),(.013,.12,.04),axle)
                m.rotate(axle,X,lambda t:TAU*2*t)
    m.translate(root,lambda t:(0,.024*math.sin(TAU*2*t),0))
    return m


def meridian():
    m=Prop("meridian-hymn","Engine and Roll",9)
    craft=m.node("ship attitude")
    m.node("fuselage","taper","porcelain",(0,0,0),(.43,1.21,.43),X,math.pi/2,craft)
    m.node("flight nose","cone","porcelain",(0,0,1.52),(.29,.31,.29),X,math.pi/2,craft)
    sphere(m,"flight deck glass","glass",(0,.248,.94),(.25,.13,.37),craft)
    for side in (-1,1):
        m.node("wing","box","pewter",(side*.51,-.06,-.36),(.65,.038,.43),Y,side*.28,craft)
        m.node("engine pod","tube","graphite",(side*.59,.005,-.94),(.16,.39,.16),X,math.pi/2,craft)
        flare=m.node("engine core","cone","story-teal",(side*.59,.005,-1.48),(.16,.29,.16),X,-math.pi/2,craft)
        m.scale_over(flare,lambda t:1+.19*math.sin(TAU*4*t))
    m.rotate(craft,Z,lambda t:.22*math.sin(TAU*t))
    return m


def room(name, kind):
    m=Prop(name,"Room Details",8)
    box(m,"floor","pewter",(0,-.07,0),(1.86,.068,1.34))
    box(m,"back wall","porcelain",(0,1.13,-1.28),(1.86,1.13,.054))
    box(m,"return wall","porcelain",(-1.85,1.13,0),(.052,1.13,1.28))
    box(m,"wall trim","graphite",(0,.14,-1.21),(1.84,.042,.027))
    if kind in ("studio","edit","apartment","control"):
        for i,x in enumerate((-1.1,0,1.1) if kind in ("studio","control") else (-.55,.67)):
            box(m,"desk top","pewter",(x,.75,-.62),(.43,.045,.31))
            for sign in (-1,1):
                box(m,"desk leg","graphite",(x+sign*.32,.36,-.62),(.028,.36,.21))
            box(m,"monitor stand","graphite",(x,.89,-.79),(.043,.14,.04))
            box(m,"monitor bezel","graphite",(x,1.10,-.80),(.29,.19,.038))
            screen=box(m,"screen","story-teal" if kind=="control" else "glass",(x,1.10,-.756),(.266,.168,.011))
            m.scale_over(screen,lambda t,j=i:1+.022*math.sin(TAU*2*t+j))
            box(m,"keyboard","graphite",(x,.804,-.47),(.23,.014,.089))
        if kind=="studio":
            for i in range(6):
                x=-1.42+.55*(i%3); y=1.55+.29*(i//3)
                box(m,"pinned storyboard page","paper-white",(x,y,-1.212),(.22,.124,.009))
                box(m,"pencil composition","graphite",(x,y,-1.198),(.157,.007,.003))
    else:
        for x in (-1.02,0,1.02):
            box(m,"bed pedestal","graphite",(x,.24,-.44),(.25,.23,.57))
            box(m,"cradle pad","porcelain",(x,.50,-.44),(.29,.06,.62))
            box(m,"head cushion","pewter",(x,.585,-.87),(.222,.04,.15))
            box(m,"side rail","pewter",(x+.29,.70,-.44),(.019,.10,.56))
            sign=box(m,"monitor indicator","story-red" if kind=="clinic" else "story-teal",(x,1.19,-1.20),(.16,.06,.016))
            m.scale_over(sign,lambda t:1+.16*math.sin(TAU*3*t))
    return m


def crystal(name, lantern=False, kite=False):
    m=Prop(name,"Glow and Drift" if lantern else "Hover and Turn",5.5)
    rig=m.node("floating form",pos=(0,0 if kite else .86,0))
    if lantern:
        sphere(m,"light core","story-gold",(0,0,0),(.18,.24,.18),rig)
        for i in range(6):
            a=i*TAU/6
            bar(m,"lantern rib",(.20*math.cos(a),-.20,.20*math.sin(a)),
                (.20*math.cos(a),.21,.20*math.sin(a)),.023,"pewter",rig)
        m.node("lantern cap","cone","pewter",(0,.27,0),(.22,.10,.22),parent=rig)
    elif kite:
        sphere(m,"Kite core","story-teal",(0,0,0),(.19,.19,.19),rig)
        for a in (0,math.pi/3,-math.pi/3):
            m.node("gyroscope hoop","ring","pewter",(0,0,0),(.37,.081,.37),X,a,rig)
    else:
        for pos,scale,angle in [
            ((0,.26,0),(.21,.34,.14),.07),((0,.72,0),(.14,.17,.13),.34),
            ((-.28,.32,0),(.069,.27,.072),-.31),((.28,.32,0),(.069,.27,.072),.31),
            ((-.12,-.28,0),(.077,.31,.079),-.17),((.12,-.28,0),(.077,.31,.079),.17),
        ]:
            shape="box" if name=="lumen-glass-figure" else "taper"
            m.node("glass panel" if shape=="box" else "faceted body","box" if shape=="box" else "taper",
                   "story-teal" if pos[1]>.1 else "glass",pos,scale,Z,angle,rig)
        sphere(m,"inner light","story-teal",(0,.27,.14),(.10,.095,.028),rig)
    m.rotate(rig,Y,lambda t:(TAU*t if lantern or kite else .42*math.sin(TAU*t)))
    m.translate(rig,lambda t:(0,(0 if kite else .86)+.095*math.sin(TAU*t),0))
    return m


def desk_prop(kind):
    slug,name,seconds={
        "stylus":("mira-stylus-and-page","Ink Stroke",5),
        "laptop":("director-laptop","Close and Open",6),
        "phone":("mira-phone","Incoming Signal",4),
        "pen":("directors-pen-jar","Gold Glint",4),
        "light-table":("studio-light-table","Light Table Pulse",6),
        "archive":("archive-panel-stack","Pages Unfold",7),
        "lance":("severance-lance","Arm and Fire",7),
        "visor":("lyra-visor","Visor Signal",5),
    }[kind]
    m=Prop(slug,name,seconds)
    if kind=="stylus":
        box(m,"page","paper-white",(0,.015,0),(.92,.015,.62))
        stroke=box(m,"growing black stroke","graphite",(-.69,.035,.03),(.001,.002,.019))
        tip=m.node("moving stylus",pos=(-.69,.04,.03))
        bar(m,"stylus body",(0,.09,0),(.17,.74,-.23),.035,"graphite",tip)
        bar(m,"nib",(0,0,0),(0,.11,0),.016,"pewter",tip,"cone")
        amount=lambda t:lift(t,.03,.68,.82,.98)
        m.translate(tip,lambda t:(-.69+1.28*amount(t),.04+.13*lift(t,.69,.79,.91,.99),.03))
        m.translate(stroke,lambda t:(-.69+.64*amount(t),.035,.03))
        m.track(stroke,"scale",[(.001+.64*amount(i/48),.002,.019) for i in range(49)])
    elif kind=="laptop":
        box(m,"base","graphite",(0,.036,0),(.57,.035,.39))
        for i in range(6):
            box(m,"keyboard row","pewter",(0,.077,-.22+i*.063),(.47,.007,.023))
        lid=m.node("hinge",pos=(0,.068,-.37))
        box(m,"lid","graphite",(0,.006,.34),(.57,.024,.35),lid)
        box(m,"screen","glass",(0,.032,.34),(.52,.006,.30),lid)
        m.rotate(lid,X,lambda t:-1.81+1.80*lift(t,.07,.31,.67,.96))
    elif kind=="phone":
        box(m,"phone case","graphite",(0,.046,0),(.263,.046,.48))
        box(m,"phone glass","pewter",(0,.094,0),(.24,.010,.446))
        light=box(m,"incoming call light","story-teal",(0,.111,.085),(.176,.006,.082))
        m.scale_over(light,lambda t:.42+.58*(.5+.5*math.cos(TAU*2*t)))
    elif kind=="pen":
        m.node("pen jar","tube","graphite",(0,.225,0),(.185,.225,.185))
        pen=m.node("gold pen pivot",pos=(.045,.38,0),axis=Z,angle=.19)
        bar(m,"gold pen",(0,0,0),(0,.52,0),.031,"story-gold",pen)
        m.rotate(pen,Z,lambda t:.19+.19*math.sin(TAU*t))
    elif kind=="light-table":
        for x in (-.52,.52):
            box(m,"table legs","graphite",(x,.35,0),(.028,.35,.45))
        box(m,"tilt table body","pewter",(0,.725,0),(.68,.044,.49))
        surface=box(m,"light box","paper-white",(0,.775,0),(.61,.015,.435))
        for z in (-.16,.06,.24):
            box(m,"drawing","graphite",(0,.794,z),(.29,.004,.009))
        m.scale_over(surface,lambda t:1+.015*math.sin(TAU*2*t))
    elif kind=="archive":
        for i in range(12):
            page=m.node("page hinge",pos=(-.49+i*.09,.17+i*.038,0))
            box(m,"rejected frame","paper-white",(0,0,.28),(.33,.013,.245),page)
            box(m,"ink frame","graphite",(0,.015,.28),(.234,.002,.161),page)
            box(m,"frame interior","paper-white",(0,.019,.28),(.217,.002,.146),page)
            m.rotate(page,X,lambda t,n=i:-1.32*lift(t,.025+n*.02,.25+n*.018,.62+n*.015,.82+n*.013))
    elif kind=="lance":
        box(m,"emitter mount","pewter",(0,.16,0),(.36,.16,.61))
        barrel=m.node("barrel pitch",pos=(0,.64,0))
        m.node("emitter barrel","tube","graphite",(0,0,.31),(.19,.69,.19),X,math.pi/2,barrel)
        for x in (-.22,.22):
            box(m,"charge rails","story-red",(x,0,.32),(.036,.033,.62),barrel)
        beam=m.node("severance pulse","cone","story-red",(0,0,1.48),(.18,.48,.18),X,-math.pi/2,barrel)
        m.scale_over(beam,lambda t:.001+lift(t,.49,.52,.61,.73))
        m.rotate(barrel,X,lambda t:-.24*lift(t,.09,.37,.69,.94))
    else:
        shell=m.node("helmet yaw")
        sphere(m,"helmet shell","porcelain",(0,.65,0),(.47,.51,.43),shell)
        sphere(m,"visor glass","graphite",(0,.63,.33),(.42,.31,.17),shell)
        light=sphere(m,"visor signal","story-gold",(.125,.68,.474),(.059,.061,.020),shell)
        m.scale_over(light,lambda t:.54+.46*(.5+.5*math.cos(TAU*t)))
        m.rotate(shell,Y,lambda t:.17*math.sin(TAU*t))
    return m


def studio_cat():
    m=Prop("mira-studio-cat","Walk in Place",1.3)
    body=m.node("cat body")
    sphere(m,"torso","graphite",(0,.29,0),(.126,.145,.29),body)
    sphere(m,"head","graphite",(0,.38,.28),(.118,.113,.122),body)
    for x in (-.066,.066):
        m.node("pointed ear","cone","graphite",(x,.49,.26),(.043,.065,.041),parent=body)
        sphere(m,"eye","story-gold",(x*.72,.40,.382),(.018,.015,.009),body)
    tail=m.node("tail pivot",pos=(0,.33,-.25),parent=body)
    bar(m,"tail",(0,0,0),(0,.32,-.26),.032,"graphite",tail)
    m.rotate(tail,Y,lambda t:.42*math.sin(TAU*t))
    for side in (-1,1):
        for end in (-1,1):
            leg=m.node("hip",pos=(side*.089,.24,end*.18),parent=body)
            sphere(m,"leg","graphite",(0,-.10,0),(.038,.113,.043),leg)
            sphere(m,"paw","graphite",(0,-.207,.022),(.045,.029,.064),leg)
            m.rotate(leg,X,lambda t,s=side,e=end:s*e*.37*math.sin(TAU*t))
    return m


def dandelion():
    m=Prop("opening-dandelion","Open and Drift",7)
    head=m.node("flower crown",pos=(0,.64,0))
    bar(m,"stem",(0,0,0),(0,.64,0),.019,"leaf")
    for i in range(18):
        angle=i*TAU/18
        petal=m.node("petal hinge",axis=Y,angle=angle,parent=head)
        blade=m.node("petal bend",parent=petal)
        sphere(m,"petal","story-gold",(0,.05,.115),(.027,.023,.115),blade)
        m.rotate(blade,X,lambda t,j=i:-1.15+1.44*lift(t,.05+j*.007,.32+j*.007,.66,.96))
    sphere(m,"pollen","story-gold",(0,.064,0),(.093,.065,.093),head)
    return m


def signal_probe():
    m=Prop("vael-signal-probe","Signal Sweep",6)
    dish=m.node("scanner",pos=(0,.48,0))
    box(m,"probe bus","pewter",(0,.15,0),(.29,.15,.24))
    for x in (-.52,.52):
        box(m,"solar cells","graphite",(x,.2,0),(.25,.022,.19))
        for z in (-.12,0,.12):
            box(m,"solar cell trace","pewter",(x,.224,z),(.24,.003,.008))
    m.node("dish","cone","porcelain",scale=(.32,.105,.32),axis=X,angle=math.pi,parent=dish)
    bar(m,"feed horn",(0,.06,0),(0,.27,0),.023,"pewter",dish)
    signal=sphere(m,"Teo signal","story-gold",(0,.30,0),(.065,.065,.065),dish)
    m.rotate(dish,Z,lambda t:.55*math.sin(TAU*t))
    m.scale_over(signal,lambda t:.28+.72*(.5+.5*math.cos(TAU*3*t)))
    return m


def severance_cut():
    m=Prop("mira-severance-cut","Arm and Cut",6)
    box(m,"edit console","graphite",(0,.15,0),(.53,.15,.33))
    for x in (-.31,-.15,.01,.17):
        box(m,"edit switch","pewter",(x,.32,.12),(.06,.02,.068))
    arm=m.node("cut lever",pos=(.35,.31,-.08))
    bar(m,"lever stem",(0,0,0),(0,.31,0),.032,"pewter",arm)
    sphere(m,"lever grip","story-red",(0,.32,0),(.071,.072,.071),arm)
    indicator=box(m,"armed indicator","story-red",(-.23,.34,-.17),(.20,.016,.043))
    m.rotate(arm,X,lambda t:.87*lift(t,.10,.44,.68,.91))
    m.scale_over(indicator,lambda t:.02+.98*lift(t,.38,.46,.61,.75))
    return m


def memory_fish():
    m=Prop("mira-memory-fish","Swim in Place",2)
    root=m.node("paper body",pos=(0,.22,0))
    m.node("folded hull","taper","paper-white",scale=(.12,.32,.18),axis=X,angle=math.pi/2,parent=root)
    box(m,"frame mark","graphite",(.103,.04,0),(.009,.053,.12),root)
    tail=m.node("tail fold",pos=(0,0,-.25),parent=root)
    m.node("paper tail","cone","paper-white",(0,0,-.13),(.028,.13,.14),X,math.pi/2,tail)
    m.rotate(tail,Y,lambda t:.69*math.sin(TAU*t))
    m.rotate(root,Y,lambda t:-.19*math.sin(TAU*t))
    return m


def main():
    out=Path("rigged/story-worlds")
    out.mkdir(parents=True,exist_ok=True)
    models=[ring_city(),meridian(),vehicle("vael-transit-car"),vehicle("mira-night-shuttle",True),
            vehicle("mira-commuter-train"),studio_cat(), dandelion(),
            signal_probe(), severance_cut(), memory_fish()]
    models.extend(room(name,kind) for name,kind in (
        ("vael-apartment","apartment"),("vael-cradle-room","cradle"),("vael-clinic","clinic"),
        ("vael-mission-control","control"),("mira-open-studio","studio"),("mira-edit-bay","edit")))
    models.extend([crystal("aru-crystal-being"),crystal("lumen-glass-figure"),
                   crystal("kite-core",kite=True),crystal("story-lantern",lantern=True)])
    models.extend(desk_prop(kind) for kind in (
        "stylus","laptop","phone","pen","light-table","archive","lance","visor"))
    models.extend(character(name,build,top,tone) for name,build,top,tone in (
        ("lyra",(.185,.13,.105,.051,.79),"porcelain","skin-dark"),
        ("teo",(.199,.156,.12,.056,.84),"story-gold","skin-dark"),
        ("teo-child",(.129,.102,.088,.037,.51),"story-gold","skin-dark"),
        ("ismael",(.233,.165,.123,.064,.83),"pewter","skin"),
        ("tanaka-bell",(.204,.158,.122,.058,.78),"graphite","skin"),
        ("mira",(.16,.126,.106,.048,.75),"graphite","skin"),
        ("mira-director",(.24,.189,.134,.063,.81),"story-gold","skin"),
        ("mira-director-child",(.126,.10,.083,.036,.52),"story-gold","skin"),
        ("producer-vale",(.263,.207,.152,.075,.73),"pewter","skin-dark"),
    ))
    entries=[]
    for model in models:
        for material in model.g["materials"]:
            if material["name"].startswith("story-"):
                material["emissiveTexture"]=material["pbrMetallicRoughness"]["baseColorTexture"].copy()
                material["emissiveFactor"]=[.38,.38,.38]
        model.save(out)
        file=model.name+".glb"
        clips=[animation["name"] for animation in model.g["animations"]]
        entries.append({"file":file,"bytes":(out/file).stat().st_size,"animation":clips[0],
                        "animations":clips,"armature":bool(model.g.get("skins"))})
    (out/"manifest.json").write_text(json.dumps({"license":"LicenseRef-Ruralive-Models-1.0","models":entries},indent=2)+"\n")


if __name__=="__main__":
    main()

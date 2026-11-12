"""Build the original worksite, farm and character collection."""
import json
import math
from pathlib import Path

from build_expansion import PALETTE, TAU, X, Y, Z, bar, quaternion, skin_character
from build_motion_props import Prop, box, lift, sphere

PALETTE.update({
    "wool": (225, 215, 190), "pig": (204, 134, 129), "cow-white": (235, 224, 201),
    "feather": (219, 202, 155), "navy": (32, 57, 88), "mud": (115, 82, 61),
    "mint": (94, 160, 130), "gold": (237, 182, 50), "lime": (147, 174, 62),
})


def clip(model, name, duration):
    record = {"name": name, "samplers": [], "channels": []}
    model.g["animations"].insert(0, record)
    model.time = model.accessor([duration*i/48 for i in range(49)], "SCALAR", 5126, bounds=True)


def character(name, build, top, tone, species="human", workwear=False):
    m = Prop(name, "Walk in Place", 1.2)
    shoulder_width, waist, depth, limb, leg = build
    pelvis = m.node("pelvis", pos=(0, .17 + leg, 0))
    sphere(m, "trousers and hips", "denim", (0, .015, 0), (waist, .14, depth*.88), pelvis)
    spine = m.node("spine", pos=(0, .105, 0), parent=pelvis)
    sphere(m, "shirt", top, (0, .205, .012), (shoulder_width, .31, depth), spine)
    sphere(m, "waist", top, (0, .092, .045), (waist, .17, depth*.95), spine)
    if workwear:
        for side in (-1,1):
            box(m,"reflective vest strip","cream",(side*shoulder_width*.55,.24,depth*.87),(.025,.20,.028),spine)
    head = m.node("head", pos=(0, .48, 0), parent=spine)
    sphere(m,"head",tone,(0,.132,0),(.124,.158,.124),head)
    for side in (-1,1):
        sphere(m,"eye","dark",(side*.046,.147,.111),(.015,.018,.015),head)
    if species == "human":
        sphere(m,"nose",tone,(0,.122,.124),(.023,.03,.029),head)
        sphere(m,"hard hat" if workwear else "hair","yellow" if workwear else "dark",
               (0,.218,-.009),(.142,.077,.133),head)
        if workwear:
            m.node("helmet brim","tube","yellow",(0,.194,.026),(.158,.014,.145),parent=head)
    else:
        nose = "pig" if species == "pig" else "dark"
        sphere(m,"muzzle",tone,(0,.084,.134),(.084,.060,.079),head)
        sphere(m,"snout",nose,(0,.093,.197),(.055,.035,.026),head)
        for side in (-1,1):
            if species == "rabbit":
                m.node("long ear","ball",tone,(side*.075,.325,-.018),(.035,.139,.040),Z,-side*.17,head)
            elif species == "bear":
                sphere(m,"round ear",tone,(side*.099,.247,-.025),(.049,.053,.04),head)
            else:
                m.node("pointed ear","cone",tone,(side*.089,.247,-.022),(.049,.069,.042),Z,-side*.29,head)
        if species in ("fox","rabbit"):
            sphere(m,"chest bib","cream",(0,.268,depth*.87),(.13,.16,.045),spine)
    joints = []
    thigh = leg*.52
    shin = leg*.48
    for side,label in ((-1,"L"),(1,"R")):
        shoulder = m.node("shoulder."+label,pos=(side*(shoulder_width+.025),.32,0),parent=spine)
        sphere(m,"sleeve",top,(0,-.09,0),(limb*1.13,.151,limb*1.12),shoulder)
        elbow = m.node("elbow."+label,pos=(0,-.26,0),parent=shoulder)
        sphere(m,"forearm",tone,(0,-.105,0),(limb*.73,.127,limb*.72),elbow)
        sphere(m,"hand",tone,(0,-.227,.016),(.046,.057,.036),elbow)
        hip = m.node("hip."+label,pos=(side*waist*.61,-.025,0),parent=pelvis)
        sphere(m,"thigh","denim",(0,-thigh*.45,0),(limb*1.22,thigh*.58,limb*1.15),hip)
        knee = m.node("knee."+label,pos=(0,-thigh,0),parent=hip)
        sphere(m,"shin","denim",(0,-shin*.45,0),(limb*.91,shin*.58,limb*.86),knee)
        sphere(m,"boot","rubber",(0,-shin-.055,.042),(max(.058,limb),.061,.121),knee)
        joints.append((side,shoulder,elbow,hip,knee))

    tail = None
    if species == "fox":
        tail = m.node("tail",pos=(0,.05,-depth*.80),parent=pelvis)
        sphere(m,"bushy tail",tone,(0,-.055,-.24),(.092,.104,.28),tail)
        sphere(m,"tail tip","cream",(0,-.075,-.46),(.070,.083,.10),tail)
    elif species in ("rabbit","bear"):
        sphere(m,"tail",tone,(0,.025,-depth-.027),(.064,.065,.062),pelvis)

    actions = (
        ("Walk in Place",1.2), ("Run in Place",.72), ("Idle",3.2),
        ("Wave",2.5), ("Dance",2.4), ("Jump",1.65), ("Squat",2.4),
    )
    base_y = .17 + leg
    for name,duration in actions:
        clip(m,name,duration)
        for side,shoulder,elbow,hip,knee in joints:
            phase = 0 if side > 0 else math.pi
            if name in ("Walk in Place","Run in Place"):
                running = name == "Run in Place"
                stride = .72 if running else .43
                m.rotate(hip,X,lambda t,p=phase:stride*math.cos(TAU*t+p))
                m.rotate(knee,X,lambda t,p=phase:(.85 if running else .56)*max(0,math.sin(TAU*t+p))**1.5)
                m.rotate(shoulder,X,lambda t,p=phase:-stride*.83*math.cos(TAU*t+p))
                m.rotate(elbow,X,lambda t,p=phase:(-.74 if running else -.22)+.11*math.sin(TAU*t+p))
            elif name=="Wave" and side>0:
                m.rotate(shoulder,Z,lambda t:.15+1.86*lift(t,.02,.22,.75,.98))
                m.rotate(elbow,Z,lambda t:lift(t,.02,.22,.75,.98)*(.79+.28*math.sin(TAU*3*t)))
            elif name=="Dance":
                m.rotate(shoulder,Z,lambda t,s=side:s*(.64+.34*math.sin(TAU*2*t+s*.6)))
                m.rotate(elbow,X,lambda t,s=side:-.7+.29*math.cos(TAU*2*t+s*.6))
                m.rotate(hip,Z,lambda t,s=side:s*(.09+.10*math.sin(TAU*t+s*.6)))
                m.rotate(knee,X,lambda t,s=side:.15+.11*math.cos(TAU*2*t+s*.6))
            elif name in ("Jump","Squat"):
                crouch = lambda t: lift(t,.03,.19,.24,.36)+.55*lift(t,.62,.69,.75,.94) if name=="Jump" else lift(t,.09,.32,.61,.93)
                m.rotate(hip,X,lambda t:-.54*crouch(t))
                m.rotate(knee,X,lambda t:1.0*crouch(t))
                m.rotate(shoulder,X,lambda t:-.92*crouch(t))
            else:
                m.rotate(shoulder,X,lambda t,s=side:.045*math.sin(TAU*t+s*.8))
        if name in ("Walk in Place","Run in Place","Dance"):
            bounce=.056 if name=="Run in Place" else .026
            m.translate(pelvis,lambda t:(.042*math.sin(TAU*t) if name=="Dance" else 0,
                                        base_y+bounce*(1-math.cos(TAU*2*t)),0))
            m.rotate(spine,Y,lambda t:.13*math.sin(TAU*t))
        elif name=="Jump":
            def jump(t):
                phase=max(0,min(1,(t-.32)/.31))
                return 2.08*phase*(1-phase)
            m.translate(pelvis,lambda t:(0,base_y+jump(t)-.145*lift(t,.04,.19,.23,.34)
                                        -.09*lift(t,.59,.70,.76,.94),0))
        elif name=="Squat":
            m.translate(pelvis,lambda t:(0,base_y-.23*lift(t,.09,.32,.61,.93),-.055*lift(t,.09,.32,.61,.93)))
        else:
            m.rotate(head,Y,lambda t:.13*math.sin(TAU*t))
        if tail is not None:
            m.rotate(tail,Y,lambda t:.34*math.sin(TAU*t))
    m.g["animations"].reverse()
    del m.g["animations"][0]
    skin_character(m,pelvis)
    return m


def animal(species):
    bird = species in ("hen","duck","goose")
    color = {
        "cow":"cow-white","pig":"pig","sheep":"wool","goat":"hide",
        "hen":"feather","duck":"cow-white","goose":"bird-white",
    }[species]
    if species=="goose":
        PALETTE.setdefault("bird-white",(232,225,216))
    m=Prop("farm-"+species,"Walk in Place",1.5)
    body_y=.34 if bird else .66
    body=m.node("torso",pos=(0,body_y,0))
    length=.34 if bird else .54
    width=.23 if bird else .29
    sphere(m,"body",color,(0,0,0),(width,.24,length),body)
    head=m.node("neck and head",pos=(0,.11 if bird else .16,length*.72),parent=body)
    neck=.30 if species=="goose" else .135
    sphere(m,"neck",color,(0,neck*.46,.04),(.105,neck,.108),head)
    sphere(m,"head",color,(0,neck,.10),(.126,.122,.14),head)
    if bird:
        beak=.13 if species=="hen" else .18
        bar(m,"beak",(0,neck-.026,.15),(0,neck-.034,.15+beak),.066,"orange",head,"cone")
        if species=="hen":
            for i in range(3):
                sphere(m,"comb","red",(0,neck+.114,.038+i*.042),(.024,.066,.034),head)
    else:
        sphere(m,"muzzle","pig" if species in ("pig","cow") else "dark",
               (0,neck-.04,.22),(.109,.069,.066),head)
        for side in (-1,1):
            m.node("ear","ball",color,(side*.115,neck+.088,.057),(.053,.098,.029),Z,-side*.58,head)
            if species in ("cow","goat"):
                bar(m,"horn",(side*.085,neck+.101,.01),(side*.147,neck+.265,-.039),.042,"cream",head,"cone")
    for side in (-1,1):
        sphere(m,"eye","dark",(side*.102,neck+.029,.151),(.025,.024,.025),head)
    if species=="sheep":
        for i in range(13):
            a=i*2.399
            sphere(m,"fleece curl","wool",(.23*math.cos(a),.09+.106*math.sin(a),-.43+i*.070),(.115,.12,.106),body)
    if species=="cow":
        for x,y,z,s in ((.253,.05,.11,.11),(-.251,.04,-.19,.135),(.118,.199,-.23,.145)):
            sphere(m,"coat patch","dark",(x,y,z),(s,.060,s*1.22),body)
    legs=[]
    for side in (-1,1):
        for front in ((0,) if bird else (-1,1)):
            leg=m.node("leg joint",pos=(side*(.09 if bird else .18),-.15 if bird else -.125,front*.31),parent=body)
            h=.145 if bird else .43
            bar(m,"leg",(0,0,0),(0,-h,0),.023 if bird else .057,"orange" if bird else color,leg)
            sphere(m,"foot","orange" if bird else "dark",(0,-h,.041),(.052,.036,.088),leg)
            legs.append((leg,side if bird else side*front))
    tail=m.node("tail pivot",pos=(0,.03,-length*.88),parent=body)
    if species=="pig":
        m.node("curled tail","ring","pig",(0,.067,-.09),(.064,.035,.067),X,math.pi/2,tail)
    else:
        sphere(m,"tail",color,(0,.055,-.095),(.080,.056,.143),tail)
    for name,duration in (("Walk in Place",1.5),("Forage",3.8),("Idle",3.2)):
        clip(m,name,duration)
        if name=="Walk in Place":
            for leg,sign in legs:
                m.rotate(leg,X,lambda t,s=sign:s*.39*math.sin(TAU*t))
            m.translate(body,lambda t:(0,body_y+.016*(1-math.cos(TAU*2*t)),0))
            m.rotate(head,X,lambda t:.10*math.sin(TAU*2*t))
        elif name=="Forage":
            m.rotate(head,X,lambda t:.78*lift(t,.06,.24,.70,.95)+.08*math.sin(TAU*3*t)*lift(t,.17,.27,.65,.81))
        else:
            m.rotate(head,Y,lambda t:.21*math.sin(TAU*t))
        m.rotate(tail,Y,lambda t:.36*math.sin(TAU*2*t))
    m.g["animations"].reverse()
    del m.g["animations"][0]
    return m


def wheel(m,x,z,r=.32):
    axle=m.node("wheel axle",pos=(x,r,z))
    m.node("tire","tube","rubber",scale=(r,.13,r),axis=Z,angle=math.pi/2,parent=axle)
    m.node("rim","tube","steel",scale=(r*.64,.136,r*.64),axis=Z,angle=math.pi/2,parent=axle)
    for i in range(5):
        a=TAU*i/5
        sphere(m,"lug","ink",(math.copysign(.145,x),r*.36*math.cos(a),r*.36*math.sin(a)),
               (.014,.027,.027),axle)
    return axle


def wheeled_machine(kind):
    labels={
        "farm-tractor":"Drive in Place","construction-dump-truck":"Tip and Return",
        "construction-forklift":"Lift and Lower","construction-road-roller":"Roll in Place",
        "construction-bulldozer":"Raise and Lower Blade","construction-wheel-loader":"Scoop and Dump",
    }
    m=Prop(kind,labels[kind],6)
    x=.56 if kind!="construction-dump-truck" else .68
    for z in (-.79,.79):
        for side in (-1,1):
            if z>0 and kind=="construction-road-roller":
                continue
            axle=wheel(m,side*x,z,.42 if kind=="farm-tractor" and z<0 else .31)
            if kind in ("farm-tractor","construction-road-roller"):
                m.rotate(axle,X,lambda t:TAU*t)
    paint="red" if kind=="farm-tractor" else "yellow"
    box(m,"chassis",paint,(0,.43,0),(.54,.16,1.13))
    rear_cab=kind in ("construction-wheel-loader","construction-road-roller","construction-bulldozer")
    cab_z=-.42 if rear_cab else .52
    box(m,"cab body",paint,(0,.70,cab_z),(.47,.24,.33))
    box(m,"cab windows","glass",(0,1.00,cab_z),(.37,.25,.30))
    box(m,"cab roof",paint,(0,1.275,cab_z),(.43,.036,.36))
    for side in (-1,1):
        for z in (-1.135,1.135):
            box(m,"lamp","red" if z<0 else "cream",(side*.31,.57,z),(.09,.060,.025))
    if kind=="farm-tractor":
        box(m,"hood","red",(0,.72,-.30),(.30,.21,.52))
        bar(m,"exhaust",(.24,.80,-.50),(.24,1.37,-.50),.029,"ink")
    elif kind=="construction-dump-truck":
        pivot=m.node("bed hinge",pos=(0,.61,-1.05))
        box(m,"bed floor","steel",(0,.07,.48),(.61,.052,.52),pivot)
        for side in (-1,1):
            box(m,"bed wall","yellow",(side*.61,.30,.49),(.062,.23,.52),pivot)
        box(m,"bulkhead","yellow",(0,.30,1.02),(.62,.23,.045),pivot)
        gate=m.node("tailgate hinge",pos=(0,.47,-.034),parent=pivot)
        box(m,"tailgate","steel",(0,-.21,0),(.58,.22,.035),gate)
        m.rotate(pivot,X,lambda t:-.92*lift(t,.09,.38,.60,.94))
        m.rotate(gate,X,lambda t:.71*lift(t,.24,.42,.59,.76))
    elif kind=="construction-forklift":
        for side in (-1,1):
            bar(m,"mast rail",(side*.29,.17,1.04),(side*.29,1.89,1.04),.042,"steel")
        carrier=m.node("sliding carriage",pos=(0,.30,1.08))
        box(m,"backrest","ink",(0,.22,0),(.29,.22,.043),carrier)
        for side in (-1,1):
            box(m,"fork tine","steel",(side*.19,-.058,.31),(.049,.029,.35),carrier)
        m.translate(carrier,lambda t:(0,.30+1.18*lift(t,.06,.41,.62,.95),1.08))
    elif kind=="construction-road-roller":
        drum=m.node("roller drum",pos=(0,.38,.82))
        m.node("steel roller","tube","steel",scale=(.37,.56,.37),axis=Z,angle=math.pi/2,parent=drum)
        for side in (-1,1):
            box(m,"drum marking","orange",(side*.566,.16,0),(.01,.08,.028),drum)
        m.rotate(drum,X,lambda t:TAU*t)
    else:
        pivot=m.node("lift linkage",pos=(0,.69,.26))
        for side in (-1,1):
            bar(m,"lift arm",(side*.40,0,0),(side*.40,-.20,1.00),.057,"yellow",pivot,shape="box")
        tool=m.node("blade pivot" if kind.endswith("bulldozer") else "bucket pivot",
                    pos=(0,-.20,1.00),parent=pivot)
        box(m,"steel tool","steel",(0,-.12,.15),(.62,.18,.12),tool)
        box(m,"cutting edge","chrome",(0,-.29,.27),(.64,.035,.11),tool)
        m.rotate(pivot,X,lambda t:-.84*lift(t,.14,.40,.60,.92))
        m.rotate(tool,X,lambda t:.65*lift(t,.30,.48,.61,.84))
        if kind.endswith("bulldozer"):
            for side in (-1,1):
                box(m,"crawler track cover","rubber",(side*.56,.27,0),(.19,.24,1.07))
                for i in range(12):
                    box(m,"steel grouser","steel",(side*.56,.49,-.98+i*.178),(.17,.027,.049))
    return m


def crane():
    m=Prop("construction-tower-crane","Slew, Lower Hook and Return",12)
    box(m,"concrete pad","stone",(0,.08,0),(.63,.08,.63))
    for x in (-.14,.14):
        for z in (-.14,.14):
            bar(m,"tower column",(x,.16,z),(x,2.52,z),.026,"yellow",shape="box")
    for i in range(7):
        y=.17+i*.332
        for x in (-.14,.14):
            bar(m,"tower brace",(x,y,-.14),(x,y+.32,.14),.018,"yellow")
        for z in (-.14,.14):
            bar(m,"tower brace",(-.14,y,z),(.14,y+.32,z),.018,"yellow")
    top=m.node("slewing ring",pos=(0,2.47,0))
    box(m,"counterweight","stone",(-.66,.17,0),(.24,.18,.19),top)
    box(m,"operator cab","glass",(.18,.04,.20),(.13,.14,.115),top)
    for z in (-.10,.10):
        box(m,"jib rail","yellow",(.65,.19,z),(1.51,.045,.023),top)
    for i in range(9):
        x=-.74+i*.33
        bar(m,"diagonal jib support",(x,.14,-.1),(x+.22,.42,.1),.017,"yellow",top)
    trolley=m.node("travelling trolley",pos=(1.40,.10,0),parent=top)
    box(m,"trolley","steel",(0,0,0),(.098,.071,.14),trolley)
    cable=bar(m,"hoist cable",(0,0,0),(0,-.42,0),.013,"ink",trolley)
    hook=m.node("hook assembly",pos=(0,-.42,0),parent=trolley)
    m.node("hook","ring","steel",(0,-.055,0),(.061,.038,.061),X,math.pi/2,hook)
    length=lambda t:.42+1.34*lift(t,.21,.46,.65,.88)
    m.translate(trolley,lambda t:(1.40+.50*lift(t,.05,.26,.69,.92),.10,0))
    m.translate(hook,lambda t:(0,-length(t),0))
    m.translate(cable,lambda t:(0,-length(t)/2,0))
    m.track(cable,"scale",[(.013,length(i/48)/2,.013) for i in range(49)])
    m.rotate(top,Y,lambda t:.94*lift(t,.03,.23,.76,.98))
    return m


def container(name,treasure=False,metal=False):
    m=Prop(name,"Open, Hold and Close",5)
    wood="teal" if metal else "walnut"
    w=.66 if treasure else .54
    box(m,"bottom",wood,(0,.05,0),(w,.05,.39))
    for z in (-.39,.39):
        for i in range(3):
            box(m,"side board",wood,(0,.14+i*.116,z),(w,.054,.036))
    for x in (-w,w):
        for i in range(3):
            box(m,"end board",wood,(x,.14+i*.116,0),(.035,.054,.39))
    for x in (-w+.074,w-.074):
        for z in (-.428,.428):
            box(m,"corner strap","brass" if treasure else "steel",(x,.235,z),(.043,.23,.013))
    hinge=m.node("rear lid hinge",pos=(0,.437,-.39))
    box(m,"lid",wood,(0,.038,.39),(w+.033,.046,.41),hinge)
    for x in (-w*.72,w*.72):
        box(m,"lid strap","brass" if treasure else "steel",(x,.09,.39),(.043,.015,.414),hinge)
    if treasure:
        for i in range(18):
            x=(i%6-2.5)*.159
            z=(i//6-1)*.20
            m.node("coin pile","tube","gold",(x,.108+.012*(i%4),z),(.063,.028+.012*(i%4),.063))
        box(m,"latch plate","brass",(0,.388,.439),(.087,.073,.028))
        sphere(m,"lock","ink",(0,.382,.465),(.029,.039,.013))
    m.rotate(hinge,X,lambda t:-1.80*lift(t,.04,.31,.68,.96))
    return m


def farm_scene():
    m=Prop("farmyard-barn","Farmyard Gate",8)
    box(m,"yard","island-green",(0,-.04,0),(2.41,.04,1.74))
    box(m,"rear wall","red",(-.66,.78,-1.49),(1.03,.76,.042))
    for side in (-1,1):
        box(m,"side wall","red",(-.66+side*1.00,.78,-.69),(.05,.76,.84))
        box(m,"front wall beside door","red",(-.66+side*.80,.78,.15),(.228,.76,.045))
    box(m,"door header","red",(-.66,1.29,.15),(.59,.25,.046))
    box(m,"barn floor","wood",(-.66,.025,-.69),(1.03,.022,.84))
    for side in (-1,1):
        m.node("barn roof","box","ink",(-.66+side*.55,1.69,-.69),(.66,.062,.95),
               axis=Z,angle=-side*.37)
    for side in (-1,1):
        door=m.node("barn door",pos=(-.66+side*.57,.52,.16))
        box(m,"door face","cream",(-side*.27,0,0),(.27,.47,.042),door)
        bar(m,"door brace",(-side*.50,-.41,.048),(-side*.045,.41,.048),.026,"wood",door,shape="box")
        m.rotate(door,Y,lambda t,s=side:-s*1.45*lift(t,.10,.34,.62,.91))
    for z in (-.38,.18,.74,1.30):
        box(m,"fence post","wood",(1.86,.28,z),(.046,.28,.046))
    for y in (.20,.43):
        bar(m,"fence rail",(1.86,y,-.4),(1.86,y,1.32),.032,"wood",shape="box")
    for i in range(4):
        m.node("hay bale","tube","sand",(1.34,.18,-1.27+i*.32),(.14,.14,.14),axis=X,angle=math.pi/2)
    return m


def main():
    PALETTE.setdefault("island-green",(77,122,63))
    out=Path("rigged/farm-and-worksite")
    out.mkdir(parents=True,exist_ok=True)
    models = [
        wheeled_machine(name) for name in ("farm-tractor","construction-dump-truck",
            "construction-forklift","construction-road-roller","construction-bulldozer",
            "construction-wheel-loader")
    ]
    models.extend([crane(),container("wooden-crate"),container("metal-equipment-crate",metal=True),
                   container("treasure-chest",treasure=True),farm_scene()])
    models.extend(animal(species) for species in ("cow","pig","sheep","goat","hen","duck","goose"))
    models.extend(character(name,build,top,tone,species,workwear) for name,build,top,tone,species,workwear in (
        ("tall-slim-person",(.130,.105,.084,.038,.96),"mint","skin","human",False),
        ("plus-size-person",(.305,.312,.265,.097,.75),"purple","skin-dark","human",False),
        ("short-stocky-person",(.271,.206,.158,.079,.60),"orange","skin","human",False),
        ("tall-athletic-person",(.302,.170,.145,.076,.86),"blue","skin-dark","human",False),
        ("slim-construction-worker",(.144,.114,.092,.043,.83),"orange","skin-dark","human",True),
        ("plus-size-construction-worker",(.304,.316,.272,.104,.73),"lime","skin","human",True),
        ("humanoid-fox",(.186,.138,.116,.052,.79),"teal","orange","fox",False),
        ("humanoid-rabbit",(.151,.108,.091,.045,.86),"purple","wool","rabbit",False),
        ("humanoid-bear",(.329,.300,.236,.097,.68),"red","brown","bear",False),
        ("humanoid-pig",(.258,.252,.224,.081,.72),"navy","pig","pig",False),
    ))
    entries=[]
    for model in models:
        model.save(out)
        file=model.name+".glb"
        clips=[animation["name"] for animation in model.g["animations"]]
        entries.append({"file":file,"bytes":(out/file).stat().st_size,"animation":clips[0],
                        "animations":clips,"armature":bool(model.g.get("skins"))})
    (out/"manifest.json").write_text(json.dumps(
        {"license":"LicenseRef-Ruralive-Models-1.0","models":entries},indent=2)+"\n")


if __name__=="__main__":
    main()

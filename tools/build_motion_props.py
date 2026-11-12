"""Original props with articulated, closed animation cycles."""
import json
import math
from pathlib import Path

from build_expansion import Model, PALETTE, SHAPES, TAU, X, Y, Z, bar, grid, quaternion

PALETTE.update({
    "brass": (177, 132, 56), "ivory": (242, 232, 204), "teal": (49, 112, 109),
    "walnut": (95, 58, 41), "wood": (145, 99, 58), "ink": (35, 37, 52), "signal": (243, 157, 43),
})


class Prop(Model):
    def __init__(self, name, clip, seconds):
        super().__init__(name, clip)
        self.time = self.accessor([seconds*i/48 for i in range(49)], "SCALAR", 5126, bounds=True)

    def rotate(self, node, axis, curve):
        self.track(node, "rotation", [quaternion(axis, curve(i/48)) for i in range(49)])

    def translate(self, node, curve):
        self.track(node, "translation", [curve(i/48) for i in range(49)])

    def scale_over(self, node, curve):
        base = self.g["nodes"][node].get("scale", (1, 1, 1))
        self.track(node, "scale", [tuple(s*curve(i/48) for s in base) for i in range(49)])


def smooth(a, b, t):
    x = max(0, min(1, (t-a)/(b-a)))
    return x*x*(3-2*x)


def lift(t, start=.08, top=.32, release=.59, stop=.86):
    return smooth(start, top, t)-smooth(release, stop, t)


def box(m, name, color, pos, dimensions, parent=0):
    return m.node(name, "box", color, pos, dimensions, parent=parent)


def sphere(m, name, color, pos, dimensions, parent=0):
    return m.node(name, "ball", color, pos, dimensions, parent=parent)


def windmill():
    m = Prop("stone-windmill", "Sails Turning", 7)
    m.node("tapered tower","taper","stone",(0,1.15,0),(.69,1.15,.69))
    m.node("cap","cone","red",(0,2.52,0),(.47,.29,.47))
    box(m,"door","walnut",(0,.37,.66),(.145,.31,.045))
    hub=m.node("sail axle",pos=(0,1.93,.60))
    sphere(m,"axle cap","brass",(0,0,0),(.14,.14,.12),hub)
    for i in range(4):
        blade=m.node("sail",axis=Z,angle=i*TAU/4,parent=hub)
        box(m,"spar","walnut",(0,.77,0),(.046,.77,.039),blade)
        for j in range(6):
            box(m,"sail cloth panel","ivory",(.14,.51+j*.15,.01),(.14,.068,.015),blade)
        box(m,"outer rail","walnut",(.29,.90,0),(.018,.43,.024),blade)
    m.rotate(hub,Z,lambda t:TAU*t)
    return m


def lighthouse():
    m=Prop("coastal-lighthouse","Beacon Sweep",8)
    m.node("rock base","ball","stone",(0,.03,0),(1.1,.24,.82))
    for i in range(6):
        r=.49-i*.037
        m.node("tower course","tube","ivory" if i%2==0 else "red",(0,.32+i*.32,0),(r,.16,r))
    m.node("balcony","tube","ink",(0,2.14,0),(.48,.05,.48))
    for i in range(12):
        a=i*TAU/12
        bar(m,"balcony rail",(.45*math.cos(a),2.15,.45*math.sin(a)),
            (.45*math.cos(a),2.34,.45*math.sin(a)),.018,"steel")
    m.node("roof","cone","red",(0,2.79,0),(.43,.22,.43))
    lantern=m.node("rotating lantern",pos=(0,2.45,0))
    sphere(m,"lamp","sun",(0,0,0),(.17,.15,.17),lantern)
    m.node("beam","cone","sun",(0,0,.98),(.21,.96,.17),X,-math.pi/2,lantern)
    m.rotate(lantern,Y,lambda t:TAU*t)
    return m


def drawbridge():
    m=Prop("canal-drawbridge","Open, Hold and Close",9)
    box(m,"water","water",(0,-.08,0),(2.8,.08,1.02))
    for sign in (-1,1):
        box(m,"stone quay","stone",(sign*1.83,.11,0),(.61,.25,.88))
        deck=m.node("lifting deck",pos=(sign*1.28,.39,0))
        box(m,"wood deck","walnut",(-sign*.62,0,0),(.62,.055,.57),deck)
        for z in (-.52,.52):
            for i in range(4):
                x=-sign*(.1+i*.32)
                box(m,"handrail post","steel",(x,.17,z),(.022,.17,.022),deck)
            box(m,"handrail","steel",(-sign*.58,.34,z),(.58,.019,.024),deck)
        m.rotate(deck,Z,lambda t, side=sign:-side*1.04*lift(t))
    return m


def excavator():
    m=Prop("tracked-excavator","Dig and Dump",8)
    for z in (-.48,.48):
        box(m,"crawler track","rubber",(0,.23,z),(.91,.20,.18))
        for i in range(9):
            x=-.76+i*.19
            box(m,"track cleat","steel",(x,.45,z),(.045,.025,.17))
            m.node("track roller","tube","steel",(x,.22,z),(.13,.184,.13),X,math.pi/2)
    turret=m.node("slewing upper carriage",pos=(0,.51,0))
    box(m,"counterweight","yellow",(-.42,.21,0),(.48,.22,.49),turret)
    box(m,"cab","glass",(-.37,.59,.25),(.28,.35,.25),turret)
    box(m,"cab roof","yellow",(-.37,.96,.25),(.31,.045,.28),turret)
    boom=m.node("boom pivot",pos=(.14,.38,-.16),axis=Z,angle=.28,parent=turret)
    bar(m,"boom",(0,0,0),(1.02,.08,0),.092,"yellow",boom,shape="box")
    stick=m.node("stick pivot",pos=(1.02,.08,0),axis=Z,angle=-1.09,parent=boom)
    bar(m,"stick",(0,0,0),(.72,0,0),.070,"yellow",stick,shape="box")
    bucket=m.node("bucket hinge",pos=(.72,0,0),parent=stick)
    box(m,"bucket shell","steel",(.13,-.1,0),(.17,.12,.24),bucket)
    for z in (-.17,-.06,.06,.17):
        box(m,"bucket tooth","chrome",(.29,-.14,z),(.075,.032,.022),bucket)
    m.rotate(turret,Y,lambda t:1.04*lift(t,.33,.53,.74,.94))
    m.rotate(boom,Z,lambda t:.28+.47*lift(t,.22,.39,.76,.98)-.25*lift(t,.02,.13,.22,.35))
    m.rotate(stick,Z,lambda t:-1.09+.38*lift(t,.19,.35,.67,.96))
    m.rotate(bucket,Z,lambda t:.72*lift(t,.13,.29,.57,.69)-.45*lift(t,.60,.69,.79,.96))
    return m


def locomotive():
    m=Prop("steam-locomotive","Driving Rods",4)
    box(m,"chassis","red",(0,.46,0),(.69,.14,1.58))
    m.node("boiler","tube","ink",(0,.92,.21),(.43,1.06,.43),X,math.pi/2)
    m.node("smokebox door","tube","steel",(0,.92,1.29),(.39,.051,.39),X,math.pi/2)
    box(m,"engine cab","teal",(0,1.09,-.95),(.58,.55,.50))
    box(m,"roof","ink",(0,1.68,-.95),(.64,.07,.54))
    for x in (-.59,.59):
        box(m,"cab window","glass",(x,1.34,-.97),(.02,.22,.29))
    m.node("chimney","taper","ink",(0,1.58,.80),(.16,.34,.16))
    sphere(m,"headlamp","sun",(0,1.19,1.35),(.13,.13,.07))
    for side in (-1,1):
        x=side*.72
        for z in (-.95,0,.95):
            axle=m.node("coupled wheel",pos=(x,.39,z))
            m.node("wheel tire","tube","rubber",scale=(.37,.09,.37),axis=Z,angle=math.pi/2,parent=axle)
            m.node("wheel disc","tube","red",scale=(.29,.097,.29),axis=Z,angle=math.pi/2,parent=axle)
            sphere(m,"crank pin","brass",(side*.11,.15,0),(.048,.048,.048),axle)
            m.rotate(axle,X,lambda t:TAU*2*t)
        rod=box(m,"coupling rod","chrome",(x+side*.12,.54,0),(.036,.036,1.03))
        m.translate(rod,lambda t, px=x+side*.12:(px,.39+.15*math.cos(TAU*2*t),.15*math.sin(TAU*2*t)))
    return m


def robot_arm():
    m=Prop("assembly-robot","Reach, Grip and Return",7)
    m.node("base plate","tube","steel",(0,.13,0),(.50,.13,.50))
    turret=m.node("turntable",pos=(0,.26,0))
    box(m,"shoulder housing","orange",(0,.24,0),(.25,.24,.25),turret)
    shoulder=m.node("shoulder hinge",pos=(0,.43,0),axis=Z,angle=-.45,parent=turret)
    bar(m,"upper arm",(0,0,0),(0,.84,0),.113,"orange",shoulder)
    elbow=m.node("elbow hinge",pos=(0,.84,0),axis=Z,angle=-1.22,parent=shoulder)
    bar(m,"forearm",(0,0,0),(0,.72,0),.085,"yellow",elbow)
    wrist=m.node("wrist",pos=(0,.72,0),parent=elbow)
    box(m,"gripper body","steel",(0,.06,0),(.13,.09,.13),wrist)
    for side in (-1,1):
        finger=m.node("finger hinge",pos=(side*.093,.10,0),parent=wrist)
        box(m,"finger","chrome",(0,.13,0),(.032,.133,.051),finger)
        box(m,"finger tip","rubber",(-side*.04,.24,0),(.06,.024,.048),finger)
        m.rotate(finger,Z,lambda t,s=side:-s*.35*(1-lift(t,.21,.32,.72,.83)))
    m.rotate(turret,Y,lambda t:1.16*lift(t,.34,.57,.78,.97))
    m.rotate(shoulder,Z,lambda t:-.45-.31*lift(t,.09,.25,.33,.44)-.26*lift(t,.59,.68,.76,.91))
    m.rotate(elbow,Z,lambda t:-1.22+.41*lift(t,.14,.26,.34,.50)+.37*lift(t,.59,.69,.76,.93))
    return m


def rowboat():
    m=Prop("wooden-rowboat","Power and Recovery Stroke",4)
    hull=m.node("boat roll",pos=(0,.23,0))
    def shell(u, v):
        angle = TAU*u
        radius = .07+.93*v
        return (.59*radius*math.cos(angle), -.19+.40*v*v, 1.33*radius*math.sin(angle)), Y

    SHAPES["rowboat-shell"] = grid(24, 9, shell)
    m.node("open wooden hull","rowboat-shell","wood",parent=hull)
    m.node("gunwale","ring","walnut",(0,.21,0),(.55,.071,1.23),parent=hull)
    box(m,"keel","walnut",(0,-.177,0),(.063,.04,.64),hull)
    for z in (-.48,.40):
        box(m,"bench","ivory",(0,.25,z),(.47,.034,.11),hull)
    for side in (-1,1):
        yaw=m.node("oarlock yaw",pos=(side*.51,.29,.13),parent=hull)
        pitch=m.node("oar pitch",parent=yaw)
        bar(m,"oar shaft",(-side*.36,0,0),(side*.94,0,0),.025,"walnut",pitch)
        sphere(m,"oar blade","wood",(side*.99,0,0),(.24,.025,.107),pitch)
        m.rotate(yaw,Y,lambda t,s=side:s*.64*math.sin(TAU*t))
        m.rotate(pitch,Z,lambda t,s=side:s*(-.14+.16*math.cos(TAU*t)))
    m.rotate(hull,Z,lambda t:.032*math.sin(TAU*t))
    m.translate(hull,lambda t:(0,.23+.025*math.sin(TAU*t+.5),0))
    return m


def telescope():
    m=Prop("observatory-telescope","Scan the Sky",8)
    for i in range(3):
        a=i*TAU/3
        bar(m,"tripod leg",(.68*math.cos(a),.03,.68*math.sin(a)),(0,1.01,0),.055,"walnut")
    mount=m.node("azimuth mount",pos=(0,1.03,0))
    m.node("mount","tube","brass",scale=(.20,.13,.20),parent=mount)
    tilt=m.node("elevation hinge",pos=(0,.19,0),parent=mount)
    m.node("optical tube","tube","ivory",(0,0,0),(.17,.71,.17),X,math.pi/2,tilt)
    m.node("lens ring","tube","brass",(0,0,.72),(.209,.055,.209),X,math.pi/2,tilt)
    m.node("objective lens","tube","glass",(0,0,.78),(.174,.012,.174),X,math.pi/2,tilt)
    m.node("eyepiece","tube","ink",(0,0,-.78),(.075,.11,.075),X,math.pi/2,tilt)
    m.rotate(mount,Y,lambda t:1.10*lift(t,.04,.35,.55,.94))
    m.rotate(tilt,X,lambda t:-.25-.29*lift(t,.17,.47,.60,.91))
    return m


def gramophone():
    m=Prop("brass-gramophone","Record and Tonearm",6)
    box(m,"cabinet","walnut",(0,.20,0),(.65,.19,.54))
    platter=m.node("turntable",pos=(0,.415,0))
    m.node("record","tube","ink",scale=(.47,.023,.47),parent=platter)
    for r in (.33,.38,.43):
        m.node("groove","ring","rubber",(0,.026,0),(r,.012,r),parent=platter)
    m.node("record label","tube","red",(0,.029,0),(.15,.005,.15),parent=platter)
    box(m,"record label detail","ivory",(.055,.038,.03),(.051,.004,.012),platter)
    arm=m.node("tonearm pivot",pos=(.49,.50,-.37),axis=Y,angle=.04)
    bar(m,"tonearm",(0,0,0),(-.44,0,.32),.026,"brass",arm)
    box(m,"stylus","steel",(-.44,-.03,.32),(.055,.028,.033),arm)
    bar(m,"horn pipe",(.54,.44,-.34),(.54,.96,-.34),.052,"brass")
    m.node("horn","cone","brass",(.42,1.23,-.15),(.30,.37,.30),X,math.pi/2)
    m.node("horn lip","ring","brass",(.42,1.23,.22),(.28,.054,.28),X,math.pi/2)
    m.node("horn opening","ball","walnut",(.42,1.23,.216),(.245,.245,.026))
    m.rotate(platter,Y,lambda t:TAU*3*t)
    m.rotate(arm,Y,lambda t:.04+.067*lift(t,.10,.44,.64,.93))
    return m


def clock():
    m=Prop("pendulum-clock","Clockwork",6)
    box(m,"case","walnut",(0,.93,0),(.46,.92,.19))
    box(m,"pendulum cavity","ink",(0,.58,.20),(.35,.46,.017))
    m.node("dial","tube","ivory",(0,1.43,.23),(.375,.028,.375),X,math.pi/2)
    for i in range(12):
        a=i*TAU/12
        m.node("dial tick","box","ink",(.307*math.sin(a),1.43+.307*math.cos(a),.26),
               (.012,.031 if i%3==0 else .020,.008),Z,-a)
    for name,length,turns in (("minute",.265,1),("second",.292,2)):
        hand=m.node(name+" axle",pos=(0,1.43,.30 if turns==1 else .326))
        box(m,name+" hand","red" if turns==2 else "ink",(0,length*.5,0),(.014,length*.5,.01),hand)
        m.rotate(hand,Z,lambda t,n=turns:-TAU*n*t)
    pendulum=m.node("pendulum hinge",pos=(0,.96,.26))
    bar(m,"pendulum rod",(0,0,0),(0,-.51,0),.018,"brass",pendulum)
    m.node("pendulum bob","tube","brass",(0,-.51,0),(.12,.021,.12),X,math.pi/2,pendulum)
    m.rotate(pendulum,Z,lambda t:.22*math.sin(TAU*3*t))
    return m


def umbrella():
    m=Prop("opening-umbrella","Open, Hold and Fold",6)
    bar(m,"shaft",(0,.26,0),(0,1.54,0),.029,"steel")
    m.node("curved handle","ring","walnut",(0,.27,0),(.14,.08,.14),X,math.pi/2)
    for i in range(8):
        angle=i*TAU/8
        azimuth=m.node("rib azimuth",pos=(0,1.46,0),axis=Y,angle=angle)
        rib=m.node("rib hinge",axis=Z,angle=-1.14,parent=azimuth)
        bar(m,"rib",(0,0,0),(.73,-.14,0),.016,"steel",rib)
        sphere(m,"canopy panel","teal" if i%2 else "blue",(.39,-.078,0),(.42,.027,.25),rib)
        m.rotate(rib,Z,lambda t:-1.14+1.04*lift(t,.06,.33,.67,.95))
    return m


def carousel():
    m=Prop("fairground-carousel","Roundabout",12)
    m.node("plinth","tube","teal",(0,.13,0),(1.52,.13,1.52))
    rotor=m.node("turntable",pos=(0,.27,0))
    m.node("deck","tube","red",scale=(1.43,.072,1.43),parent=rotor)
    bar(m,"centre pole",(0,0,0),(0,2.12,0),.092,"brass",rotor)
    m.node("canopy","cone","red",(0,2.02,0),(1.54,.44,1.54),parent=rotor)
    for i in range(8):
        a=i*TAU/8
        x,z=1.10*math.cos(a),1.10*math.sin(a)
        bar(m,"riding pole",(x,.12,z),(x,1.73,z),.028,"brass",rotor)
        horse=m.node("rising horse",pos=(x,.70,z),axis=Y,angle=-a,parent=rotor)
        sphere(m,"horse body","ivory",(0,0,0),(.125,.145,.23),horse)
        sphere(m,"horse head","ivory",(0,.19,.16),(.09,.125,.12),horse)
        box(m,"saddle","purple",(0,.11,-.02),(.14,.042,.10),horse)
        for side in (-1,1):
            for front in (-1,1):
                bar(m,"leg",(side*.075,-.04,front*.12),
                    (side*.09,-.21,front*.21),.035,"ivory",horse)
        m.translate(horse,lambda t,px=x,pz=z,phase=a:(px,.70+.20*math.sin(TAU*3*t+phase),pz))
    m.rotate(rotor,Y,lambda t:TAU*t)
    return m


def main():
    out=Path("rigged/motion-props")
    out.mkdir(parents=True,exist_ok=True)
    props=[windmill,lighthouse,drawbridge,excavator,locomotive,robot_arm,
           rowboat,telescope,gramophone,clock,umbrella,carousel]
    entries=[]
    for build in props:
        model=build()
        model.save(out)
        file=model.name+".glb"
        entries.append({"file":file,"bytes":(out/file).stat().st_size,
                        "animation":model.g["animations"][0]["name"]})
    (out/"manifest.json").write_text(json.dumps(
        {"license":"LicenseRef-Ruralive-Models-1.0","models":entries},indent=2)+"\n")


if __name__=="__main__":
    main()

import ezdxf


AAMA_CUT = "1"
AAMA_DRAW = "8"
AAMA_INTCUT = "11"

def filterlayerelements(d, layernames):
    return [ e  for e in d.entities  if (e.dxf.layer in layernames) and (e.dxftype() not in ["MTEXT", "INSERT"]) ]

def linearizeelement(e):
    if e.dxftype() == "LINE":
        return [e.dxf.start, e.dxf.end]
    elif e.dxftype() == "POLYLINE":
        return [ p.dxf.location  for p in e.vertices ]
    elif e.dxftype() == "ARC":
        segments = 15
        endangle = e.dxf.end_angle
        if 0 < endangle + 360 - e.dxf.start_angle < 180:
            endangle += 360
        angs = [ e.dxf.start_angle*(1-i/segments) + endangle*(i/segments)  for i in range(segments+1) ]
        return [ e.dxf.center + ezdxf.math.vector.Vector.from_deg_angle(a, e.dxf.radius)  for a in angs]
    elif e.dxftype() == "CIRCLE":
        segments = 20
        angs = [ 360.0*i/segments  for i in range(segments+1) ]
        return [ e.dxf.center + ezdxf.math.vector.Vector.from_deg_angle(a, e.dxf.radius)  for a in angs]
    elif e.dxftype() == "SPLINE":
        knots = [ k-e.knots[0]  for k in e.knots ]
        s = ezdxf.math.BSpline(e.control_points, e.dxfattribs()["degree"]+1, knots, e.weights or None)
        return list(s.approximate(20))
    else:
        print("Unknown type ", e.dxftype())


class MergeEdge:
    def __init__(self, e, pts, bfore, mvfar):
        self.e = e
        self.pts = pts
        self.bfore = bfore
        self.mvfar = mvfar
        v = (self.pts[1] - self.pts[0]) if self.bfore else (self.pts[-2] - self.pts[-1])
        self.angout = (v.angle_deg + 360)%360

    def umvfar(self):
        while self.mvfar.successormv is not None:
            self.mvfar = self.mvfar.successormv
        return self.mvfar
    
        
class MergeVert:
    def __init__(self, pt, prevmv):
        self.pt = pt
        self.mergeedges = [ ] 
        self.successormv = None
        if prevmv is not None:
            assert prevmv.successormv is None
            prevmv.successormv = self
            
    def mergein(self, mv):
        assert self.successormv is None
        assert mv.successormv is None
        assert len(self.mergeedges) != 0 and len(mv.mergeedges) != 0
        spt = self.pt*len(self.mergeedges) + mv.pt*len(mv.mergeedges)
        self.mergeedges.extend(mv.mergeedges)
        mv.successormv = self
        mv.pt = spt/len(self.mergeedges)
        mv.mergeedges.clear()
        
def MergeVertBiway(e):
    pts = linearizeelement(e)
    mv0 = MergeVert(pts[0], None)
    mv1 = MergeVert(pts[-1], None)
    mv0.mergeedges.append(MergeEdge(e, pts, True, mv1))
    mv1.mergeedges.append(MergeEdge(e, pts, False, mv0))
    return [mv0, mv1]

def ultimatesuccessor(mv):
    while mv.successormv is not None:
        mv = mv.successormv
    return mv

def makemergevertset(cutelements, dmax):
    mergeverts = [ ]
    for e in cutelements:
            mergeverts.extend(MergeVertBiway(e))
    mergeverts.sort(key=lambda X: X.pt.x)

    mvdists = [ ]
    dmaxs = [ ]
    for i in range(len(mergeverts)):
        for j in range(i+1, len(mergeverts)):
            v = mergeverts[j].pt - mergeverts[i].pt
            if v.x > dmax:
                break
            if v.magnitude < dmax:
                mvdists.append((v.magnitude, mergeverts[i], mergeverts[j]))
                dmaxs.append(v.magnitude)
    mvdists.sort(key=lambda X:X[0])
    if max(dmaxs) > 0.01:
        print("dmaxs-tail: ", sorted(dmaxs)[-3:])
    
    smergeverts = set(mergeverts)
    for i in range(len(mvdists)):
        mv0 = ultimatesuccessor(mvdists[i][1])
        mv1 = ultimatesuccessor(mvdists[i][2])
        if mv0 != mv1:
            if mv1 in [ me.mvfar  for me in mv0.mergeedges ]:
                print("suppressing loop making merge")
            else:
                mv0.mergein(mv1)
                smergeverts.remove(mv1)
        else:
            pass # print("already merged ", mv0.pt)

    #print("vertdegs:", [len(mv.mergeedges)  for mv in smergeverts])
    for mv in smergeverts:
        mv.mergeedges.sort(key=lambda X: X.angout)
        
    return smergeverts


def findcutelementsouter(cutelements, dmax):
    smergeverts = makemergevertset(cutelements, 0.999)

    mvTL = min(smergeverts, key=lambda X: X.pt.x-X.pt.y)
    meTL = max(mvTL.mergeedges, key=lambda X: (X.angout+360-135)%360)

    cutelementsouter = [ meTL.e ]
    cutelementsouterdir = [ meTL.bfore ]
    me = meTL
    mv = me.umvfar()
    while mv != mvTL:
        iin = [ me.e  for me in mv.mergeedges ].index(me.e)
        iout = (iin + len(mv.mergeedges) - 1) % len(mv.mergeedges)
        me = mv.mergeedges[iout]
        cutelementsouter.append(me.e)
        cutelementsouterdir.append(me.bfore)
        mv = me.umvfar()
    return cutelementsouter, cutelementsouterdir

def cutcontouraspoly(cutelementsouter, cutelementsouterdir):
    ptsseq = [ ]
    for e, bfore in zip(cutelementsouter, cutelementsouterdir):
        if bfore:
            ptsseq.extend(linearizeelement(e)[:-1])
        else:
            ptsseq.extend(reversed(linearizeelement(e)[1:]))
    return ptsseq


def dxfentitymidpoint(e):
    pts = linearizeelement(e)
    i = max(1, int(len(pts)/2))
    return (pts[i-1] + pts[i])/2

def windingnumber(p, ptsseq):
    wn = 0
    for i in range(len(ptsseq)):
        p0 = ptsseq[i]
        p1 = ptsseq[(i+1)%len(ptsseq)]
        if (p0.y < p.y) != (p1.y < p.y):
            lam = (p.y-p0.y)/(p1.y-p0.y)
            pc = p0*(1-lam) + p1*lam
            assert (abs(pc.y - p.y) < 0.01)
            if pc.x > p.x:
                wn += (1 if p0.y > p1.y else -1)
    return wn


def getblockcomponent(cutelements, penelements, dmax):
    outercutelements, outercutelementsdir = findcutelementsouter(cutelements, dmax)
    ptsseq = cutcontouraspoly(outercutelements, outercutelementsdir)

    internalcutelements = [ ]
    internalpenelements = [ ]
    remainingcutelements = [ ]
    remainingpenelements = [ ]

    for e in cutelements:
        if e not in outercutelements:
            wn = windingnumber(dxfentitymidpoint(e), ptsseq)
            if wn == 1:
                internalcutelements.append(e)
            else:
                remainingcutelements.append(e)
    for e in penelements:
        wn = windingnumber(dxfentitymidpoint(e), ptsseq)
        if wn == 1:
            internalpenelements.append(e)
        else:
            remainingpenelements.append(e)

    return (outercutelements, outercutelementsdir), (internalcutelements, internalpenelements), (remainingcutelements, remainingpenelements)


def addelementstoblock(block, offset, layer, elements, elementsdir=None):
    if not elementsdir:
        elementsdir = [ True ]*len(elements)
    for e, bfore in zip(elements, elementsdir):
        dxfattribs = { "layer":layer.dxf.name }
        if e.dxftype() == "LINE":
            if bfore:
                block.add_line(e.dxf.start+offset, e.dxf.end+offset, dxfattribs=dxfattribs)
            else:
                block.add_line(e.dxf.end+offset, e.dxf.start+offset, dxfattribs=dxfattribs)
        elif e.dxftype() == "ARC":
            if bfore:
                block.add_arc(e.dxf.center+offset, e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle, dxfattribs=dxfattribs)
            else:
                assert False, "cannot change direction of arc"
                block.add_arc(e.dxf.center+offset, e.dxf.radius, e.dxf.end_angle, e.dxf.start_angle, dxfattribs=dxfattribs)
        elif e.dxftype() == "CIRCLE":
            assert bfore
            block.add_circle(e.dxf.center+offset, e.dxf.radius, dxfattribs=dxfattribs)
        elif e.dxftype() == "SPLINE":
            pts = linearizeelement(e)
            if not bfore:
                pts.reverse()
            block.add_polyline2d([p+offset  for p in pts], dxfattribs=dxfattribs)
        else:
            print("Unknown type", e)
            #block.add_foreign_entity(e)

def reflvecY(pt):
    return ezdxf.math.vector.Vector(pt.x, -pt.y, pt.z)

def addelementstoblockReflY(block, offset, layer, elements, elementsdir=None):
    if not elementsdir:
        elementsdir = [ True ]*len(elements)
    for e, bfore in zip(elements, elementsdir):
        dxfattribs = { "layer":layer.dxf.name }
        if e.dxftype() == "LINE":
            if bfore:
                block.add_line(reflvecY(e.dxf.start)+offset, reflvecY(e.dxf.end)+offset, dxfattribs=dxfattribs)
            else:
                block.add_line(reflvecY(e.dxf.end)+offset, reflvecY(e.dxf.start)+offset, dxfattribs=dxfattribs)
        elif e.dxftype() == "ARC":
            if bfore:
                block.add_arc(reflvecY(e.dxf.center)+offset, e.dxf.radius, 360-e.dxf.end_angle, 360-e.dxf.start_angle, dxfattribs=dxfattribs)
            else:
                block.add_arc(reflvecY(e.dxf.center)+offset, e.dxf.radius, 360-e.dxf.start_angle, 360-e.dxf.end_angle, dxfattribs=dxfattribs)
        elif e.dxftype() == "CIRCLE":
            assert bfore
            block.add_circle(reflvecY(e.dxf.center)+offset, e.dxf.radius, dxfattribs=dxfattribs)
        elif e.dxftype() == "SPLINE":
            pts = linearizeelement(e)
            if not bfore:
                pts.reverse()
            pts = [ reflvecY(pt)+offset  for pt in pts ]
            block.add_polyline2d(pts, dxfattribs=dxfattribs)
        else:
            print("Unknown type", e)
            #block.add_foreign_entity(e)

            
import os
def dxfoutputblocks(outputfilename, elementgroups, breflY=False):
    blockbasename = os.path.splitext(os.path.split(outputfilename)[1])[0]

    doc = ezdxf.new('R12')
    aamacutlayer = doc.layers.new("1", {"color":1})
    aamadrawlayer = doc.layers.new("8", {"color":4})
    aamaintcutlayer = doc.layers.new("11", {"color":3})

    for i, elementgroup in enumerate(elementgroups):
        (outercutelements, outercutelementsdir, internalcutelements, internalpenelements) = elementgroup
        blockname = blockbasename+str(i)
        block = doc.blocks.new(name=blockname)

        ptsseq = cutcontouraspoly(outercutelements, outercutelementsdir)
        ptsseq.append(ptsseq[0])
        if breflY:
            ptsseq = [ reflvecY(pt)  for pt in ptsseq ]
        contourcentre = ezdxf.math.vector.Vector((min(p.x  for p in ptsseq) + max(p.x  for p in ptsseq))/2, 
                                                 (min(p.y  for p in ptsseq) + max(p.y  for p in ptsseq))/2, 0)
        cptsseq = [ pt - contourcentre  for pt in ptsseq ]
        block.add_polyline2d(cptsseq, dxfattribs={ "layer":aamacutlayer.dxf.name })
        #addelementstoblock(block, aamacutlayer, outercutelements, outercutelementsdir)

        if breflY:
            addelementstoblockReflY(block, -contourcentre, aamaintcutlayer, internalcutelements)
            addelementstoblockReflY(block, -contourcentre, aamadrawlayer, internalpenelements)
        else:
            addelementstoblock(block, -contourcentre, aamaintcutlayer, internalcutelements)
            addelementstoblock(block, -contourcentre, aamadrawlayer, internalpenelements)

        msp = doc.modelspace()
        dxfattribs = {'rotation': 0, 'linetype':'BYLAYER' }
        k = msp.add_blockref(blockname, contourcentre, dxfattribs=dxfattribs)
        
    doc.set_modelspace_vport(height=2300, center=(1800, 900))
    doc.saveas(outputfilename)

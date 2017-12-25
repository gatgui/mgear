"""Component chain FK spline 01 module"""

import pymel.core as pm
from pymel.core import datatypes

from mgear.maya.shifter import component

from mgear.maya import transform, primitive, vector, curve, applyop

##########################################################
# COMPONENT
##########################################################


class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self):
        """Add all the objects needed to create the component."""

        self.normal = self.guide.blades["blade"].z * -1
        self.binormal = self.guide.blades["blade"].x

        self.WIP = self.options["mode"]

        # FK controllers ------------------------------------
        self.fk_npo = []
        self.fk_ctl = []
        self.tweak_ctl = []
        self.upv_curv_lvl = []
        t = self.guide.tra["root"]

        parent = self.root
        tOld = False
        fk_ctl = None
        self.previusTag = self.parentCtlTag
        for i, t in enumerate(transform.getChainTransform(self.guide.apos,
                                                          self.normal,
                                                          self.negate)):
            self.dist = vector.getDistance(self.guide.apos[i],
                                           self.guide.apos[i + 1])
            if self.settings["neutralpose"] or not tOld:
                tnpo = t
            else:
                tnpo = transform.setMatrixPosition(
                    tOld,
                    transform.getPositionFromMatrix(t))

            fk_npo = primitive.addTransform(
                parent, self.getName("fk%s_npo" % i), tnpo)
            fk_ctl = self.addCtl(
                fk_npo,
                "fk%s_ctl" % i,
                t,
                self.color_fk,
                "cube",
                w=self.dist,
                h=self.size * .1,
                d=self.size * .1,
                po=datatypes.Vector(self.dist * .5 * self.n_factor, 0, 0),
                tp=self.previusTag)

            tweak_ctl = self.addCtl(
                fk_ctl,
                "tweak%s_ctl" % i,
                t,
                self.color_ik,
                "square",
                w=self.size * .15,
                h=self.size * .15,
                d=self.size * .15,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.previusTag)

            upv_curv_lvl = primitive.addTransform(
                tweak_ctl, self.getName("upv%s_lvl" % i), t)
            upv_curv_lvl.attr("tz").set(.01)

            self.fk_npo.append(fk_npo)
            self.fk_ctl.append(fk_ctl)
            self.tweak_ctl.append(tweak_ctl)
            self.upv_curv_lvl.append(upv_curv_lvl)
            tOld = t
            self.previusTag = fk_ctl
            parent = fk_ctl

            # self.jnt_pos.append([fk_ctl, i, None, False])

        # add end control
        tweak_npo = primitive.addTransform(
            fk_ctl, self.getName("tweakEnd_npo"), t)
        tweak_ctl = self.addCtl(
            tweak_npo,
            "tweakEnd_ctl",
            t,
            self.color_ik,
            "square",
            w=self.size * .15,
            h=self.size * .15,
            d=self.size * .15,
            ro=datatypes.Vector([0, 0, 1.5708]),
            tp=self.previusTag)

        upv_curv_lvl = primitive.addTransform(
            tweak_ctl, self.getName("upvEnd_lvl"), t)
        upv_curv_lvl.attr("tz").set(.01)

        tweak_npo.attr("tx").set(self.dist)

        self.tweak_ctl.append(tweak_ctl)
        self.upv_curv_lvl.append(upv_curv_lvl)

        # add length offset control if keep length
        # This option will be added only if keep length is active
        if self.settings["keepLength"]:
            self.tweakTip_npo = primitive.addTransform(
                tweak_ctl, self.getName("tweakTip_npo"), t)
            tweak_ctl = self.addCtl(
                self.tweakTip_npo,
                "tweakEnd_ctl",
                t,
                self.color_fk,
                "square",
                w=self.size * .1,
                h=self.size * .1,
                d=self.size * .1,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.previusTag)

            upv_curv_lvl = primitive.addTransform(
                tweak_ctl, self.getName("upvTip_lvl"), t)
            upv_curv_lvl.attr("tz").set(.01)

            # move to align with the parent
            self.tweakTip_npo.attr("tx").set(0)

            self.tweak_ctl.append(tweak_ctl)
            self.upv_curv_lvl.append(upv_curv_lvl)

        # Curves -------------------------------------------
        self.mst_crv = curve.addCnsCurve(self.root,
                                         self.getName("mst_crv"),
                                         self.tweak_ctl,
                                         3)

        self.upv_crv = curve.addCnsCurve(self.root,
                                         self.getName("upv_crv"),
                                         self.upv_curv_lvl,
                                         3)

        self.mst_crv.setAttr("visibility", False)
        self.upv_crv.setAttr("visibility", False)

        # Divisions
        self.div_cns = []
        self.upv_cns = []

        if self.settings["overrideJntNb"]:
            self.def_number = self.settings["jntNb"]
        else:
            self.def_number = len(self.guide.apos)

        for i in range(self.def_number):
            # References
            div_cns = primitive.addTransform(self.root,
                                             self.getName("%s_cns" % i))

            pm.setAttr(div_cns + ".inheritsTransform", False)
            self.div_cns.append(div_cns)

            upv_cns = primitive.addTransform(self.root,
                                             self.getName("%s_upv" % i))

            pm.setAttr(upv_cns + ".inheritsTransform", False)
            self.upv_cns.append(upv_cns)

            self.jnt_pos.append([div_cns, i])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""
        return

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        if self.settings["keepLength"]:
            arclen_node = pm.arclen(self.mst_crv, ch=True)
            alAttr = pm.getAttr(arclen_node + ".arcLength")
            muldiv_node = pm.createNode("multiplyDivide")
            pm.connectAttr(arclen_node + ".arcLength",
                           muldiv_node + ".input1X")
            pm.setAttr(muldiv_node + ".input2X", alAttr)
            pm.setAttr(muldiv_node + ".operation", 2)
            pm.addAttr(self.mst_crv, ln="length_ratio", k=True, w=True)
            pm.connectAttr(muldiv_node + ".outputX",
                           self.mst_crv + ".length_ratio")

        step = 1.000 / (self.def_number - 1)
        u = 0.000
        for i in range(self.def_number):
            cnsUpv = applyop.pathCns(self.upv_cns[i],
                                     self.upv_crv,
                                     cnsType=False,
                                     u=u,
                                     tangent=False)

            cns = applyop.pathCns(
                self.div_cns[i], self.mst_crv, False, u, True)

            if self.settings["keepLength"]:
                muldiv_node2 = pm.createNode("multiplyDivide")
                condition_node = pm.createNode("condition")
                pm.setAttr(muldiv_node2 + ".operation", 2)
                pm.setAttr(muldiv_node2 + ".input1X", u)
                pm.connectAttr(self.mst_crv + ".length_ratio",
                               muldiv_node2 + ".input2X")
                pm.connectAttr(muldiv_node2 + ".outputX",
                               condition_node + ".colorIfFalseR")
                pm.connectAttr(muldiv_node2 + ".outputX",
                               condition_node + ".secondTerm")
                pm.connectAttr(muldiv_node2 + ".input1X",
                               condition_node + ".colorIfTrueR")
                pm.connectAttr(muldiv_node2 + ".input1X",
                               condition_node + ".firstTerm")
                pm.setAttr(condition_node + ".operation", 4)

                pm.connectAttr(condition_node + ".outColorR",
                               cnsUpv + ".uValue")
                pm.connectAttr(condition_node + ".outColorR",
                               cns + ".uValue")

            cns.setAttr("worldUpType", 1)
            cns.setAttr("frontAxis", 0)
            cns.setAttr("upAxis", 1)

            pm.connectAttr(self.upv_cns[i].attr("worldMatrix[0]"),
                           cns.attr("worldUpMatrix"))
            u += step

        if self.settings["keepLength"]:
            # add the safty distance offset
            self.tweakTip_npo.attr("tx").set(self.dist)
    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.fk_ctl[0]
        self.controlRelatives["root"] = self.fk_ctl[0]
        self.jointRelatives["root"] = 0
        for i in range(0, len(self.fk_ctl) - 1):
            self.relatives["%s_loc" % i] = self.fk_ctl[i + 1]
            self.controlRelatives["%s_loc" % i] = self.fk_ctl[i + 1]
            self.jointRelatives["%s_loc" % i] = i + 1
            self.aliasRelatives["%s_ctl" % i] = i + 1
        self.relatives["%s_loc" % (len(self.fk_ctl) - 1)] = self.fk_ctl[-1]
        self.controlRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = self.fk_ctl[-1]
        self.jointRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = len(self.fk_ctl) - 1
        self.aliasRelatives["%s_loc" % (
            len(self.fk_ctl) - 1)] = len(self.fk_ctl) - 1

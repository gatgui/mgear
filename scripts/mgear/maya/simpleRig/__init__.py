# MGEAR is under the terms of the MIT License

# Copyright (c) 2016 Jeremie Passerin, Miquel Campos

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Author:     Jeremie Passerin      geerem@hotmail.com  www.jeremiepasserin.com
# Author:     Miquel Campos         hello@miquel-campos.com  www.miquel-campos.com
# Date:       2016 / 10 / 10

"""
Simple autorig for props or set dressing.

This rigging system follow the structure and naming conventions from Shifer.
"""
import datetime
import getpass

from mGear_pyqt import QtWidgets, wrapInstance

# Maya
import pymel.core as pm
import maya.OpenMayaUI as OpenMayaUI

#mGear
import mgear
import mgear.maya.icon as ico
import mgear.maya.dag as dag
import mgear.maya.transform as tra
import mgear.maya.node as nod
import mgear.string as st
import mgear.maya.attribute as att




#############################################
# GLOBAL
#############################################
PIVOT_EXTENSION = "lvl"
PGROUP_EXTENSION = "pgrp"
ROOT_EXTENSION = "root"
WIP = False



#############################################
# Helper functions
#############################################


def bBoxData(obj=None, yZero=True, *args):
    """Calculate the bounding box data

    Args:
        obj (None, optional): The object to calculate the bounding box
        yZero (bool, optional): If true, sets the hight to the lowest point
        *args: Maya dummy

    Returns:
        TYPE: Description
    """
    volCenter = False

    if not obj:
        obj = pm.selected()[0]
    shapes = pm.listRelatives(obj, ad=True, s=True)
    if shapes:
        bb = pm.polyEvaluate(shapes, b=True)
        volCenter = [ (axis[0] + axis[1]) /2 for axis in bb ]
        if yZero:
            volCenter[1] = bb[1][0]
        radio = max([bb[0][1] - bb[0][0],bb[2][1] - bb[2][0]])/1.7

    return volCenter, radio, bb

def getMayaWindow():
    """Gets Maya main window

    Returns:
        QMainWindow: Maya window
    """
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return wrapInstance(long(ptr), QtWidgets.QMainWindow)

def cnsPart(source, target):
    """Constraint target to source with parent and scale constraint

    Args:
        source (dagNode): Source object
        target (dagNode): target object
    """
    if not WIP:
        pm.parentConstraint(source, target, mo=True)
        pm.scaleConstraint(source, target, mo=True)


    if WIP:
        # Is not working with stack offset objects
        offsetLvl = pm.createNode("transform", n=source.name().split("_")[0]+"_offLvl")
        pm.parent(offsetLvl, source)
        mulmat_node =  pm.createNode("multMatrix")
        pm.connectAttr(offsetLvl+".worldMatrix", mulmat_node+".matrixIn[0]", f=True)
        pm.connectAttr(target+".parentInverseMatrix", mulmat_node+".matrixIn[1]", f=True)


        dm_node = nod.createDecomposeMatrixNode(mulmat_node+".matrixSum")
        pm.connectAttr(dm_node+".outputTranslate", target+".t", f=True)
        pm.connectAttr(dm_node+".outputRotate", target+".r", f=True)
        pm.connectAttr(dm_node+".outputScale", target+".s", f=True)




###########################################
# RIG TOOLS
###########################################

# ========================================================
def simpleRig(rigName="rig", wCntCtl=False, *args):
    """Create a simple 1Click rig.

    Args:
        rigName (str, optional): Name of the rig.
        wCntCtl (bool, optional): Place the Golbal control in the wolrd center or use the general BBox of the selection.
        *args: Description

    Returns:
        dagNode: Rig top node
    """
    meshList = []
    ctlList = []
    lvlList = []
    absBB = []
    absRadio = 0.5

    listSelection = [oSel for oSel in  pm.selected()]


    # Create base structure
    rig = pm.createNode('transform', n=rigName)
    geo = pm.createNode('transform', n="geo", p=rig)

    att.addAttribute(rig, "is_rig", "bool", True)
    att.addAttribute(rig, "rig_name", "string", "rig")
    att.addAttribute(rig, "user", "string", getpass.getuser())
    att.addAttribute(rig, "date", "string", str(datetime.datetime.now()))
    att.addAttribute(rig, "maya_version", "string", str(pm.mel.eval("getApplicationVersionAsFloat")))
    att.addAttribute(rig, "gear_version", "string", mgear.getVersion())
    att.addAttribute(rig, "ctl_vis", "bool", True)
    att.addAttribute(rig, "jnt_vis", "bool", False)

    att.addAttribute(rig, "quickselA", "string", "")
    att.addAttribute(rig, "quickselB", "string", "")
    att.addAttribute(rig, "quickselC", "string", "")
    att.addAttribute(rig, "quickselD", "string", "")
    att.addAttribute(rig, "quickselE", "string", "")
    att.addAttribute(rig, "quickselF", "string", "")

    rig.addAttr( "rigGroups",  at='message', m=1 )
    rig.addAttr( "rigPoses", at='message', m=1 )


    for  oSel in listSelection:

        bbCenter, bbRadio, bb = bBoxData(oSel)
        lvl = pm.createNode('transform', n=oSel.name().split("_")[0] + "_npo")
        lvlList.append(lvl)
        t = tra.getTransformFromPos(bbCenter)
        lvl.setTransformation(t)
        ctl = ico.create(lvl, oSel.name().split("_")[0] + "_ctl", t, 14, icon="circle", w=bbRadio*2)
        cnsPart(ctl, oSel)


        ctlList.append(ctl)
        for oShape in oSel.listRelatives(ad=True, s=True, type='mesh'):
            pm.connectAttr(ctl+".visibility", oShape+".visibility", f=True)
            meshList.append(oShape)

        #Reparenting
        pm.parent(oSel, geo)


        #calculate the global control BB
        if not wCntCtl:
            if not absBB:
                absBB = bb
            else:
                absBB = [[min(bb[0][0], absBB[0][0]), max(bb[0][1], absBB[0][1])],
                         [min(bb[1][0], absBB[1][0]), max(bb[1][1], absBB[1][1])],
                         [min(bb[2][0], absBB[2][0]), max(bb[2][1], absBB[2][1])]]

        userPivots = dag.findChildrenPartial(oSel, PIVOT_EXTENSION)
        # Loop selection
        uPivotCtl = []
        if userPivots:
            for uPivot in reversed(userPivots):
                try:
                    pgrp = pm.PyNode(uPivot.name().split('_')[0]+"_"+PGROUP_EXTENSION)
                except:
                    pm.displayError("The selected pivot dont have the group contrapart. Review your rig structure")
                    return False
                objList = pgrp.listRelatives(ad=True)
                if objList:
                    bbCenter, bbRadio, bb = bBoxData(objList)
                    t = uPivot.getMatrix(worldSpace=True)
                    lvlParent = pm.listRelatives(uPivot, p=True)[0].name().split("_")[0]+"_ctl"
                    lvl = pm.createNode('transform', n=uPivot.split("_")[0] + "_npo")
                    lvl.setTransformation(t)
                    ctl = ico.create(lvl, uPivot.split("_")[0] + "_ctl", t, 15, icon="cube", w=bbRadio*2, h=bbRadio*2, d=bbRadio*2)
                    pm.parent(lvl, lvlParent)
                    att.setKeyableAttributes(lvl, [])
                    uPivotCtl.append(ctl)
                    #Constraint
                    cnsPart(ctl, pgrp)

                    for oShape in uPivot.listRelatives(ad=True, s=True, type='mesh'):
                        pm.connectAttr(ctl+".visibility", oShape+".visibility", f=True)
                        meshList.append(oShape)

                    #hidde user pivot
                    uPivot.attr("visibility").set(False)

    # setting the global control
    if wCntCtl:
        absCenter = [0,0,0]
    else:
        absCenter = [ (axis[0] + axis[1]) /2 for axis in absBB ]
        #set the cencter in the floor
        absCenter[1] = absBB[1][0]
        absRadio = max([absBB[0][1] - absBB[0][0],absBB[2][1] - absBB[2][0]])/1.7
    t = tra.getTransformFromPos(absCenter)
    lvl = pm.createNode('transform', n="global_npo")
    lvl.setTransformation(t)
    pm.parent(lvl, rig)
    ctlGlobal = ico.create(lvl, "global_ctl", t, 17, icon="square", w=absRadio*2, d=absRadio*2)
    pm.parent(lvlList, ctlGlobal)
    ctlList.append(ctlGlobal)
    att.setKeyableAttributes(lvl, [])
    for lvl in lvlList:
        att.setKeyableAttributes(lvl, [])

    # Create sets
    meshSet = pm.sets(meshList, n="CACHE_grp")
    ctlSet = pm.sets([ctlList, uPivotCtl], n="rig_controllers_grp")
    deformersSet = pm.sets(meshList, n="rig_deformers_grp")
    compGroup = pm.sets(meshList, n="rig_componentsRoots_grp")
    rigSets = pm.sets([meshSet, ctlSet, deformersSet, compGroup], n="rig_Sets_grp")

    pm.connectAttr(rigSets.attr("message"), "rig.rigGroups[0]")
    pm.connectAttr(meshSet.attr("message"), "rig.rigGroups[1]")
    pm.connectAttr(ctlSet.attr("message"), "rig.rigGroups[2]")
    pm.connectAttr(deformersSet.attr("message"), "rig.rigGroups[3]")
    pm.connectAttr(compGroup.attr("message"), "rig.rigGroups[4]")

    #create dagPose
    pm.select(ctlSet)
    node = pm.dagPose(save=True, selection=True)
    pm.connectAttr(node.message, rig.rigPoses[0])

    return rig


def setUserRigPivot(*args):
    """Set user pivot for a part of the rig.


    Args:
        *args: Maya dummy

    Returns:
        dagNode, dagNode: the axis and the group
    """
    listSelection = [oSel for oSel in  pm.selected()]
    if listSelection:
        parent = listSelection[0].listRelatives(p=True)
        if parent:
            parent = parent[0]
        else:
            pm.displayWarning("In order to set user pivot, the selected object must have one parent or Root")
            return False, False
        dialog = NameUIDialog(getMayaWindow())
        dialog.exec_()
        oName  = dialog.rootName

        bbCenter, bbRadio, bb = bBoxData(listSelection, yZero=False)
        t = tra.getTransformFromPos(bbCenter)
        axis = ico.axis(parent=parent, name=oName +"_"+PIVOT_EXTENSION, width=1, color=[0,0,0], m=t)
        pgrp = pm.group(listSelection, p=parent, n=oName  + "_"+ PGROUP_EXTENSION)
        return axis, pgrp
    else:
        pm.displayWarning("Please select the objects to set and the parent root/userPivot")
        return False, False


def selectObjectInUserRootPivot(*args):
    """Selects the object under the group transform contrapart of a user pivot

    Args:
        *args: Maya dummy

    Returns:
        list of dagNode: The objects under the user pivot group
    """
    oSel = pm.selected()[0]
    try:
        pgrp = pm.PyNode(oSel.name().split('_')[0]+"_"+PGROUP_EXTENSION)
        objList = pgrp.listRelatives(ad=True, type="transform")
        pm.select(objList)
    except:
        pm.displayError("The selected pivot dont have the group contrapart. Review your rig structure")
        return False

def addToUserPivot(*args):
    """Add the selected objects to a user pivot.
    First select the objects and last the pivot

    Args:
        *args: Maya dummy

    Returns:
        None: None
    """
    oSel = pm.selected()[:-1]
    pivot = pm.selected()[-1]
    try:
        pgrp = pm.PyNode(pivot.name().split('_')[0]+"_"+PGROUP_EXTENSION)
        pm.parent(oSel, pgrp)
    except:
        pm.displayError("The selected pivot dont have the group contrapart. Review your rig structure")
        return False


def createRoot(*args):
    """Create new root to organise the rig

    Args:
        *args: Maya Dummy

    Returns:
        dagNode: The group
    """
    group = False
    dialog = NameUIDialog(getMayaWindow())
    dialog.exec_()
    oName  = dialog.rootName
    if oName:

        group = pm.group(n=oName + "_" + ROOT_EXTENSION)
    return group



###########################################
# UI
###########################################
class NameUIDialog(QtWidgets.QDialog):
    """Ui dialog for names input

    """
    def __init__(self, parent=None):
        super(NameUIDialog, self).__init__(parent)
        self.setWindowTitle('Name')
        self.setObjectName('NameUI')
        self.setModal(True)
        self.resize(230, 75)
        self.rootName = ""

        mainVbox = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("Please set the name for this part." )
        label.setWordWrap(True)
        mainVbox.addWidget(label)

        self.line = QtWidgets.QLineEdit()
        # self.line.installEventFilter(self)
        mainVbox.addWidget(self.line)

        btn = QtWidgets.QPushButton('Ok')
        btn.released.connect(self.getName)
        mainVbox.addWidget(btn)

        self.line.returnPressed.connect(self.getName)



    def getName(self):
        """Get the name of from the dialog
        """
        self.rootName = st.removeInvalidCharacter(self.line.text())
        self.close()

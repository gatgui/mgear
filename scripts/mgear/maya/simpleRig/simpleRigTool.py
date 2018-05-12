import datetime
import getpass
import json

from mgear.vendor.Qt import QtCore, QtWidgets

import pymel.core as pm
from pymel import versions
from pymel.core import datatypes

import mgear
import mgear.maya.icon as ico
from mgear.maya import transform, node, attribute, applyop, utils, pyqt, curve
from mgear import string
from . import simpleRigUI as srUI
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


CTL_TAG_ATTR = "is_simple_rig_ctl"
RIG_ROOT = "rig"

# TODO: add control tags


# driven attr ===========================================

def _driven_attr(dagNode):
    # message attribute to store a list of object affected by the root or pivot
    if not dagNode.hasAttr("drivenElements"):
        dagNode.addAttr("drivenElements", attributeType='message', multi=True)
    return dagNode.attr("drivenElements")


def _add_to_driven_attr(dagNode, driven):
    # add one or more elements to the driven list
    # should check is not in another driven attr and remove from others
    d_attr = _driven_attr(dagNode)
    if not isinstance(driven, list):
        driven = [driven]
    for d in driven:
        if not _is_valid_ctl(d):
            _remove_from_driven_attr(d)
            ni = _get_driven_attr_next_available_index(d_attr)
            pm.connectAttr(d.message,
                           d_attr.attr("drivenElements[{}]".format(str(ni))))
        else:
            pm.displayWarning("{} is a simple rig control and can't be "
                              " driven by another control".format(d))


def _remove_from_driven_attr(driven):
    # remove one or more elements to the driven attr
    if not isinstance(driven, list):
        driven = [driven]
    for x in driven:
        for o in x.message.connections(p=True):
            if "drivenElements" in o.name():
                pm.disconnectAttr(x.message, o)


def _get_from_driven_attr(dagNode):
    # return a list of all elements in the driven attr as PyNodes
    d_attr = _driven_attr(dagNode)
    return d_attr.inputs()


def _get_driven_attr_next_available_index(d_attr):
    # get the next available index for the drivenElements attr
    return attribute.get_next_available_index(d_attr)


# creators ===========================================


def _create_control(name,
                    t,
                    radio,
                    parent=None,
                    icon="circle",
                    side="C",
                    indx=0,
                    color=17,
                    driven=None,
                    sets_config=None):
    name = _validate_name(name)

    def _set_name(extension):
        if side:
            fullName = "{}_{}{}_{}".format(name, side, str(indx), extension)
            i = 0
            while pm.ls(fullName):
                i += 1
                fullName = "{}_{}{}_{}".format(name, side, str(i), extension)
        else:
            fullName = "{}_{}".format(name, extension)
        return fullName

    npo = pm.createNode('transform', n=_set_name("npo"))
    npo.setTransformation(t)
    if parent:
        pm.parent(npo, parent)

    ctl = ico.create(npo,
                     _set_name("ctl"),
                     t,
                     color,
                     icon=icon,
                     w=radio * 2,
                     h=radio * 2,
                     d=radio * 2)

    attribute.addAttribute(ctl, "conf_icon", "string", icon)
    attribute.addAttribute(ctl, "conf_radio", "float", radio, keyable=False)
    attribute.addAttribute(ctl, "conf_color", "long", color, keyable=False)
    attribute.addAttribute(ctl, CTL_TAG_ATTR, "bool", True, keyable=False)
    attribute.addAttribute(ctl, "edit_mode", "bool", False, keyable=False)
    pm.parent(ctl, npo)
    attribute.setKeyableAttributes(ctl)

    if driven:
        if not isinstance(driven, list):
            driven = [driven]
        _add_to_driven_attr(ctl, driven)
        _update_driven(ctl)

    grp = _get_sets_grp()
    grp.add(ctl)
    if sets_config:
        for ef in _extra_sets(sets_config):
            ef.add(ctl)

    return ctl


# @utils.one_undo
def _create_simple_rig_root(rigName=RIG_ROOT,
                            selection=None,
                            world_ctl=True,
                            sets_config=None,
                            ctl_wcm=False,
                            fix_radio=False,
                            radio_val=100,
                            gl_shape="square",
                            w_shape="circle"):
    # create the simple rig root
    # have the attr: is_simple_rig and is_rig
    # should not create if there is a another simple rig root
    # should have synoptic attr. (synoptic configuration in UI)
    # use World_ctl should be optional

    # check if there is another rig root in the scene
    rig_models = _get_simple_rig_root()
    if rig_models:
        pm.displayWarning("Simple rig root already exist in the "
                          "scene: {}".format(str(rig_models)))
        return

    if not selection:
        if pm.selected():
            selection = pm.selected()
        else:
            pm.displayWarning("Selection is needed to create the root")
            return

    volCenter, radio, bb = _get_branch_bbox_data(selection)

    if fix_radio:
        radio = radio_val

    meshList = []
    ctlList = []

    # Create base structure
    rig = pm.createNode('transform', n=rigName)
    # geo = pm.createNode('transform', n="geo", p=rig)
    # geo.attr("overrideEnabled").set(1)
    # geo.attr("overrideDisplayType").set(2)

    attribute.addAttribute(rig, "is_rig", "bool", True, keyable=False)
    attribute.addAttribute(rig, "is_simple_rig", "bool", True, keyable=False)
    attribute.addAttribute(rig, "geoUnselectable", "bool", True)
    attribute.addAttribute(rig, "rig_name", "string", rigName)
    attribute.addAttribute(rig, "user", "string", getpass.getuser())
    attribute.addAttribute(rig, "date", "string", str(datetime.datetime.now()))

    attribute.addAttribute(rig,
                           "maya_version",
                           "string",
                           str(pm.mel.eval("getApplicationVersionAsFloat")))

    attribute.addAttribute(rig, "gear_version", "string", mgear.getVersion())
    attribute.addAttribute(rig, "ctl_vis", "bool", True)
    attribute.addAttribute(rig, "jnt_vis", "bool", False)

    attribute.addAttribute(rig, "quickselA", "string", "")
    attribute.addAttribute(rig, "quickselB", "string", "")
    attribute.addAttribute(rig, "quickselC", "string", "")
    attribute.addAttribute(rig, "quickselD", "string", "")
    attribute.addAttribute(rig, "quickselE", "string", "")
    attribute.addAttribute(rig, "quickselF", "string", "")
    attribute.addAttribute(rig, "synoptic", "string", "")
    attribute.addAttribute(rig, "comments", "string", "")

    rig.addAttr("rigGroups", at='message', m=1)
    rig.addAttr("rigPoses", at='message', m=1)
    rig.addAttr("rigCtlTags", at='message', m=1)

    if ctl_wcm:
        t = datatypes.Matrix()
    else:
        t = transform.getTransformFromPos(volCenter)

    # configure selectable geo
    for e in selection:
        pm.connectAttr(rig.geoUnselectable, e.attr("overrideEnabled"))
        e.attr("overrideDisplayType").set(2)

    # Create sets
    # meshSet = pm.sets(meshList, n="CACHE_grp")
    ctlSet = pm.sets(ctlList, n="{}_controllers_grp".format(rigName))
    deformersSet = pm.sets(meshList, n="{}_deformers_grp".format(rigName))
    compGroup = pm.sets(meshList, n="{}_componentsRoots_grp".format(rigName))

    rigSets = pm.sets([ctlSet, deformersSet, compGroup],
                      n="rig_sets_grp")

    pm.connectAttr(rigSets.attr("message"),
                   "{}.rigGroups[0]".format(rigName))
    # pm.connectAttr(meshSet.attr("message"),
    #                "{}.rigGroups[1]".format(rigName))
    pm.connectAttr(ctlSet.attr("message"),
                   "{}.rigGroups[2]".format(rigName))
    pm.connectAttr(deformersSet.attr("message"),
                   "{}.rigGroups[3]".format(rigName))
    pm.connectAttr(compGroup.attr("message"),
                   "{}.rigGroups[4]".format(rigName))

    ctt = None
    # create world ctl
    if world_ctl:
        world_ctl = _create_control("world",
                                    t,
                                    radio * 1.5,
                                    parent=rig,
                                    icon=w_shape,
                                    side=None,
                                    indx=0,
                                    color=13,
                                    driven=None,
                                    sets_config=sets_config)
        # ctlList.append(world_ctl)
        if versions.current() >= 201650:
            ctt = node.add_controller_tag(world_ctl, None)
            _connect_tag_to_rig(rig, ctt)
    else:
        world_ctl = rig

    # create global ctl
    global_ctl = _create_control("global",
                                 t,
                                 radio * 1.1,
                                 parent=world_ctl,
                                 icon=gl_shape,
                                 side="C",
                                 indx=0,
                                 color=17,
                                 driven=None,
                                 sets_config=sets_config)
    # ctlList.append(global_ctl)
    if versions.current() >= 201650:
        ctt = node.add_controller_tag(global_ctl, ctt)
        _connect_tag_to_rig(rig, ctt)

    # create local ctl
    local_ctl = _create_control("local",
                                t,
                                radio,
                                parent=global_ctl,
                                icon=gl_shape,
                                side="C",
                                indx=0,
                                color=17,
                                driven=selection,
                                sets_config=sets_config)
    # ctlList.append(local_ctl)
    if versions.current() >= 201650:
        ctt = node.add_controller_tag(local_ctl, ctt)
        _connect_tag_to_rig(rig, ctt)

    return local_ctl


# @utils.one_undo
def _create_custom_pivot(name,
                         side,
                         icon,
                         yZero,
                         selection=None,
                         parent=None,
                         sets_config=None):
    # should have an options in UI and store as attr for rebuild
    #   -side
    #   -Control Shape
    #   -Place in base or place in BBOX center

    if not selection:
        if pm.selected():
            selection = pm.selected()
        else:
            pm.displayWarning("Selection is needed to create the root")
            return

    if not parent:
        if selection and _is_valid_ctl(selection[-1]):
            parent = selection[-1]
            selection = selection[:-1]
        # elif pm.ls("local_C0_ctl"):
        #     parent = pm.PyNode("local_C0_ctl")
        else:
            pm.displayWarning("The latest selected element should be a CTL. "
                              "PARENT is needed!")
            return

    # handle the 3rd stat for yZero
    # this state will trigger to put it in world center
    wolrd_center = False
    if yZero > 1:
        yZero = True
        wolrd_center = True

    volCenter, radio, bb = _get_branch_bbox_data(selection, yZero)
    if volCenter:
        if wolrd_center:
            t = datatypes.Matrix()
        else:
            t = transform.getTransformFromPos(volCenter)

        ctl = _create_control(name,
                              t,
                              radio,
                              parent,
                              icon,
                              side,
                              indx=0,
                              color=14,
                              driven=selection,
                              sets_config=sets_config)

        # add ctl tag
        if versions.current() >= 201650:
            parentTag = pm.PyNode(pm.controller(parent, q=True)[0])
            ctt = node.add_controller_tag(ctl, parentTag)
            _connect_tag_to_rig(ctl.getParent(-1), ctt)

        return ctl


# Getters ===========================================

def _get_simple_rig_root():
    # get the root from the scene.
    # If there is more than one It will return none and print warning
    rig_models = [item for item in pm.ls(transforms=True)
                  if _is_simple_rig_root(item)]
    if rig_models:
        return rig_models[0]


def _get_children(dagNode):
    # get all children node
    children = dagNode.listRelatives(allDescendents=True,
                                     type="transform")
    return children


def _get_bbox_data(obj=None, yZero=True, *args):
    """Calculate the bounding box data

    Args:
        obj (None, optional): The object to calculate the bounding box
        yZero (bool, optional): If true, sets the hight to the lowest point
        *args: Maya dummy

    """
    volCenter = False

    if not obj:
        obj = pm.selected()[0]
    shapes = pm.listRelatives(obj, ad=True, s=True)
    if shapes:
        bb = pm.polyEvaluate(shapes, b=True)
        volCenter = [(axis[0] + axis[1]) / 2 for axis in bb]
        if yZero:
            volCenter[1] = bb[1][0]
        radio = max([bb[0][1] - bb[0][0], bb[2][1] - bb[2][0]]) / 1.7

    return volCenter, radio, bb


def _get_branch_bbox_data(selection=None, yZero=True, *args):

    absBB = None
    absCenter = None
    absRadio = 0.5
    bbox_elements = []

    if not isinstance(selection, list):
        selection = [selection]

    for e in selection:
        bbox_elements.append(e)
        for c in _get_children(e):
            if c.getShapes():
                bbox_elements.append(c)

    for e in bbox_elements:
        if not _is_valid_ctl(e):
            bbCenter, bbRadio, bb = _get_bbox_data(e)
            if not absBB:
                absBB = bb
            else:
                absBB = [[min(bb[0][0], absBB[0][0]),
                          max(bb[0][1], absBB[0][1])],
                         [min(bb[1][0], absBB[1][0]),
                          max(bb[1][1], absBB[1][1])],
                         [min(bb[2][0], absBB[2][0]),
                          max(bb[2][1], absBB[2][1])]]
            # if absCenter:
            #     absCenter = [0, 0, 0]
            # else:
            absCenter = [(axis[0] + axis[1]) / 2 for axis in absBB]
            absRadio = max([absBB[0][1] - absBB[0][0],
                            absBB[2][1] - absBB[2][0]]) / 1.7

            # set the cencter in the floor
            if yZero:
                absCenter[1] = absBB[1][0]

    return absCenter, absRadio, absBB


# Build and IO ===========================================

def _collect_configuration_from_rig():
    # TODO: collects the simple rig configuration in a dictionary
    rig_conf_dict = {}
    ctl_settings = {}
    # get root and name
    rig_root = _get_simple_rig_root()

    # get controls list in hierarchycal order
    descendents = reversed(rig_root.listRelatives(allDescendents=True,
                                                  type="transform"))
    ctl_list = [d for d in descendents if d.hasAttr("is_simple_rig_ctl")]
    ctl_names_list = []
    # get setting for each ctl
    for c in ctl_list:

        # settings
        if not c.edit_mode.get() and _is_in_npo(c):
            ctl_name = c.name()
            ctl_names_list.append(ctl_name)

            conf_icon = c.conf_icon.get()
            conf_radio = c.conf_radio.get()
            conf_color = c.conf_color.get()
            ctl_color = curve.get_color(c)
            ctl_side = ctl_name.split("_")[-2][0]
            ctl_index = ctl_name.split("_")[-2][1:]
            ctl_short_name = ctl_name.split("_")[0]
            ctl_parent = c.getParent(2).name()
            # ctl transform matrix
            m = c.getMatrix(worldSpace=True)
            ctl_transform = m.get()
            # sets list
            sets_list = [s.name() for s in c.listConnections(type="objectSet")]

            # driven list
            driven_list = [n.name() for n in _get_from_driven_attr(c)]

        else:
            pm.displayWarning("Configuration can not be collected for Ctl in "
                              "edit pivot mode or not reset SRT "
                              "Finish edit pivot for or reset "
                              "SRT: {}".format(c))
            return
        shps, shps_n = curve.collect_curve_shapes(c)
        conf_ctl_dict = {"conf_icon": conf_icon,
                         "conf_radio": conf_radio,
                         "conf_color": conf_color,
                         "ctl_color": ctl_color,
                         "ctl_side": ctl_side,
                         "ctl_shapes": shps,
                         "ctl_shapes_names": shps_n,
                         "ctl_index": ctl_index,
                         "ctl_parent": ctl_parent,
                         "ctl_transform": ctl_transform,
                         "ctl_short_name": ctl_short_name,
                         "driven_list": driven_list,
                         "sets_list": sets_list}

        ctl_settings[ctl_name] = conf_ctl_dict

    rig_conf_dict["ctl_list"] = ctl_names_list
    rig_conf_dict["ctl_settings"] = ctl_settings
    data_string = json.dumps(rig_conf_dict, indent=4, sort_keys=True)

    print data_string
    return rig_conf_dict


# @utils.one_undo
def _build_rig_from_model(dagNode,
                          rigName=RIG_ROOT,
                          suffix="geoRoot",
                          sets_config=None,
                          ctl_wcm=False,
                          fix_radio=False,
                          radio_val=100,
                          gl_shape="square",
                          world_ctl=True,
                          w_shape="circle"):
    # using suffix keyword from a given model build a rig.
    suf = "_{}".format(string.removeInvalidCharacter(suffix))
    pm.displayInfo("Searching elements using suffix: {}".format(suf))

    parent_dict = {}
    local_ctl = _create_simple_rig_root(rigName,
                                        sets_config=sets_config,
                                        ctl_wcm=ctl_wcm,
                                        fix_radio=fix_radio,
                                        radio_val=radio_val,
                                        gl_shape=gl_shape,
                                        world_ctl=world_ctl,
                                        w_shape=w_shape)
    if local_ctl:
        descendents = reversed(dagNode.listRelatives(allDescendents=True,
                                                     type="transform"))
        for d in descendents:
            if d.name().endswith(suf):
                name = d.name().replace(suf, "")
                if d.getParent().name() in parent_dict:
                    parent = parent_dict[d.getParent().name()]
                else:
                    parent = local_ctl
                print d
                ctl = _create_custom_pivot(name,
                                           "C",
                                           "circle",
                                           True,
                                           selection=d,
                                           parent=parent,
                                           sets_config=sets_config)
                parent_dict[d.name()] = ctl


def _build_rig_from_configuration():
    # TODO: build the rig from a configuration
    # can be from scene configuration or from imported
    # create rig root
    return


def export_configuration():
    # TODO: export configuration to json
    _collect_configuration_from_rig()


def import_configuration():
    # TODO: import configuration
    return


# Convert to SHIFTER  ===========================================

def _shifter_control_component():
    # TODO: creates shifter control_01 component and sets the correct settings
    return


def convert_to_shifter_guide():
    # TODO: convert from configuration
    # convert the configuration to a shifter guide.
    # extractig the ctl shapes
    return


def convert_to_shifter_rig():
    # TODO: will create the guide and build the rig from configuration
    # skinning automatic base on driven attr
    return


# Edit ===========================================

def _remove_element_from_ctl(ctl, dagNode):

    # Check the ctl is reset
    if not _is_in_npo(ctl):
        pm.displayWarning("{}: have SRT values. Reset, before edit "
                          "elements".format(ctl))
        return

    # get affected by pivot
    driven = _get_from_driven_attr(ctl)

    # if dagNode is not in affected by pivot disconnect
    if dagNode in driven:
        _disconnect_driven(dagNode)
        _remove_from_driven_attr(dagNode)
        _update_driven(ctl)
    else:
        pm.displayWarning(
            "{} is is not connected to the ctl {}".format(dagNode,
                                                          ctl))


def _add_element_to_ctl(ctl, dagNode):
    # encusre the element is not yet in pivot
    driven = _get_from_driven_attr(ctl)
    # Check the ctl is reset
    if not _is_in_npo(ctl):
        pm.displayWarning("{}: have SRT values. Reset, before edit "
                          "elements".format(ctl))
        return
    # if dagNode is not in affected by pivot disconnect
    if dagNode not in driven:
        # move\add the selected elements to new pivot.
        _add_to_driven_attr(ctl, dagNode)
        _update_driven(ctl)


def _delete_pivot(dagNode):
    # should move all dependent elements and children pivots to his parent
    # element or move to the root if there is not parent pivot

    if _is_valid_ctl(dagNode):
        # get children pivots
        # Check the ctl is reset
        if not _is_in_npo(dagNode):
            pm.displayWarning("{}: have SRT values. Reset, before edit "
                              "elements".format(dagNode))
            return
        children = dagNode.listRelatives(type="transform")
        if children:
            pm.parent(children, dagNode.getParent(2))

        # clean connections
        for d in _get_from_driven_attr(dagNode):
            _disconnect_driven(d)

        # delete pivot
        pm.delete(dagNode.getParent())
        pm.select(clear=True)


def _parent_pivot(pivot, parent):
    # reparent pivot to another pivot or root
    # should avoid to parent under world_ctl or local_C0_ctl

    # check it parent is valid pivot
    if _is_valid_ctl(parent):
        if _is_valid_ctl(pivot):
            # Check the ctl is reset
            if not _is_in_npo(pivot):
                pm.displayWarning("{}: have SRT values. Reset, before edit "
                                  "elements".format(pivot))
            npo = pivot.getParent()
            pm.parent(npo, parent)
            # re-connect controller tag

            pivotTag = pm.PyNode(pm.controller(pivot, q=True)[0])
            node.controller_tag_connect(pivotTag, parent)

            pm.select(clear=True)
        else:
            pm.displayWarning("The selected Pivot: {} is not a "
                              "valid simple rig ctl.".format(parent.name()))
    else:
        pm.displayWarning("The selected parent: {} is not a "
                          "valid simple rig ctl.".format(parent.name()))


def _edit_pivot_position(ctl):
    # set the pivot in editable mode
    # check that is in neutral pose
    if not _is_in_npo(ctl):
        pm.displayWarning("The control: {} should be in reset"
                          " position".format(ctl.name()))
        return
    if not ctl.attr("edit_mode").get():
        # move childs to parent
        children = ctl.listRelatives(type="transform")
        if children:
            pm.parent(children, ctl.getParent())
        # disconnect the driven elements
        driven = _get_from_driven_attr(ctl)
        ctl.attr("edit_mode").set(True)
        for d in driven:
            # first try to disconnect
            _disconnect_driven(d)
        pm.select(ctl)
    else:
        pm.displayWarning("The control: {} Is already in"
                          " Edit pivot Mode".format(ctl.name()))
        return


def _consolidate_pivot_position(ctl):
    # consolidate the pivot position after editing

    if ctl.attr("edit_mode").get():
        # unparent the  children
        # rig = pm.PyNode(RIG_ROOT)
        rig = _get_simple_rig_root()
        npo = ctl.getParent()
        children = npo.listRelatives(type="transform")
        pm.parent(children, rig)
        # filter out the ctl
        children = [c for c in children if c != ctl]
        # set the npo to his position
        transform.matchWorldTransform(ctl, npo)
        pm.parent(ctl, npo)
        # reparent childrens
        if children:
            pm.parent(children, ctl)
        # re-connect/update driven elements
        _update_driven(ctl)
        ctl.attr("edit_mode").set(False)
        pm.select(ctl)
    else:
        pm.displayWarning("The control: {} Is NOT in"
                          " Edit pivot Mode".format(ctl.name()))


def _delete_rig():
    # delete the rig and clean all connections on the geometry
    # rig = pm.ls(RIG_ROOT)
    rig = _get_simple_rig_root()
    if rig:
        confirm = pm.confirmDialog(title='Confirm Delete Simple Rig',
                                   message='Are you sure?',
                                   button=['Yes', 'No'],
                                   defaultButton='Yes',
                                   cancelButton='No',
                                   dismissString='No')
        if confirm == "Yes":
            children = rig.listRelatives(allDescendents=True,
                                         type="transform")
            to_delete = []
            not_npo = []
            for c in children:
                if _is_valid_ctl(c):
                    if _is_in_npo(c):
                        to_delete.append(c)
                    else:
                        not_npo.append(c.name())
            if not_npo:
                pm.displayWarning("Please set all the controls to reset "
                                  "position before delete rig. The following"
                                  " controls are not "
                                  "reset:{}".format(str(not_npo)))
                return
            for c in to_delete:
                _delete_pivot(c)
            pm.delete(rig)
    else:
        pm.displayWarning("No rig found to delete!")

# utils ===========================================


def _connect_tag_to_rig(rig, ctt):

    ni = attribute.get_next_available_index(rig.rigCtlTags)
    pm.connectAttr(ctt.message,
                   rig.attr("rigCtlTags[{}]".format(str(ni))))


def _validate_name(name):
    # check and correct bad formating
    return string.removeInvalidCharacter(name)


def _is_valid_ctl(dagNode):
    # check if the dagNode is a simple rig ctl
    return dagNode.hasAttr(CTL_TAG_ATTR)


def _is_simple_rig_root(dagNode):
    # check if the dagNode is a simple rig ctl
    return dagNode.hasAttr("is_simple_rig")


def _is_in_npo(dagNode):
    # check if the SRT is reset
    trAxis = ["tx", "ty", "tz", "rx", "ry", "rz"]
    sAxis = ["sx", "sy", "sz"]
    npo_status = True
    for axis in trAxis:
        val = dagNode.attr(axis).get()
        if val != 0.0:
            npo_status = False
            pm.displayWarning("{}.{} is not neutral! Value is {}, "
                              "but should be {}".format(dagNode.name(),
                                                        axis,
                                                        str(val),
                                                        "0.0"))
    for axis in sAxis:
        val = dagNode.attr(axis).get()
        if val != 1.0:
            npo_status = False
            pm.displayWarning("{}.{} is not neutral! Value is {}, "
                              "but should be {}".format(dagNode.name(),
                                                        axis,
                                                        str(val),
                                                        "1.0"))
    return npo_status


# groups ==============================================

def _get_sets_grp(grpName="controllers_grp"):
    # node = pm.PyNode(RIG_ROOT)
    rig = _get_simple_rig_root()
    sets = rig.listConnections(type="objectSet")

    controllersGrp = None
    for oSet in sets:
        if grpName in oSet.name():
            controllersGrp = oSet

    return controllersGrp


def _extra_sets(sets_config):
    # sets_config = "animSets.basic.test,animSets.facial"
    sets_grp = _get_sets_grp("sets_grp")
    sets_list = sets_config.split(",")
    last_sets_list = []
    for s in sets_list:
        set_fullname = ".".join([sets_grp.name(), s])
        parent_set = None
        # ss is the subset
        for ss in set_fullname.split("."):
            if pm.ls(ss):
                parent_set = pm.ls(ss)[0]
            else:
                child_set = pm.sets(None, n=ss)
                if parent_set:
                    parent_set.add(child_set)
                parent_set = child_set
        last_sets_list.append(parent_set)

    return last_sets_list


# Connect ===========================================

def _connect_driven(driver, driven):
    # Connect the driven element with multiply matrix
    # before connect check if the driven is valid.
    # I.E. only elements not under geoRoot.
    if _is_valid_ctl(driven):
        pm.displayWarning("{} can't not be driven or connected to a ctl, "
                          "because is a simple rig control".format(driven))
        return

    # Check the ctl is reset
        if not _is_in_npo(driver):
            pm.displayWarning("{}: have SRT values. Reset, before connect "
                              "elements".format(driver))
    # connect message of the matrix mul nodes to the driven.
    # So later is easy to delete
    mOperatorNodes = "mOperatorNodes"
    if not driven.hasAttr(mOperatorNodes):
        driven.addAttr(mOperatorNodes, attributeType='message', multi=True)
        # print driven.attr(mOperatorNodes)
    mOp_attr = driven.attr(mOperatorNodes)
    m = driven.worldMatrix.get()

    im = driver.worldMatrix.get().inverse()
    mul_node0 = applyop.gear_mulmatrix_op(im,
                                          driver.worldMatrix)
    mul_node1 = applyop.gear_mulmatrix_op(m,
                                          mul_node0.output)
    mul_node2 = applyop.gear_mulmatrix_op(mul_node1.output,
                                          driven.parentInverseMatrix)
    dm_node = node.createDecomposeMatrixNode(mul_node2.output)

    pm.connectAttr(dm_node.outputTranslate, driven.t)
    pm.connectAttr(dm_node.outputRotate, driven.r)
    pm.connectAttr(dm_node.outputScale, driven.s)
    pm.connectAttr(dm_node.outputShear, driven.shear)

    pm.connectAttr(mul_node0.message,
                   mOp_attr.attr("{}[0]".format(mOperatorNodes)))
    pm.connectAttr(mul_node1.message,
                   mOp_attr.attr("{}[1]".format(mOperatorNodes)))
    pm.connectAttr(mul_node2.message,
                   mOp_attr.attr("{}[2]".format(mOperatorNodes)))
    pm.connectAttr(dm_node.message,
                   mOp_attr.attr("{}[3]".format(mOperatorNodes)))


def _disconnect_driven(driven):
    # delete the matrix mult nodes
    mOperatorNodes = "mOperatorNodes"
    if driven.hasAttr(mOperatorNodes):
        pm.delete(driven.attr(mOperatorNodes).inputs())


# @utils.one_undo
def _update_driven(driver):
    # update the driven connections using the driver drivenElements attr
    driven = _get_from_driven_attr(driver)
    for d in driven:
        # first try to disconnect
        _disconnect_driven(d)
        # Connect
        _connect_driven(driver, d)


####################################
# Simple Rig dialog
####################################

class simpleRigUI(QtWidgets.QMainWindow, srUI.Ui_MainWindow):

    def __init__(self, parent=None):
        super(simpleRigUI, self).__init__(parent)
        self.setupUi(self)


class simpleRigTool(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        self.toolName = "SimpleRigTool"
        super(simpleRigTool, self).__init__(parent)
        self.srUIInst = simpleRigUI()

        self.setup_simpleRigWindow()
        self.create_layout()
        self.create_connections()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

    def setup_simpleRigWindow(self):

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Simple Rig")
        self.resize(280, 260)

    def create_layout(self):

        self.sr_layout = QtWidgets.QVBoxLayout()
        self.sr_layout.addWidget(self.srUIInst)

        self.setLayout(self.sr_layout)

    def create_connections(self):
        self.srUIInst.createRoot_pushButton.clicked.connect(self.create_root)
        self.srUIInst.createCtl_pushButton.clicked.connect(self.create_ctl)
        self.srUIInst.selectAffected_pushButton.clicked.connect(
            self.select_affected)
        self.srUIInst.reParentPivot_pushButton.clicked.connect(
            self.parent_pivot)
        self.srUIInst.add_pushButton.clicked.connect(self.add_to_ctl)
        self.srUIInst.remove_pushButton.clicked.connect(self.remove_from_ctl)
        self.srUIInst.editPivot_pushButton.clicked.connect(self.edit_pivot)
        self.srUIInst.setPivot_pushButton.clicked.connect(self.set_pivot)
        self.srUIInst.autoRig_pushButton.clicked.connect(self.auto_rig)

        # Menus
        self.srUIInst.deletePivot_action.triggered.connect(self.delete_pivot)
        self.srUIInst.deleteRig_action.triggered.connect(self.delete_rig)
        self.srUIInst.autoBuild_action.triggered.connect(self.auto_rig)
        self.srUIInst.export_action.triggered.connect(self.export_config)

        # Misc
        self.srUIInst.rootName_lineEdit.textChanged.connect(
            self.rootName_text_changed)
        self.srUIInst.createCtl_lineEdit.textChanged.connect(
            self.ctlName_text_changed)

    # ==============================================
    # Slots ========================================
    # ==============================================

    def rootName_text_changed(self):
        name = _validate_name(self.srUIInst.rootName_lineEdit.text())
        self.srUIInst.rootName_lineEdit.setText(name)

    def ctlName_text_changed(self):
        name = _validate_name(self.srUIInst.createCtl_lineEdit.text())
        self.srUIInst.createCtl_lineEdit.setText(name)

    def create_root(self):
        name = self.srUIInst.rootName_lineEdit.text()
        sets_config = self.srUIInst.extraSets_lineEdit.text()
        ctl_wcm = self.srUIInst.worldCenter_checkBox.isChecked()
        fix_radio = self.srUIInst.fixSize_checkBox.isChecked()
        radio_val = self.srUIInst.fixSize_doubleSpinBox.value()
        iconIdx = self.srUIInst.mainCtlShape_comboBox.currentIndex()
        icon = ["square", "circle"][iconIdx]
        w_ctl = self.srUIInst.worldCtl_checkBox.isChecked()
        iconIdx = self.srUIInst.worldCtlShape_comboBox.currentIndex()
        w_icon = ["circle", "sphere"][iconIdx]
        _create_simple_rig_root(name,
                                sets_config=sets_config,
                                ctl_wcm=ctl_wcm,
                                fix_radio=fix_radio,
                                radio_val=radio_val,
                                gl_shape=icon,
                                world_ctl=w_ctl,
                                w_shape=w_icon)

    def create_ctl(self):
        name = self.srUIInst.createCtl_lineEdit.text()
        if name:
            sideIdx = self.srUIInst.side_comboBox.currentIndex()
            side = ["C", "L", "R"][sideIdx]
            iconIdx = self.srUIInst.shape_comboBox.currentIndex()
            icon = ["circle", "cube"][iconIdx]
            position = self.srUIInst.position_comboBox.currentIndex()
            sets_config = self.srUIInst.extraSets_lineEdit.text()
            _create_custom_pivot(
                name, side, icon, yZero=position, sets_config=sets_config)
        else:
            pm.displayWarning("Name is not valid")

    # @utils.one_undo
    def select_affected(self):
        oSel = pm.selected()
        if oSel:
            ctl = oSel[0]
            pm.select(_get_from_driven_attr(ctl))

    # @utils.one_undo
    def parent_pivot(self):
        oSel = pm.selected()
        if oSel and len(oSel) >= 2:
            for c in oSel[:-1]:
                _parent_pivot(c, oSel[-1])

    # @utils.one_undo
    def add_to_ctl(self):
        oSel = pm.selected()
        if oSel and len(oSel) >= 2:
            for e in oSel[:-1]:
                _add_element_to_ctl(oSel[-1], e)

    # @utils.one_undo
    def remove_from_ctl(self):
        oSel = pm.selected()
        if oSel and len(oSel) >= 2:
            for e in oSel[:-1]:
                _remove_element_from_ctl(oSel[-1], e)

    # @utils.one_undo
    def delete_pivot(self):
        for d in pm.selected():
            _delete_pivot(d)

    # @utils.one_undo
    def edit_pivot(self):
        oSel = pm.selected()
        if oSel and len(oSel) == 1:
            _edit_pivot_position(oSel[0])
        else:
            pm.displayWarning("Please select one ctl")

    # @utils.one_undo
    def set_pivot(self):
        oSel = pm.selected()
        if oSel and len(oSel) == 1:
            _consolidate_pivot_position(oSel[0])
        else:
            pm.displayWarning("Please select one ctl")

    # @utils.one_undo
    def delete_rig(self):
        _delete_rig()

    # @utils.one_undo
    def auto_rig(self):
        oSel = pm.selected()
        if oSel and len(oSel) == 1:
            suffix = self.srUIInst.autoBuild_lineEdit.text()
            name = self.srUIInst.rootName_lineEdit.text()
            sets_config = self.srUIInst.extraSets_lineEdit.text()
            ctl_wcm = self.srUIInst.worldCenter_checkBox.isChecked()
            fix_radio = self.srUIInst.fixSize_checkBox.isChecked()
            radio_val = self.srUIInst.fixSize_doubleSpinBox.value()
            iconIdx = self.srUIInst.mainCtlShape_comboBox.currentIndex()
            icon = ["square", "circle"][iconIdx]
            w_ctl = self.srUIInst.worldCtl_checkBox.isChecked()
            iconIdx = self.srUIInst.worldCtlShape_comboBox.currentIndex()
            w_icon = ["circle", "sphere"][iconIdx]
            _build_rig_from_model(oSel[0],
                                  name,
                                  suffix,
                                  sets_config,
                                  ctl_wcm=ctl_wcm,
                                  fix_radio=fix_radio,
                                  radio_val=radio_val,
                                  gl_shape=icon,
                                  world_ctl=w_ctl,
                                  w_shape=w_icon)
        else:
            pm.displayWarning("Please select root of the model")

    def export_config(self):
        export_configuration()


def open(*args):
    pyqt.showDialog(simpleRigTool)
####################################


if __name__ == "__main__":

    open()

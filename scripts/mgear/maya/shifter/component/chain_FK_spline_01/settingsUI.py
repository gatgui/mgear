import mgear.maya.pyqt as gqt
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(255, 290)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.neutralPose_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.neutralPose_checkBox.setText("Neutral pose")
        self.neutralPose_checkBox.setObjectName("neutralPose_checkBox")
        self.verticalLayout.addWidget(self.neutralPose_checkBox)
        self.keepLength_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.keepLength_checkBox.setText("Keep Length")
        self.keepLength_checkBox.setObjectName("keepLength_checkBox")
        self.verticalLayout.addWidget(self.keepLength_checkBox)
        self.overrideJntNb_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.overrideJntNb_checkBox.setText("Override Joints Number")
        self.overrideJntNb_checkBox.setObjectName("overrideJntNb_checkBox")
        self.verticalLayout.addWidget(self.overrideJntNb_checkBox)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.jntNb_label = QtWidgets.QLabel(self.groupBox)
        self.jntNb_label.setObjectName("jntNb_label")
        self.horizontalLayout.addWidget(self.jntNb_label)
        self.jntNb_spinBox = QtWidgets.QSpinBox(self.groupBox)
        self.jntNb_spinBox.setMinimum(1)
        self.jntNb_spinBox.setProperty("value", 3)
        self.jntNb_spinBox.setObjectName("jntNb_spinBox")
        self.horizontalLayout.addWidget(self.jntNb_spinBox)
        self.verticalLayout.addLayout(self.horizontalLayout)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.gridLayout_2.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(gqt.fakeTranslate("Form", "Form", None, -1))
        self.jntNb_label.setText(gqt.fakeTranslate("Form", "Joints Number", None, -1))

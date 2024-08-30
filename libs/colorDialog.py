try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import QColorDialog, QDialogButtonBox
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

BB = QDialogButtonBox#管理对话框按钮的类


class ColorDialog(QColorDialog):#继承自QColorDialog类。QColorDialog是Qt提供的一个用于选择颜色的标准对话框类
    '''
    自定义的颜色选择对话框，它允许用户选择带有透明度的颜色
    '''

    def __init__(self, parent=None):#parent=None表示这个对话框没有父窗口，它是一个独立的窗口
        super(ColorDialog, self).__init__(parent)
        self.setOption(QColorDialog.ShowAlphaChannel)#使其可以显示带有透明度的颜色
        # The Mac native dialog does not support our restore button.
        self.setOption(QColorDialog.DontUseNativeDialog)#要使用平台的原生颜色选择对话框
        # Add a restore defaults button.
        # The default is set at invocation time, so that it
        # works across dialogs for different elements.
        self.default = None#
        self.bb = self.layout().itemAt(1).widget()#添加一个“恢复默认”按钮
        self.bb.addButton(BB.RestoreDefaults)
        self.bb.clicked.connect(self.checkRestore)

    def getColor(self, value=None, title=None, default=None):
        '''获取颜色选择对话框中用户选择的颜色'''
        self.default = default
        if title:
            self.setWindowTitle(title)
        if value:
            self.setCurrentColor(value)
        return self.currentColor() if self.exec_() else None

    def checkRestore(self, button):
        '''
        检查被点击的按钮是否是“恢复默认”按钮（通过BB.ResetRole判断），
        并且检查是否有默认颜色设置（self.default是否不为None）
        '''
        if self.bb.buttonRole(button) & BB.ResetRole and self.default:
            self.setCurrentColor(self.default)

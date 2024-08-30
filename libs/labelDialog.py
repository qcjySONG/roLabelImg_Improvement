try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from lib import newIcon, labelValidator

BB = QDialogButtonBox


class LabelDialog(QDialog):#label选择的时候
        # 定义了一个名为LabelDialog的类，它继承自QDialog，用于创建一个自定义的对话框。
        # 这个对话框包含一个文本编辑框（QLineEdit）和一个按钮框（QDialogButtonBox），
        # 并且可能还包含一个列表框（QListWidget），这取决于是否传入了listItem参数。

    def __init__(self, text="Enter object label", parent=None, listItem=None):
        super(LabelDialog, self).__init__(parent)#QDialog是Qt框架中用于创建标准对话框的基类。
        self.edit = QLineEdit()#创建一个QLineEdit对象（一个单行文本编辑框），并将其存储在self.edit中
        self.edit.setText(text)#self.edit（即文本编辑框）的初始文本为传入的text参数值。
        self.edit.setValidator(labelValidator())#验证器（labelValidator()），该验证器用于确保用户输入满足特定条件
        self.edit.editingFinished.connect(self.postProcess)#编辑完成（即用户完成输入并离开编辑框）时，触发postProcess方法
        layout = QVBoxLayout()#垂直布局
        layout.addWidget(self.edit)#将self.edit（文本编辑框）添加到布局中。
        self.buttonBox = bb = BB(BB.Ok | BB.Cancel, Qt.Horizontal, self)#创建一个QDialogButtonBox对象，包含“确定”（Ok）和“取消”（Cancel）两个按钮
        #为“确定”和“取消”按钮分别设置图标,
        # newIcon函数用于创建图标，这里传入的参数（'done'和'undo'）可能是图标的名称或标识符
        bb.button(BB.Ok).setIcon(newIcon('done'))
        bb.button(BB.Cancel).setIcon(newIcon('undo'))
        #当点击“确定”按钮时，触发validate方法；当点击“取消”按钮时，触发reject方法。
        bb.accepted.connect(self.validate)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)#将按钮框添加到布局中
        #如果传入了非空的listItem列表，则创建一个QListWidget（列表框），
        # 并将listItem中的每个项添加到列表中。当列表中的项被双击时，
        # 触发listItemClick方法。最后，将列表框添加到布局中。
        if listItem is not None and len(listItem) > 0:
            self.listWidget = QListWidget(self)
            for item in listItem:
                self.listWidget.addItem(item)
            self.listWidget.itemClicked.connect(self.listItemClick)
            layout.addWidget(self.listWidget)
        self.setLayout(layout)

    def validate(self):
        # 检查编辑框中的文本，如果非空则接受对话框
        try:
            if self.edit.text().trimmed():
                self.accept()
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            if self.edit.text().strip():
                self.accept()

    def postProcess(self):# 处理编辑框中的文本，去除前后空白字符
        try:
            self.edit.setText(self.edit.text().trimmed())
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            self.edit.setText(self.edit.text())

    def popUp(self, text='', move=True):
        self.edit.setText(text)
        self.edit.setSelection(0, len(text))
        self.edit.setFocus(Qt.PopupFocusReason)
        if move:
            self.move(QCursor.pos())
        return self.edit.text() if self.exec_() else None

    def listItemClick(self, tQListWidgetItem):
        try:
            text = tQListWidgetItem.text().trimmed()
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            text = tQListWidgetItem.text().strip()
        self.edit.setText(text)
        self.validate()

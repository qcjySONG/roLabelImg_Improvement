try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *


class ToolBar(QToolBar):
    #创建自定义的工具栏和工具栏按钮
    def __init__(self, title):
        super(ToolBar, self).__init__(title)#并设置工具栏的标题
        layout = self.layout()#内容边距为 0
        m = (0, 0, 0, 0)#分别代表左、上、右和下边距
        layout.setSpacing(0)
        layout.setContentsMargins(*m)
        self.setContentsMargins(*m)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)#确保工具栏没有边框

    def addAction(self, action):
        '''
        addAction方法用于向工具栏添加动作。如果传递的动作是QWidgetAction类型，
        它会直接调用父类的addAction方法来添加该动作。否则，它会创建一个ToolButton` 实例，
        并将传递的动作设置为按钮的默认动作。然后，它设置按钮的工具按钮样式为工具栏当前的样式，
        并将按钮添加到工具栏中。
        '''
        if isinstance(action, QWidgetAction):
            return super(ToolBar, self).addAction(action)
        btn = ToolButton()
        btn.setDefaultAction(action)
        btn.setToolButtonStyle(self.toolButtonStyle())
        self.addWidget(btn)


class ToolButton(QToolButton):#提供工具按钮功能的部件
    """ToolBar companion class which ensures all buttons have the same size."""
    minSize = (60, 60)#表示按钮的最小宽度和高度

    def minimumSizeHint(self):
        ms = super(ToolButton, self).minimumSizeHint()
        w1, h1 = ms.width(), ms.height()
        w2, h2 = self.minSize
        ToolButton.minSize = max(w1, w2), max(h1, h2)
        return QSize(*ToolButton.minSize)

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *


class ZoomWidget(QSpinBox):

    def __init__(self, value=100):
        super(ZoomWidget, self).__init__()
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setRange(1, 500)#调整的倍率从1--500
        self.setSuffix(' %')#设置控件值的后缀为 '%'
        self.setValue(value)#设置控件的初始值为 value，其默认值为 100
        self.setToolTip(u'Zoom Level')#设置控件的工具提示为 "Zoom Level
        self.setStatusTip(self.toolTip())
        self.setAlignment(Qt.AlignCenter)#设置控件内的文本居中对齐

    def minimumSizeHint(self):#供控件的最小推荐尺寸
        height = super(ZoomWidget, self).minimumSizeHint().height()#获取父类 QSpinBox 的最小推荐高度
        fm = QFontMetrics(self.font())#获取控件当前字体的度量信息
        width = fm.width(str(self.maximum()))#计算控件最大值（这里是 500）的字符串表示形式在当前字体下的宽度
        return QSize(width, height)

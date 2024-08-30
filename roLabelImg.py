#!/usr/bin/env python
# -*- coding: utf8 -*-
import codecs
import os.path
import re
import sys
import shutil
import subprocess
import webbrowser as wb
from functools import partial
from collections import defaultdict

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    # needed for py3+qt4
    # Ref:
    # http://pyqt.sourceforge.net/Docs/PyQt4/incompatible_apis.html
    # http://stackoverflow.com/questions/21217399/pyqt4-qtcore-qvariant-object-instead-of-a-string
    if sys.version_info.major >= 3:
        import sip
        sip.setapi('QVariant', 2)
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
import warnings
# 忽略特定类型的警告
warnings.filterwarnings("ignore", category=DeprecationWarning)#浮点数转换错误的问题



import resources
# Add internal libs
dir_name = os.path.abspath(os.path.dirname(__file__))
libs_path = os.path.join(dir_name, 'libs')
sys.path.insert(0, libs_path)
from lib import struct, newAction, newIcon, addActions, fmtShortcut
from shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
from canvas import Canvas
from zoomWidget import ZoomWidget
from labelDialog import LabelDialog
from colorDialog import ColorDialog
from labelFile import LabelFile, LabelFileError
from toolBar import ToolBar
from pascal_voc_io import PascalVocReader
from pascal_voc_io import XML_EXT
from ustr import ustr

__appname__ = 'roLabelImg'

# Utility functions and classes.


def have_qstring():
    '''p3/qt5 get rid of QString wrapper as py3 has native unicode str type'''
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))


def util_qt_strlistclass():
    return QStringList if have_qstring() else list


class WindowMixin(object):

    def menu(self, title, actions=None):
        '''title（用于设置菜单的标题）和 actions（一个可选参数，可能是一个动作列表，用于添加到菜单中的动作）'''
        menu = self.menuBar().addMenu(title)
        if actions:
            addActions(menu, actions)#将这些动作添加到新创建的菜单中
        return menu

    def toolbar(self, title, actions=None):
        '''title（用于设置工具栏的标题）和 actions（一个可选参数，用于添加到工具栏中的动作）'''
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)#设置工具栏的工具按钮样式为“文本位于图标下方”
        if actions:
            addActions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar


# PyQt5: TypeError: unhashable type: 'QListWidgetItem'
class HashableQListWidgetItem(QListWidgetItem):

    def __init__(self, *args):
        super(HashableQListWidgetItem, self).__init__(*args)

    def __hash__(self):
        return hash(id(self))


class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))#适应窗口、适应宽度和手动缩放

    def __init__(self, defaultFilename=None, defaultPrefdefClassFile=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)
        # Save as Pascal voc xml
        self.defaultSaveDir = None#默认保存目录，用于保存文件。
        self.usingPascalVocFormat = True#否使用Pascal VOC格式保存文件
        # For loading all image under a directory
        self.mImgList = []#存储加载的图像
        self.dirname = None#存储当前目录的名称
        self.labelHist = []#存储标签
        self.lastOpenDir = None#存储上次打开的目录

        # Whether we need to save or not.
        self.dirty = False#表示窗口内容是否已修改但尚未保存
        #控制是否允许创建新的项目或资源
        self.isEnableCreate = True
        self.isEnableCreateRo = True

        # Enble auto saving if pressing next
        self.autoSaving = True
        self._noSelectionSlot = False
        self._beginner = True
        self.screencastViewer = "Edge"#默认在Firefox浏览器中打开
        self.screencast = "https://openmmlab.com/"
        # For a demo of original labelImg, please see "https://youtu.be/p0nR2YsCY_U"

        # Main widgets and related state.
        self.labelDialog = LabelDialog(parent=self, listItem=self.labelHist)
        
        self.itemsToShapes = {}
        self.shapesToItems = {}
        self.prevLabelText = ''#存储上一个选择的标签文本
        #垂直布局（QVBoxLayout），并设置了其内容边距为0。
        listLayout = QVBoxLayout()
        listLayout.setContentsMargins(0, 0, 0, 0)
        
        # Create a widget for using default label
        self.useDefautLabelCheckbox = QCheckBox(u'使用默认标签')#复选框，并将其文本设置为“Use default label”（使用默认标签）
        self.useDefautLabelCheckbox.setChecked(False)#复选框的初始状态为未选中,启动时，默认标签的使用功能将是关闭的
        self.defaultLabelTextLine = QLineEdit()#创建了一个文本输入框
        useDefautLabelQHBoxLayout = QHBoxLayout()#创建了一个水平布局，用于将复选框和文本输入框水平排列
        useDefautLabelQHBoxLayout.addWidget(self.useDefautLabelCheckbox)#复选框添加到水平布局中
        useDefautLabelQHBoxLayout.addWidget(self.defaultLabelTextLine)#将文本输入框也添加到水平布局中，使其位于复选框的右侧。
        useDefautLabelContainer = QWidget()#包含水平布局和其中的小部件
        useDefautLabelContainer.setLayout(useDefautLabelQHBoxLayout)#将之前创建的水平布局设置为容器的布局

        # 创建编辑和难度选择按钮的控件
        """
        此代码块用于创建用户界面中的两个按钮：难度选择按钮和编辑按钮。
        - 难度选择按钮是一个复选框，默认未选中状态。
        - 编辑按钮是一个工具按钮，其样式设置为文本与图标并排显示。
        这两个按钮均与外部方法`btnstate`相连，以响应状态变化事件。
        """
        self.diffcButton = QCheckBox(u'difficult')  # 创建一个难度选择的复选框
        self.diffcButton.setChecked(False)  # 设置默认为未选中状态
        self.diffcButton.stateChanged.connect(self.btnstate)  # 将其状态改变事件与btnstate方法连接
        self.editButton = QToolButton()  # 创建一个编辑功能的工具按钮
        self.editButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)  # 设置按钮样式，使文本与图标并排显示

        # 将一些小部件添加到列表布局中
        listLayout.addWidget(self.editButton)  # 添加编辑按钮
        listLayout.addWidget(self.diffcButton)  # 添加难度选择按钮
        listLayout.addWidget(useDefautLabelContainer)  # 添加使用默认标签容器


        """
        创建并添加一个用于显示当前标签项的控件
        """
        # 创建标签列表控件
        self.labelList = QListWidget()
        # 创建一个容器来存放标签列表，并设置其布局
        labelListContainer = QWidget()
        labelListContainer.setLayout(listLayout)
        # 连接信号：当列表项被激活或选择发生变化时调用
        self.labelList.itemActivated.connect(self.labelSelectionChanged)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        # 连接信号：当列表项被双击时调用，用于编辑标签
        self.labelList.itemDoubleClicked.connect(self.editLabel)
        # 连接信号：用于检测复选框状态的变化
        self.labelList.itemChanged.connect(self.labelItemChanged)
        # 将标签列表控件添加到布局中
        listLayout.addWidget(self.labelList)


        self.dock = QDockWidget(u'Box Labels', self)#创建一个可停靠的窗口
        self.dock.setObjectName(u'Label')
        self.dock.setWidget(labelListContainer)#与前面已经创建的labelListContainer相关联

        # Tzutalin 20160906 : Add file list and dock to move faster
        self.fileListWidget = QListWidget()#用于显示文件列表，用户可以通过单击或双击来与这些项目交互
        self.fileListWidget.itemDoubleClicked.connect(self.fileitemDoubleClicked)#双击列表中的某个项目时，这个槽函数将被调用
        filelistLayout = QVBoxLayout()#垂直布局（QVBoxLayout）实例
        filelistLayout.setContentsMargins(0, 0, 0, 0)#fileListWidget将紧密地填充其容器，没有任何额外的空间
        filelistLayout.addWidget(self.fileListWidget)#将之前创建的fileListWidget添加到垂直布局中
        fileListContainer = QWidget()#新的容器部件（QWidget）实例，用于包含垂直布局和其中的fileListWidget
        fileListContainer.setLayout(filelistLayout)
        self.filedock = QDockWidget(u'File List', self)#创建了一个新的可停靠窗口（QDockWidget）实例，并设置了它的窗口标题为“File List”
        self.filedock.setObjectName(u'File')#设置了可停靠窗口的对象名称为“File”
        self.filedock.setWidget(fileListContainer)#将之前创建的fileListContainer（包含文件列表的容器）设置为可停靠窗口的内容部件

        self.zoomWidget = ZoomWidget()
        # self.colorDialog = ColorDialog(parent=self)

        self.canvas = Canvas()#绘图或显示区域
        self.canvas.zoomRequest.connect(self.zoomRequest)#控制图像的缩放、平移或其他与视图相关的操作

        scroll = QScrollArea()#创建了一个滚动区域
        scroll.setWidget(self.canvas)#将之前创建的canvas部件设置为滚动区域的内部部件
        # 内部部件（在这里是canvas）为可调整大小。这意味着当用户调整滚动区域的大小时，canvas也会相应地调整其大小。
        scroll.setWidgetResizable(True)

        self.scrollBars = {#存储滚动区域的垂直和水平滚动条
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }

        self.canvas.scrollRequest.connect(self.scrollRequest)#将canvas的scrollRequest信号连接到MainWindow的scrollRequest槽函数

        self.canvas.newShape.connect(self.newShape)#当canvas上创建了一个新的形状时，它会发出newShape信号
        #将canvas的shapeMoved信号连接到MainWindow的setDirty槽函数。当canvas上的形状被移动时，它会发出shapeMoved信号
        self.canvas.shapeMoved.connect(self.setDirty)
        #将canvas的selectionChanged信号连接到MainWindow的shapeSelectionChanged槽函数
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        #将canvas的drawingPolygon信号连接到MainWindow的toggleDrawingSensitive槽函数。
        # 当canvas开始或结束绘制多边形时，它会发出drawingPolygon信号
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)
        #将canvas的status信号连接到MainWindow的status槽函数。canvas可能通过status信号来通知其当前的状态（例如，忙碌、空闲、错误等）
        self.canvas.status.connect(self.status)

        #将canvas的hideNRect信号连接到MainWindow的enableCreate槽函数。
        # 当canvas上的某个特定形状（水平框）被隐藏时
        self.canvas.hideNRect.connect(self.enableCreate)
        #将canvas的hideRRect信号连接到MainWindow的enableCreateRo槽函数。
        # 当canvas上的另一个特定形状（旋转框）被隐藏时
        self.canvas.hideRRect.connect(self.enableCreateRo)

        self.setCentralWidget(scroll)#将滚动区域（scroll）设置为MainWindow的中央部件
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)#将一个名为dock的QDockWidget添加到主窗口的右侧停靠区域
        # Tzutalin 20160906 : Add file list and dock to move faster
        self.addDockWidget(Qt.RightDockWidgetArea, self.filedock)#将另一个QDockWidget（名为filedock）也添加到主窗口的右侧停靠区域
        '''
        这行代码定义了一个变量self.dockFeatures，它包含两个QDockWidget的特性：DockWidgetClosable和DockWidgetFloatable。
        DockWidgetClosable意味着用户可以关闭这个停靠窗口，而DockWidgetFloatable意味着这个停靠窗口可以从主窗口中分离出来，
        以浮动窗口的形式存在。
        '''
        self.dockFeatures = QDockWidget.DockWidgetClosable\
            | QDockWidget.DockWidgetFloatable

        '''
        这行代码设置了self.dock的特性。它首先获取self.dock当前的特性集（self.dock.features()），
        然后使用异或操作符（^）与self.dockFeatures进行运算。这实际上是清除了self.dock当前已经具有的特性（如果有的话），
        并只设置了self.dockFeatures中定义的特性。结果是，
        self.dock现在只具有DockWidgetClosable和DockWidgetFloatable这两个特性。
        '''
        self.dock.setFeatures(self.dock.features() ^ self.dockFeatures)
        self.filedock.setFeatures(self.filedock.features() ^ self.dockFeatures)

        # Actions
        action = partial(newAction, self)
        quit = action('&关闭', self.close,
                      'Ctrl+Q', 'quit', u'Quit application')

        open = action('&打开文件', self.openFile,
                      'Ctrl+O', 'open', u'Open image or label file')

        opendir = action('&打开目录', self.openDir,
                         'Ctrl+u', 'open', u'Open Dir')

        changeSavedir = action('&更改默认保存注释目录', self.changeSavedir,
                               'Ctrl+r', 'open', u'更改默认保存注释目录')

        openAnnotation = action('&打开标注文件', self.openAnnotation,
                                'Ctrl+Shift+O', 'openAnnotation', u'打开注释')

        openNextImg = action('&下一张', self.openNextImg,
                             'd', 'next', u'下一张')

        openPrevImg = action('&上一张', self.openPrevImg,
                             'a', 'prev', u'上一张')

        verify = action('&验证图片', self.verifyImg,
                        'space', 'verify', u'验证图片')

        save = action('&保存', self.saveFile,
                      'Ctrl+S', 'save', u'将标签保存为文件', enabled=False)
        saveAs = action('&另存为', self.saveFileAs,
                        'Ctrl+Shift+S', 'save-as', u'将标签保存到另一个文件',
                        enabled=False)
        close = action('&关闭', self.closeFile,
                       'Ctrl+W', 'close', u'关闭当前文件')

        color1 = action('线条 & 颜色', self.chooseColor1,
                        'Ctrl+L', 'color_line', u'选择框线条颜色')
        color2 = action('填充 & 颜色', self.chooseColor2,
                        'Ctrl+Shift+L', 'color', u'选择框填充颜色')

        createMode = action('Create\nRectBox', self.setCreateMode,
                            'Ctrl+N', 'new', u'Start drawing Boxs', enabled=False)
        editMode = action('&Edit\nRectBox', self.setEditMode,
                          'Ctrl+J', 'edit', u'Move and edit Boxs', enabled=False)

        create = action('Create\n创建区块', self.createShape,#水平框
                        'w', 'new', u'创建一个水平框标注', enabled=False)

        createRo = action('Create\n创建区块（旋）', self.createRoShape,#旋转框
                        'e', 'newRo', u'创建一个旋转框标注', enabled=False)

        delete = action('删除区块', self.deleteSelectedShape,
                        'Delete', 'delete', u'Delete', enabled=False)

        copy = action('&复制区块', self.copySelectedShape,
                      'Ctrl+C', 'copy', u'复制所选矩形框',
                      enabled=False)

        advancedMode = action('&高级模式', self.toggleAdvancedMode,
                              'Ctrl+Shift+A', 'expert', u'切换到高级模式',
                              checkable=True)

        hideAll = action('&隐藏\n矩形框', partial(self.togglePolygons, False),
                         'Ctrl+H', 'hide', u'隐藏所有矩形框',
                         enabled=False)
        showAll = action('&显示\n矩形框', partial(self.togglePolygons, True),
                         'Ctrl+A', 'hide', u'显示所有矩形框',
                         enabled=False)

        help = action('&OpenMMlab', self.tutorial, 'Ctrl+T', 'help',
                      u'显示演示')

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with"
            " %s and %s from the canvas." % (fmtShortcut("Ctrl+[-+]"),
                                             fmtShortcut("Ctrl+Wheel")))
        self.zoomWidget.setEnabled(False)

        zoomIn = action('放大画面', partial(self.addZoom, 10),
                        'Ctrl++', 'zoom-in', u'Increase zoom level', enabled=False)
        zoomOut = action('缩小画面', partial(self.addZoom, -10),
                         'Ctrl+-', 'zoom-out', u'Decrease zoom level', enabled=False)
        zoomOrg = action('&Original size', partial(self.setZoom, 100),
                         'Ctrl+=', 'zoom', u'Zoom to original size', enabled=False)
        fitWindow = action('&调整到窗口大小', self.setFitWindow,
                           'Ctrl+F', 'fit-window', u'Zoom follows window size',
                           checkable=True, enabled=False)
        fitWidth = action('自适应屏幕宽度', self.setFitWidth,
                          'Ctrl+Shift+F', 'fit-width', u'Zoom follows window width',
                          checkable=True, enabled=False)
        # 将缩放控件组合成一个列表的目的是为了更方便地切换这些控件的状态
        zoomActions = (self.zoomWidget, zoomIn, zoomOut,
                       zoomOrg, fitWindow, fitWidth)
        self.zoomMode = self.MANUAL_ZOOM#模式
        self.scalers = {#存储不同缩放模式下的缩放函数或比例
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action('&编辑标签', self.editLabel,
                      'Ctrl+E', 'edit', u'Modify the label of the selected Box',
                      enabled=False)
        self.editButton.setDefaultAction(edit)

        shapeLineColor = action('形状 & 线条颜色', self.chshapeLineColor,
                                icon='color_line', tip=u'更改此特定形状的线条颜色',
                                enabled=False)
        shapeFillColor = action('形状 & 填充颜色', self.chshapeFillColor,
                                icon='color', tip=u'更改此特定形状的填充颜色',
                                enabled=False)

        labels = self.dock.toggleViewAction()
        labels.setText('显示/隐藏标签面板')
        labels.setShortcut('Ctrl+Shift+L')

        # 标签列表的上下文菜单
        labelMenu = QMenu()#创建菜单
        addActions(labelMenu, (edit, delete))#将edit和delete两个动作添加到labelMenu
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(
            self.popLabelListMenu)

        # Store actions for further handling.
        self.actions = struct(save=save, saveAs=saveAs, open=open, close=close,
                              lineColor=color1, fillColor=color2,
                              create=createRo,
                              createRo=createRo,
                              delete=delete, edit=edit, copy=copy,
                              createMode=createMode, editMode=editMode, advancedMode=advancedMode,
                              shapeLineColor=shapeLineColor, shapeFillColor=shapeFillColor,
                              zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
                              fitWindow=fitWindow, fitWidth=fitWidth,
                              zoomActions=zoomActions,
                              fileMenuActions=(
                                  open, opendir, save, saveAs, close, quit),
                              beginner=(), advanced=(),

                              editMenu=(edit, copy, delete,
                                        None, color1, color2),
                              beginnerContext=(createRo, edit, copy, delete),
                              advancedContext=(createMode, editMode, edit, copy,
                                               delete, shapeLineColor, shapeFillColor),
                              onLoadActive=(
                                  close, create, createMode, editMode),
                              onShapesPresent=(saveAs, hideAll, showAll))

        self.menus = struct(
            file=self.menu('&文件(F)'),
            edit=self.menu('&编辑(E)'),
            view=self.menu('&查看(V)'),
            help=self.menu('帮助(H)'),
            recentFiles=QMenu('打开 &最近'),
            labelList=labelMenu)

        addActions(self.menus.file,
                   (open, opendir, changeSavedir, openAnnotation, self.menus.recentFiles, save, saveAs, close, None, quit))
        addActions(self.menus.help, (help,))
        addActions(self.menus.view, (
            labels, advancedMode, None,
            hideAll, showAll, None,
            zoomIn, zoomOut, zoomOrg, None,
            fitWindow, fitWidth))

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        addActions(self.canvas.menus[0], self.actions.beginnerContext)
        addActions(self.canvas.menus[1], (
            action('&Copy here', self.copyShape),
            action('&Move here', self.moveShape)))

        self.tools = self.toolbar('Tools')
        self.actions.beginner = (
            open, opendir, openNextImg, openPrevImg, verify, save, None, create, createRo, copy, delete, None,
            zoomIn, zoom, zoomOut, fitWindow, fitWidth)

        self.actions.advanced = (
            open, save, None,
            createMode, editMode, None,
            hideAll, showAll)

        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # Application state.
        self.image = QImage()
        self.filePath = ustr(defaultFilename)
        self.recentFiles = []
        self.maxRecent = 7
        self.lineColor = None
        self.fillColor = None
        self.zoom_level = 100
        self.fit_window = False
        # Add Chris
        self.difficult = False

        # Load predefined classes to the list
        self.loadPredefinedClasses(defaultPrefdefClassFile)
        # XXX: Could be completely declarative.
        # Restore application settings.
        if have_qstring():
            types = {
                'filename': QString,
                'recentFiles': QStringList,
                'window/size': QSize,
                'window/position': QPoint,
                'window/geometry': QByteArray,
                'line/color': QColor,
                'fill/color': QColor,
                'advanced': bool,
                # Docks and toolbars:
                'window/state': QByteArray,
                'savedir': QString,
                'lastOpenDir': QString,
            }
        else:
            types = {
                'filename': str,
                'recentFiles': list,
                'window/size': QSize,
                'window/position': QPoint,
                'window/geometry': QByteArray,
                'line/color': QColor,
                'fill/color': QColor,
                'advanced': bool,
                # Docks and toolbars:
                'window/state': QByteArray,
                'savedir': str,
                'lastOpenDir': str,
            }

        self.settings = settings = Settings(types)
        self.recentFiles = list(settings.get('recentFiles', []))
        #屏幕大小设置
        size = settings.get('window/size', QSize(720, 540))
        position = settings.get('window/position', QPoint(0, 0))#给定的屏幕坐标点（point）上弹出标签列表菜单

        self.resize(size)
        self.move(position)

        saveDir = ustr(settings.get('savedir', None))

        self.lastOpenDir = ustr(settings.get('lastOpenDir', None))
        if saveDir is not None and os.path.exists(saveDir):
            self.defaultSaveDir = saveDir
            self.statusBar().showMessage('%s started. Annotation will be saved to %s' %
                                         (__appname__, self.defaultSaveDir))
            self.statusBar().show()

        # or simply:
        # self.restoreGeometry(settings['window/geometry']
        self.restoreState(settings.get('window/state', QByteArray()))
        self.lineColor = QColor(settings.get('line/color', Shape.line_color))
        self.fillColor = QColor(settings.get('fill/color', Shape.fill_color))
        Shape.line_color = self.lineColor
        Shape.fill_color = self.fillColor
        # Add chris
        Shape.difficult = self.difficult

        def xbool(x):
            '''
            检查它是否是 QVariant 类型（QVariant 是 Qt 框架中用于存储不同数据类型的类）。
            如果是，它会使用 toBool() 方法将 QVariant 转换为布尔值。如果不是 QVariant 类型，
            它会直接使用内置的 bool() 函数尝试将 x 转换为布尔值。
            '''
            if isinstance(x, QVariant):
                return x.toBool()
            return bool(x)

        if xbool(settings.get('advanced', False)):#'advanced' 设置项,如果这个设置项的值经过 xbool 函数处理后为 True，则启用高级模式。
            self.actions.advancedMode.setChecked(True)
            self.toggleAdvancedMode()

        # 动态填充文件菜单
        self.updateFileMenu()
        # Since loading the file may take some time, make sure it runs in the

        #后台加载文件
        #在事件队列中放置一个任务，这个任务会在后台执行 self.loadFile 方法来加载文件。self.filePath or ""
        # 确保如果 self.filePath 为 None 或 False，则使用空字符串作为默认路径。
        self.queueEvent(partial(self.loadFile, self.filePath or ""))



        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

    ## Support Functions ##

    def noShapes(self):
        """
        检查当前是否有形状物品。
        该方法用于判断self.itemsToShapes是否为空，若为空则表示没有形状物品。
        参数:
        self - 对象自身的引用。
        返回值:
        bool - 如果没有形状物品，返回True；否则返回False。
        """
        return not self.itemsToShapes

    def toggleAdvancedMode(self, value=True):
        '''用于切换应用程序中的“高级模式”和“初级模式”'''
        self._beginner = not value
        self.canvas.setEditing(True)#无论 value 的值如何，这行代码都确保画布（canvas）处于编辑模式
        self.populateModeActions()#新与不同模式相关的动作（如菜单项或工具栏按钮）
        self.editButton.setVisible(not value)#根据 value 的值来控制 editButton的可见性
        if value:
            self.actions.createMode.setEnabled(True)
            self.actions.editMode.setEnabled(False)
            # self.dock.setFeatures(self.dock.features() | self.dockFeatures)
        else:
            pass
            # self.dock.setFeatures(self.dock.features() ^ self.dockFeatures)

    def populateModeActions(self):
        if self.beginner():#检查当前是否处于初级模式
            tool, menu = self.actions.beginner, self.actions.beginnerContext
        else:
            tool, menu = self.actions.advanced, self.actions.advancedContext
        self.tools.clear()#清空当前工具栏的所有动作
        addActions(self.tools, tool)#调用 addActions 函数来将当前模式的工具动作集合添加到工具栏中
        self.canvas.menus[0].clear()#清空画布第一个菜单的所有动作
        addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()#清空编辑菜单的所有动作
        #使用条件表达式来确定要添加到编辑菜单的动作集合
        actions = (self.actions.create,) if self.beginner()\
            else (self.actions.createMode, self.actions.editMode)
        addActions(self.menus.edit, actions + self.actions.editMenu)

    def setBeginner(self):
        #将应用程序设置为初级模式
        self.tools.clear()#清空工具栏上的所有动作
        addActions(self.tools, self.actions.beginner)#调用 addActions 函数来将初级模式的工具动作集合添加到工具栏中

    def setAdvanced(self):#将应用程序设置为高级模式
        self.tools.clear()
        addActions(self.tools, self.actions.advanced)

    def setDirty(self):
        #标记应用程序的状态为“脏”（即未保存更改）
        self.dirty = True
        self.canvas.verified = False
        self.actions.save.setEnabled(True)

    def setClean(self):
        #将应用程序的状态设置为“干净”（即所有更改已保存）。
        self.dirty = False#表示没有未保存的更改。
        self.actions.save.setEnabled(False)#禁用保存动作，因为所有更改都已保存。
        self.actions.create.setEnabled(True)#启用创建动作，允许用户创建新的内容或对象。
        self.actions.createRo.setEnabled(True)#同样启用另一个创建动作

    def enableCreate(self,b):#启用或禁用创建水平框
        self.isEnableCreate = not b
        self.actions.create.setEnabled(self.isEnableCreate)

    def enableCreateRo(self,b):#启用或禁用创建旋转框
        self.isEnableCreateRo = not b
        self.actions.createRo.setEnabled(self.isEnableCreateRo)

    def toggleActions(self, value=True):
        """
        Enable/Disable widgets which depend on an opened image.
        启用或禁用一组依赖于已打开图像的动作或控件
        """
        for z in self.actions.zoomActions:#对于 self.actions.zoomActions 中的每个动作，根据其 value 参数来启用或禁用它。
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queueEvent(self, function):#将一个函数放入事件队列中，以便在当前的事件循环迭代结束时执行。
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):#在状态栏中显示 message 消息，并在 delay 毫秒后自动清除它
        # print(message)
        self.statusBar().showMessage(message, delay)
        self.statusBar().show()

    def resetState(self):#重置应用程序或组件的状态到初始状态
        #项目到形状和形状到项目的映射
        self.itemsToShapes.clear()
        self.shapesToItems.clear()

        self.labelList.clear()#清除标签列表
        self.filePath = None#重置文件路劲
        self.imageData = None#重置图片数据
        self.labelFile = None#重置标签文件
        self.canvas.resetState()

    def currentItem(self):#获取当前选中的项目
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    def addRecentFile(self, filePath):#将文件路径添加到最近的文件列表
        if filePath in self.recentFiles:
            self.recentFiles.remove(filePath)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filePath)

    def beginner(self):
        return self._beginner

    def advanced(self):
        return not self.beginner()

    ## Callbacks ##
    def tutorial(self,browser='default', link=None):
        if link is None:
            link = self.screencast

        if browser.lower() == 'default':
            wb.open(link, new=2)
        elif browser.lower() == 'chrome' and self.os_name == 'Windows':
            if shutil.which(browser.lower()):  # 'chrome' not in wb._browsers in windows
                wb.register('chrome', None, wb.BackgroundBrowser('chrome'))
            else:
                chrome_path="D:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                if os.path.isfile(chrome_path):
                    wb.register('chrome', None, wb.BackgroundBrowser(chrome_path))
            try:
                wb.get('chrome').open(link, new=2)
            except:
                wb.open(link, new=2)
        elif browser.lower() in wb._browsers:
            wb.get(browser.lower()).open(link, new=2)
        #subprocess.Popen([self.screencastViewer, self.screencast])

    # create Normal Rect
    def createShape(self):
        assert self.beginner()
        self.canvas.setEditing(False)
        self.canvas.canDrawRotatedRect = False
        self.actions.create.setEnabled(False)
        self.actions.createRo.setEnabled(False)

    # create Rotated Rect
    def createRoShape(self):
        """
        创建一个旋转形状的函数。
        此函数首先断言当前状态为初学者模式，然后设置画布为不可编辑状态，
        并允许画布绘制旋转矩形。同时，禁用创建和创建旋转形状的动作。
        参数:
        self - 对象自身的引用。
        返回值:
        无
        """
        assert self.beginner()  # 断言当前状态为初学者模式
        self.canvas.setEditing(False)  # 设置画布为不可编辑状态
        self.canvas.canDrawRotatedRect = True  # 允许绘制旋转矩形
        self.actions.create.setEnabled(False)  # 禁用创建动作
        self.actions.createRo.setEnabled(False)  # 禁用创建旋转形状的动作

    def toggleDrawingSensitive(self, drawing=True):
        """
        切换绘图敏感状态。
        在绘图过程中，模式之间的切换应该被禁用。
        参数:
        drawing (bool, optional): 是否处于绘图模式。默认为 True。
        """
        # 根据绘图状态来切换编辑模式的可用性。
        # 如果处于绘图状态，则禁用编辑模式；否则，启用编辑模式。
        self.actions.editMode.setEnabled(not drawing)
        if not drawing and self.beginner():
            # Cancel creation.
            print('Cancel creation.')
            self.canvas.setEditing(True)# 设置画布为编辑模式。
            self.canvas.restoreCursor() # 恢复画布的光标设置。
            self.actions.create.setEnabled(True)
            self.actions.createRo.setEnabled(True)
            

    def toggleDrawMode(self, edit=True):
        self.canvas.setEditing(edit)
        self.actions.createMode.setEnabled(edit)
        self.actions.editMode.setEnabled(not edit)

    def setCreateMode(self):
        print('setCreateMode')
        assert self.advanced()
        self.toggleDrawMode(False)

    def setEditMode(self):
        assert self.advanced()
        self.toggleDrawMode(True)

    def updateFileMenu(self):
        # 获取当前文件的路径
        currFilePath = self.filePath
        print("# 获取当前文件的路径:currFilePath:",currFilePath)

        def exists(filename):# 定义一个内部函数exists，用于检查文件是否存在
            return os.path.exists(filename)

        menu = self.menus.recentFiles# 获取最近文件菜单对象
        menu.clear()# 清除最近文件菜单中的所有动作（菜单项）
        # 从self.recentFiles列表中筛选出存在的文件，并且这些文件不是当前文件
        files = [f for f in self.recentFiles if f !=
                 currFilePath and exists(f)]
        for i, f in enumerate(files):# 遍历筛选后的文件列表
            icon = newIcon('labels') # 为每个文件创建一个新的图标

            # 创建一个新的QAction对象，该对象将在菜单中作为一个动作（菜单项）显示
            # QAction对象接受一个图标、一个文本和一个父对象
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)

            # 连接动作的triggered信号到一个槽函数，这个槽函数是self.loadRecent方法，并传入文件路径f作为参数
            # 当用户点击菜单项时，将触发这个动作，并调用self.loadRecent方法来加载对应的文件
            action.triggered.connect(partial(self.loadRecent, f))
            # 将创建的动作添加到最近文件菜单中
            menu.addAction(action)

    def popLabelListMenu(self, point):
        # 在给定的屏幕坐标点（point）上弹出标签列表菜单
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def editLabel(self, item=None):
        if not self.canvas.editing():
            # 如果当前画布不处于编辑模式，则直接返回
            return
        # 如果没有传入item参数，则使用当前选中的item
        item = item if item else self.currentItem()
        # 弹出一个对话框来获取新的标签文本
        text = self.labelDialog.popUp(item.text())
        # 如果用户输入了新的文本，则更新item的文本，并标记应用程序为“已修改”状态
        if text is not None:
            item.setText(text)
            self.setDirty()

    # Tzutalin 20160906 : Add file list and dock to move faster
    '''响应某个文件列表项（可能是 QListWidget 或类似控件中的项）的双击事件'''
    def fileitemDoubleClicked(self, item=None):
        # 获取被双击的项的文本，并转换为字符串（可能为了确保兼容性或避免编码问题）
        # 然后在图片列表 self.mImgList 中查找该文本对应的索引
        currIndex = self.mImgList.index(ustr(item.text()))
        # 检查找到的索引是否在图片列表的有效范围内
        if currIndex < len(self.mImgList):
            filename = self.mImgList[currIndex]
            # 如果文件名存在（即不是空字符串或None），则加载该文件
            if filename:
                self.loadFile(filename)

    # Add chris
    def btnstate(self, item= None):
        """ Function to handle difficult examples
         date on each object """
        # 如果当前画布不处于编辑模式，则直接返回，不执行任何操作
        if not self.canvas.editing():
            return
        # 如果没有传入item参数或者当前没有选中的项，则使用labelList中的最后一项
        item = self.currentItem()
        if not item: # If not selected Item, take the first one
            item = self.labelList.item(self.labelList.count()-1)

        difficult = self.diffcButton.isChecked()# 检查是否选中了"困难"按钮

        try:# 尝试从itemsToShapes字典中获取与当前项对应的形状对象
            shape = self.itemsToShapes[item]
        except: # 如果发生异常（例如项不在字典中），则忽略并继续执行
            pass
        # 如果发生异常（例如项不在字典中），则忽略并继续执行
        try:
            if difficult != shape.difficult: # 如果"困难"按钮的状态与形状对象的"困难"属性不同
                shape.difficult = difficult# 更新形状对象的"困难"属性
                self.setDirty()# 标记应用程序状态为“已修改”
            else:  # 如果相同，则可能是用户改变了项的可见性
                self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)# 设置形状的可见性，根据项的选中状态来决定是否可见
        except:
            pass# 如果在更新过程中发生异常，则忽略并继续执行

    # React to canvas signals.
    def shapeSelectionChanged(self, selected=False):
        # 如果 _noSelectionSlot 为 True，则将其设置为 False
        # 这个变量可能用于标记是否应该忽略选择事件
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            # 获取当前选中的形状
            shape = self.canvas.selectedShape
            if shape:# 如果选中的形状存在
                # 在形状与项的映射中查找该形状对应的项，并将其设置为选中状态
                self.shapesToItems[shape].setSelected(True)
            else:# 如果没有选中的形状，则清除标签列表中的所有选择
                self.labelList.clearSelection()
        self.actions.delete.setEnabled(selected)
        self.actions.copy.setEnabled(selected)
        self.actions.edit.setEnabled(selected)
        self.actions.shapeLineColor.setEnabled(selected)
        self.actions.shapeFillColor.setEnabled(selected)

    def addLabel(self, shape):#向标签列表中添加一个标签
        item = HashableQListWidgetItem(shape.label)#创建一个新的列表项
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)#设置列表项的标志，使其可以被用户选中
        item.setCheckState(Qt.Checked)#将列表项的选中状态设置为已选中
        self.itemsToShapes[item] = shape
        self.shapesToItems[shape] = item
        self.labelList.addItem(item)
        for action in self.actions.onShapesPresent:#遍历 self.actions.onShapesPresent 中的所有动作，并将它们设置为可用状态
            action.setEnabled(True)

    def remLabel(self, shape):#从标签列表中移除与该形状相关联的标签
        if shape is None:
            # print('rm empty label')
            return
        item = self.shapesToItems[shape]#找到与传入的形状对象相关联的列表项

        print("shapesToItems:",self.shapesToItems)

        self.labelList.takeItem(self.labelList.row(item))#根据列表项的行号从 self.labelList 中移除该列表项
                                                        #row(item) 方法返回列表项在列表中的行号
        #从 self.shapesToItems 和 self.itemsToShapes 字典中删除形状对象和列表项之间的映射关系
        del self.shapesToItems[shape]
        del self.itemsToShapes[item]

    def loadLabels(self, shapes):
        #加载一系列的形状（shapes）到应用程序中
        s = []#存储创建的形状对象
        for label, points, direction, isRotated, line_color, fill_color, difficult in shapes:
            shape = Shape(label=label)#创建一个新的形状对象，并设置其标签
            for x, y in points:#遍历 points（一系列坐标点），并将它们添加到形状对象中。
                shape.addPoint(QPointF(x, y))
            #设置形状的其他属性
            shape.difficult = difficult
            shape.direction = direction
            shape.isRotated = isRotated
            shape.close()
            s.append(shape)
            self.addLabel(shape)

            if line_color:
                shape.line_color = QColor(*line_color)
            if fill_color:
                shape.fill_color = QColor(*fill_color)

        self.canvas.loadShapes(s)#加载形状到画布

    def saveLabels(self, annotationFilePath):
        '''当前的标签（labels）或注释（annotations）保存到指定的文件路径'''
        annotationFilePath = ustr(annotationFilePath)#将传入的 annotationFilePath 参数转换为 Unicode 字符串
        if self.labelFile is None:#意味着还没有创建或加载标签文件
            self.labelFile = LabelFile()#创建一个新的 LabelFile 对象，并将其赋值给 self.labelFile
            self.labelFile.verified = self.canvas.verified

        def format_shape(s):
            '''将一个形状对象 s 转换成一个字典，这个字典包含了形状的各种属性，以便于后续的保存或传输。'''
            return dict(label=s.label,
                        line_color=s.line_color.getRgb()
                        #如果形状的线条颜色与默认的线条颜色（self.lineColor）不同，则返回线条颜色的 RGB 值；否则返回 None
                        if s.line_color != self.lineColor else None,
                        fill_color=s.fill_color.getRgb()
                        if s.fill_color != self.fillColor else None,
                        points=[(p.x(), p.y()) for p in s.points],
                       # add chris
                        difficult = s.difficult,
                        # You Hao 2017/06/21
                        # add for rotated bounding box
                        direction = s.direction,
                        center = s.center,#形状的中心点坐标
                        isRotated = s.isRotated)

        shapes = [format_shape(shape) for shape in self.canvas.shapes]
        # Can add differrent annotation formats here
        try:
            if self.usingPascalVocFormat is True:#检查是否使用 Pascal VOC 格式来保存标注数据
                print ('Img: ' + self.filePath + ' -> Its xml: ' + annotationFilePath)
                self.labelFile.savePascalVocFormat(annotationFilePath, shapes, self.filePath, self.imageData,
                                                   self.lineColor.getRgb(), self.fillColor.getRgb())

            else:#否则，直接调用 self.labelFile.save 方法来保存标注数据
                self.labelFile.save(annotationFilePath, shapes, self.filePath, self.imageData,
                                    self.lineColor.getRgb(), self.fillColor.getRgb())
            return True
        except LabelFileError as e:
            self.errorMessage(u'Error saving label data',
                              u'<b>%s</b>' % e)
            return False

    def copySelectedShape(self):
        '''复制当前选中的形状，并将它作为一个新的标签添加到画布上。'''
        #self.canvas.copySelectedShape()：从画布上复制当前选中的形状
        self.addLabel(self.canvas.copySelectedShape())#将复制的形状作为一个新的标签添加到画布上
        # fix copy and delete
        self.shapeSelectionChanged(True)

    def labelSelectionChanged(self):#用来响应标签选择的变化的
        item = self.currentItem()#获取当前选中的项
        if item and self.canvas.editing():#检查是否有选中的项，并且画布是否处于编辑模式
            self._noSelectionSlot = True#设置一个内部标志，可能是用来追踪或防止多次触发选择事件
            self.canvas.selectShape(self.itemsToShapes[item])
            shape = self.itemsToShapes[item]#获取与当前项关联的形状对象。
            # Add Chris
            self.diffcButton.setChecked(shape.difficult)#根据形状的难度属性设置某个按钮

    def labelItemChanged(self, item):
        '''响应标签项更改'''
        shape = self.itemsToShapes[item]#获取与更改的标签项关联的形状对象
        label = item.text()#获取标签项的文本内容
        if label != shape.label:#检查标签项的文本是否与形状当前的标签不同。
            shape.label = item.text()#如果不同，更新形状的标签为标签项的文本。
            self.setDirty()#标记数据为“脏”
        else:  # User probably changed item visibility
            self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    # Callback functions:
    def newShape(self):
        """
        弹出一个标签编辑器，并给它焦点。注释还提到位置必须是全局坐标。
        """
        if not self.useDefautLabelCheckbox.isChecked() or not self.defaultLabelTextLine.text():
            #可能是一个复选框，用于选择是否使用默认标签
            if len(self.labelHist) > 0:#存储历史标签的列表
                self.labelDialog = LabelDialog(
                    parent=self, listItem=self.labelHist)

            text = self.labelDialog.popUp(text=self.prevLabelText)#弹出对话框并获取用户输入的文本，将其存储在变量 text 中
            print("977-text:",text)
        else:
            text = self.defaultLabelTextLine.text()
            print("980-text:", text)

        # Add Chris
        self.diffcButton.setChecked(False)#重置难度按钮状态
        if text is not None:#用户输入了标签文本
            self.prevLabelText = text#将 text 存储为 self.prevLabelText，以便后续使用
            self.addLabel(self.canvas.setLastLabel(text))
            if self.beginner():  # Switch to edit mode.
                self.canvas.setEditing(True)
                self.actions.create.setEnabled(self.isEnableCreate)
                self.actions.createRo.setEnabled(self.isEnableCreateRo)
            else:
                self.actions.editMode.setEnabled(True)
            self.setDirty()

            if text not in self.labelHist:
                self.labelHist.append(text)
        else:
            # self.canvas.undoLastLine()
            self.canvas.resetAllLines()

    def scrollRequest(self, delta, orientation):#处理滚动请求
        '''
        delta：滚动的量或方向。
        orientation：滚动的方向
        '''
        units = - delta / (8 * 15)#计算滚动单位
        bar = self.scrollBars[orientation]#滚动方向获取相应的滚动条
        bar.setValue(bar.value() + bar.singleStep() * units)

    def setZoom(self, value):#设置缩放级别
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=10):#增加缩放级别
        self.setZoom(self.zoomWidget.value() + increment)

    def zoomRequest(self, delta):#处理缩放请求
        units = delta / (8 * 15)
        scale = 10
        self.addZoom(scale * units)

    def setFitWindow(self, value=True):#设置是否适应窗口大小进行缩放
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):#设置是否适应宽度进行缩放
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def togglePolygons(self, value):#切换多边形的显示状态
        for item, shape in self.itemsToShapes.items():
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)

    def loadFile(self, filePath=None):
        """Load the specified file, or the last opened file if None."""
        '''加载指定的文件，如果filePath为空，则加载最后打开的文件'''
        print("filePath,1043:",filePath)
        #重置状态并禁用画布
        self.resetState()
        self.canvas.setEnabled(False)

        if filePath is None:
            #如果filePath为空，则从设置中获取文件名
            filePath = self.settings.get('filename')

        unicodeFilePath = ustr(filePath)#将filePath转换为Unicode格式
        # Tzutalin 20160906 : 添加文件列表和停靠以加快移动速度
        # 高亮显示文件项
        if unicodeFilePath and self.fileListWidget.count() > 0:#如果unicodeFilePath存在且文件列表小部件计数大于0，则突出显示文件项
            index = self.mImgList.index(unicodeFilePath)# 获取文件路径在mImgList中的索引
            fileWidgetItem = self.fileListWidget.item(index)# 获取文件路径对应的列表项

            print("1058-fileWidgetItem:",fileWidgetItem)

            fileWidgetItem.setSelected(True)# 设置列表项为选中状态

        if unicodeFilePath and os.path.exists(unicodeFilePath):#如果unicodeFilePath存在且文件路径有效
            if LabelFile.isLabelFile(unicodeFilePath):#检查是否为标签文件
                try:
                    self.labelFile = LabelFile(unicodeFilePath)#打开标签文件
                except LabelFileError as e:
                    self.errorMessage(u'Error opening file',
                                      (u"<p><b>%s</b></p>"
                                       u"<p>Make sure <i>%s</i> is a valid label file.")
                                      % (e, unicodeFilePath))
                    self.status("Error reading %s" % unicodeFilePath)
                    return False
                self.imageData = self.labelFile.imageData # 获取图像数据
                self.lineColor = QColor(*self.labelFile.lineColor)# 获取线条颜色
                self.fillColor = QColor(*self.labelFile.fillColor)# 获取填充颜色
            else:
                # 加载图像：
                # 首先读取数据并存储以便保存到标签文件中
                self.imageData = read(unicodeFilePath, None)# 读取图像数据
                self.labelFile = None
            image = QImage.fromData(self.imageData)# 将图像数据转换为QImage对象
            if image.isNull():
                self.errorMessage(u'Error opening file',
                                  u"<p>Make sure <i>%s</i> is a valid image file." % unicodeFilePath)
                self.status("Error reading %s" % unicodeFilePath)
                return False
            self.status("Loaded %s" % os.path.basename(unicodeFilePath))
            self.image = image # 设置图像属性
            self.filePath = unicodeFilePath # 设置文件路径属性
            self.canvas.loadPixmap(QPixmap.fromImage(image)) # 在画布上加载图像
            if self.labelFile:
                self.loadLabels(self.labelFile.shapes)# 加载标签
            self.setClean()# 设置状态为干净
            self.canvas.setEnabled(True)# 启用画布
            self.adjustScale(initial=True)# 调整缩放
            self.paintCanvas()# 绘制画布
            self.addRecentFile(self.filePath)# 将文件添加到最近打开文件列表
            self.toggleActions(True)# 切换操作

            # # 如果使用Pascal VOC格式，则标记XML文件并根据文件名显示边界框
            if self.usingPascalVocFormat is True:
                if self.defaultSaveDir is not None:
                    basename = os.path.basename(
                        os.path.splitext(self.filePath)[0]) + XML_EXT
                    xmlPath = os.path.join(self.defaultSaveDir, basename)
                    self.loadPascalXMLByFilename(xmlPath)
                else:
                    xmlPath = filePath.split(".")[0] + XML_EXT
                    if os.path.isfile(xmlPath):
                        self.loadPascalXMLByFilename(xmlPath)

            self.setWindowTitle(__appname__ + ' ' + filePath)

            # 默认情况下，如果有至少一个标签，则选择最后一个标签项
            if self.labelList.count():
                self.labelList.setCurrentItem(self.labelList.item(self.labelList.count()-1))
                # self.labelList.setItemSelected(self.labelList.item(self.labelList.count()-1), True)

            self.canvas.setFocus(True)# 设置焦点在画布上
            return True
        return False

    def resizeEvent(self, event):#处理窗口大小调整事件
        '''
        如果self.canvas存在、self.image不是空的（即已加载了图像），
        并且缩放模式不是手动（self.zoomMode != self.MANUAL_ZOOM），
        则调用self.adjustScale()来调整缩放。
        '''
        if self.canvas and not self.image.isNull()\
           and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):#绘制画布
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()#设置画布的缩放比例（self.canvas.scale）为self.zoomWidget.value()的0.01倍
        self.canvas.adjustSize()#调整画布大小以适应缩放后的内容
        self.canvas.update()#更新画布以显示新的绘制内容

    def adjustScale(self, initial=False):#调整缩放级别
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def scaleFitWindow(self):
        """Figure out the size of the pixmap in order to fit the main widget."""
        '''计算图像在窗口中适应显示的缩放比例'''
        e = 2.0  # So that no scrollbars are generated.
        #计算主窗口部件（self.centralWidget()）的宽度和高度，并减去一个小的常数e，以避免生成滚动条
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1 #计算窗口部件的宽高比
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2 #计算图像的宽高比
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        #计算图像在窗口中适应宽度的缩放比例
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()
        s = self.settings
        # If it loads images from dir, don't load it at the begining
        if self.dirname is None:
            s['filename'] = self.filePath if self.filePath else ''
        else:
            s['filename'] = ''

        s['window/size'] = self.size()
        s['window/position'] = self.pos()
        s['window/state'] = self.saveState()
        s['line/color'] = self.lineColor
        s['fill/color'] = self.fillColor
        s['recentFiles'] = self.recentFiles
        s['advanced'] = not self._beginner
        if self.defaultSaveDir is not None and len(self.defaultSaveDir) > 1:
            s['savedir'] = ustr(self.defaultSaveDir)
        else:
            s['savedir'] = ""

        if self.lastOpenDir is not None and len(self.lastOpenDir) > 1:
            s['lastOpenDir'] = self.lastOpenDir
        else:
            s['lastOpenDir'] = ""

    ## User Dialogs ##

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def scanAllImages(self, folderPath):#扫描指定文件夹中的所有图像文件
        '''folderPath：要扫描的文件夹的路径'''
        extensions = ['.jpeg', '.jpg', '.png', '.bmp']
        images = []
        print("1202-images:",images)

        #使用os.walk函数递归地遍历folderPath指定的文件夹及其所有子文件夹
        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):#endswith方法和一个元组来检查多个扩展名
                    relatviePath = os.path.join(root, file)#将当前目录路径和文件名组合成相对路径
                    path = ustr(os.path.abspath(relatviePath))#将相对路径转换为绝对路径
                    images.append(path)
        images.sort(key=lambda x: x.lower())#以确保路径按字母顺序排列
        return images

    def changeSavedir(self, _value=False):#改变保存目录
        if self.defaultSaveDir is not None:
            path = ustr(self.defaultSaveDir)
        else:
            path = '.'

        dirpath = ustr(QFileDialog.getExistingDirectory(self,
                                                       '%s - 保存到该目录下' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                       | QFileDialog.DontResolveSymlinks))

        if dirpath is not None and len(dirpath) > 1:
            self.defaultSaveDir = dirpath

        self.statusBar().showMessage('%s . Annotation will be saved to %s' %
                                     ('Change saved folder', self.defaultSaveDir))
        self.statusBar().show()

    def openAnnotation(self, _value=False):#选择一个Pascal VOC格式的标注XML文件
        if self.filePath is None:
            return

        path = os.path.dirname(ustr(self.filePath))\
            if self.filePath else '.'
        if self.usingPascalVocFormat:#获取文件所在目录
            filters = "Open Annotation XML file (%s)" % \
                      ' '.join(['*.xml'])
            #弹出文件选择对话框
            filename = QFileDialog.getOpenFileName(self,'%s - Choose a xml file' % __appname__, path, filters)
            if filename:
                if isinstance(filename, (tuple, list)):
                    filename = filename[0]
            self.loadPascalXMLByFilename(filename)

    def openDir(self, _value=False):
        """
        打开目录选择对话框，允许用户选择一个目录，然后更新相关属性和列表以反映所选目录中的图像文件。

        :param _value: 该参数在当前函数实现中未使用，但保留以保持接口兼容性。
        :return: 无返回值。
        """
        # 如果当前操作不应继续，则直接返回
        if not self.mayContinue():
            return

        # 根据是否有文件路径来确定对话框打开的初始路径
        path = os.path.dirname(self.filePath)\
            if self.filePath else '.'

        # 如果之前打开的目录不为空且长度大于1，则使用之前打开的目录作为初始路径
        if self.lastOpenDir is not None and len(self.lastOpenDir) > 1:
            path = self.lastOpenDir

        # 使用QFileDialog获取存在的目录路径，设置显示目录而非文件，不解析符号链接
        dirpath = ustr(QFileDialog.getExistingDirectory(self,
                                                     '%s - Open Directory' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                     | QFileDialog.DontResolveSymlinks))

        # 如果用户选择了目录且路径不为空，则更新最近打开的目录
        if dirpath is not None and len(dirpath) > 1:
            self.lastOpenDir = dirpath

        # 更新目录名和文件路径，清空文件列表，扫描并更新图像列表，打开下一个图像
        self.dirname = dirpath
        self.filePath = None
        self.fileListWidget.clear()
        self.mImgList = self.scanAllImages(dirpath)
        self.openNextImg()
        # 将扫描到的图像路径添加到文件列表中
        for imgPath in self.mImgList:
            item = QListWidgetItem(imgPath)
            self.fileListWidget.addItem(item)

    def verifyImg(self, _value=False):
        """
        验证当前图像标签的状态。
        如果图像已经有标签，且尚未验证，则进行验证操作。
        验证操作包括：切换验证状态、更新画布为验证状态并保存文件。

        参数:
        - _value: 布尔值，指定是否强制验证，默认为False。当前未使用该参数。

        返回值:
        - 无
        """
        # 检查是否有文件路径，若有，则尝试进行验证操作
        if self.filePath is not None:
            try:
                self.labelFile.toggleVerify()  # 尝试切换标签文件的验证状态
            except AttributeError:
                # 如果标签文件不存在，创建并保存一个带有验证属性的标签文件
                self.saveFile()
                if self.labelFile is not None:
                    self.labelFile.toggleVerify()
            if self.labelFile is not None:
                self.canvas.verified = True  # 设置画布的验证状态为True
            self.paintCanvas()  # 更新画布显示
            self.saveFile()  # 保存文件

    def openPrevImg(self, _value=False):
        """
        打开上一张图片。
        如果当前没有可以继续的操作，或者图片列表为空，或者没有文件路径，则函数直接返回。
        如果存在上一张图片的文件路径，则加载该图片。
        参数:
        - _value: 布尔值，默认为False，该参数在当前函数实现中未使用。
        返回值:
        - 无
        """
        # 检查是否可以继续执行操作
        if not self.mayContinue():
            return
        # 检查图片列表是否为空
        if len(self.mImgList) <= 0:
            return
        # 检查是否有文件路径
        if self.filePath is None:
            return
        # 计算当前文件在列表中的索引，并尝试打开前一张图片
        currIndex = self.mImgList.index(self.filePath)
        if currIndex - 1 >= 0:
            filename = self.mImgList[currIndex - 1]
            if filename:
                self.loadFile(filename)

    def openNextImg(self, _value=False):
        """
        打开下一个图像文件。
        如果当前文件有更改且设置了自动保存，则先保存当前文件。
        如果可以继续，则尝试打开下一个图像，如果没有下一个则不进行操作。
        参数:
        - _value: 布尔值，用于内部逻辑判断，一般设为False，默认不使用。
        返回值:
        - 无
        """
        # 如果设置了自动保存且当前文件有修改，先保存文件
        if self.autoSaving is True and self.defaultSaveDir is not None:
            if self.dirty is True:
                self.dirty = False
                self.canvas.verified = True
                self.saveFile()

        # 检查是否可以继续进行
        if not self.mayContinue():
            return

        # 检查图像列表是否为空
        if len(self.mImgList) <= 0:
            return

        filename = None
        # 如果当前没有文件打开，直接打开列表中的第一个文件
        if self.filePath is None:
            filename = self.mImgList[0]
        else:
            # 如果已有文件打开，尝试打开列表中的下一个文件
            currIndex = self.mImgList.index(self.filePath)
            if currIndex + 1 < len(self.mImgList):
                filename = self.mImgList[currIndex + 1]

        # 如果找到了下一个文件，加载该文件
        if filename:
            self.loadFile(filename)


    def openFile(self, _value=False):
        """
        打开文件对话框，允许用户选择图像或标签文件，并加载所选文件。

        :param _value: 该参数在当前方法实现中未使用，但保留以保持接口兼容性。
        :return: 无返回值。
        """
        # 检查是否可以继续执行
        if not self.mayContinue():
            return
        # 获取文件路径，如果不存在则默认为当前目录
        path = os.path.dirname(ustr(self.filePath)) if self.filePath else '.'
        # 构建支持的图像文件格式过滤器
        formats = ['*.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        # 构建文件选择对话框的过滤器字符串
        filters = "Image & Label files (%s)" % ' '.join(formats + ['*%s' % LabelFile.suffix])
        # 显示打开文件对话框并获取用户选择的文件名
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__, path, filters)
        # 如果用户选择了文件，则尝试加载该文件
        if filename:
            # 处理在某些情况下返回文件名列表的情况
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            self.loadFile(filename)

    def saveFile(self, _value=False):#保存当前图像的相关数据到一个XML文件
        if self.defaultSaveDir is not None and len(ustr(self.defaultSaveDir)):#默认路径
            if self.filePath:
                #构建保存文件名
                imgFileName = os.path.basename(self.filePath)#图像文件的路径（self.filePath）中获取文件名（imgFileName），并去掉原始扩展名
                savedFileName = os.path.splitext(imgFileName)[0] + XML_EXT#然后添加XML扩展名（XML_EXT），得到新的保存文件名（savedFileName）
                #拼接完整的保存路径
                savedPath = os.path.join(ustr(self.defaultSaveDir), savedFileName)
                self._saveFile(savedPath)
        else:#如果没有默认保存目录
            #使用当前图像文件所在的目录（imgFileDir）作为保存路径的目录
            imgFileDir = os.path.dirname(self.filePath)
            imgFileName = os.path.basename(self.filePath)
            savedFileName = os.path.splitext(imgFileName)[0] + XML_EXT
            savedPath = os.path.join(imgFileDir, savedFileName)
            self._saveFile(savedPath if self.labelFile
                           else self.saveFileDialog())

    def saveFileAs(self, _value=False):#让用户选择一个新的位置来保存当前图像的相关数据
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())#弹出文件保存对话框并保存

    def saveFileDialog(self):#打开一个文件对话框让用户选择一个保存文件的位置的
        caption = '%s - Choose File' % __appname__#对话框的标题
        filters = 'File (*%s)' % LabelFile.suffix#过滤器
        openDialogPath = self.currentPath()#获取当前路径
        dlg = QFileDialog(self, caption, openDialogPath, filters)#创建文件对话框
        #设置默认后缀和接受模式
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        #预设选中的文件名
        filenameWithoutExtension = os.path.splitext(self.filePath)[0]
        dlg.selectFile(filenameWithoutExtension)
        dlg.setOption(QFileDialog.DontUseNativeDialog, False)#设置对话框选项
        if dlg.exec_():
            return dlg.selectedFiles()[0]
        return ''

    def _saveFile(self, annotationFilePath):
        if annotationFilePath and self.saveLabels(annotationFilePath):#检查annotationFilePath是否存在
            self.setClean()#已经保存
            self.statusBar().showMessage('Saved to  %s' % annotationFilePath)
            self.statusBar().show()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def mayContinue(self):
        #如果 self.dirty 为 True，表示有未保存的更改

        return not (self.dirty and not self.discardChangesDialog())

    def discardChangesDialog(self):
        yes, no = QMessageBox.Yes, QMessageBox.No
        msg = u'You have unsaved changes, proceed anyway?'
        return yes == QMessageBox.warning(self, u'Attention', msg, yes | no)

    def errorMessage(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def currentPath(self):
        return os.path.dirname(self.filePath) if self.filePath else '.'

    def chooseColor1(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.lineColor = color
            # Change the color for all shape lines:
            Shape.line_color = self.lineColor
            self.canvas.update()
            self.setDirty()

    def chooseColor2(self):
        color = self.colorDialog.getColor(self.fillColor, u'Choose fill color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.fillColor = color
            Shape.fill_color = self.fillColor
            self.canvas.update()
            self.setDirty()

    def deleteSelectedShape(self):
        self.remLabel(self.canvas.deleteSelected())
        self.setDirty()
        if self.noShapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)

    def chshapeLineColor(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.canvas.selectedShape.line_color = color
            self.canvas.update()
            self.setDirty()

    def chshapeFillColor(self):
        color = self.colorDialog.getColor(self.fillColor, u'Choose fill color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.canvas.selectedShape.fill_color = color
            self.canvas.update()
            self.setDirty()

    def copyShape(self):
        self.canvas.endMove(copy=True)
        self.addLabel(self.canvas.selectedShape)
        self.setDirty()

    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.setDirty()

    def loadPredefinedClasses(self, predefClassesFile):#预分配的目标类型
        if os.path.exists(predefClassesFile) is True:
            with codecs.open(predefClassesFile, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.labelHist is None:
                        self.lablHist = [line]
                    else:
                        self.labelHist.append(line)

    def loadPascalXMLByFilename(self, xmlPath):#加载xml文件
        if self.filePath is None:
            return
        if os.path.isfile(xmlPath) is False:
            return

        tVocParseReader = PascalVocReader(xmlPath)
        shapes = tVocParseReader.getShapes()
        self.loadLabels(shapes)
        self.canvas.verified = tVocParseReader.verified


class Settings(object):
    """Convenience dict-like wrapper around QSettings."""

    def __init__(self, types=None):
        self.data = QSettings()
        self.types = defaultdict(lambda: QVariant, types if types else {})

    def __setitem__(self, key, value):
        t = self.types[key]
        self.data.setValue(key,
                           t(value) if not isinstance(value, t) else value)

    def __getitem__(self, key):
        return self._cast(key, self.data.value(key))

    def get(self, key, default=None):
        return self._cast(key, self.data.value(key, default))

    def _cast(self, key, value):
        # XXX: Very nasty way of converting types to QVariant methods :P
        t = self.types.get(key)
        if t is not None and t != QVariant:
            if t is str:
                return ustr(value)
            else:
                try:
                    method = getattr(QVariant, re.sub(
                        '^Q', 'to', t.__name__, count=1))
                    return method(value)
                except AttributeError as e:
                    # print(e)
                    return value
        return value


def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])


def read(filename, default=None):
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except:
        return default


def get_main_app(argv=[]):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    app = QApplication(argv)
    app.setApplicationName(__appname__)
    app.setWindowIcon(newIcon("app"))
    # Tzutalin 201705+: Accept extra agruments to change predefined class file
    # Usage : labelImg.py image predefClassFile
    win = MainWindow(argv[1] if len(argv) >= 2 else None,
                     argv[2] if len(argv) >= 3 else os.path.join('data', 'predefined_classes.txt'))
    win.show()
    return app, win


def main(argv=[]):
    '''construct main app and run it'''
    app, _win = get_main_app(argv)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main(sys.argv))

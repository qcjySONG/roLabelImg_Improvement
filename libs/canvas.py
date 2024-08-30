
try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

#from PyQt4.QtOpenGL import *
import math
from shape import Shape
from lib import distance
import math
from tools import sin_cos

CURSOR_DEFAULT = Qt.ArrowCursor#设置一个默认的光标样式为标准的箭头样式
CURSOR_POINT = Qt.PointingHandCursor#手形光标
CURSOR_DRAW = Qt.CrossCursor#带有十字线的光标
CURSOR_MOVE = Qt.ClosedHandCursor#闭合的手形光标
CURSOR_GRAB = Qt.OpenHandCursor#开放的手形光标

# class Canvas(QGLWidget):


class Canvas(QWidget):
    # 定义了几个信号，用于在特定情况下发出通知
    zoomRequest = pyqtSignal(int)
    scrollRequest = pyqtSignal(int, int)
    newShape = pyqtSignal()
    selectionChanged = pyqtSignal(bool)
    shapeMoved = pyqtSignal()
    drawingPolygon = pyqtSignal(bool)

    hideRRect = pyqtSignal(bool)
    hideNRect = pyqtSignal(bool)
    status = pyqtSignal(str)

    CREATE, EDIT = list(range(2))#定义0 1 常量

    epsilon = 11.0



    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        # Initialise local state.
        self.mode = self.EDIT#模式 1
        self.shapes = []#形状列表
        self.current = None#当前形状
        self.selectedShape = None  # save the selected shape here 选中的矩形框
        self.selectedShapeCopy = None
        self.lineColor = QColor(0, 0, 255)
        self.line = Shape(line_color=self.lineColor)
        self.prevPoint = QPointF()
        self.offsets = QPointF(), QPointF()#偏移量
        self.scale = 1.0#比例大小
        self.pixmap = QPixmap()#像素图
        self.visible = {}
        self._hideBackround = False
        self.hideBackround = False
        self.hShape = None
        self.hVertex = None
        self._painter = QPainter()
        self._cursor = CURSOR_DEFAULT
        # Menus:
        self.menus = (QMenu(), QMenu())
        # Set widget options.
        self.setMouseTracking(True)#鼠标跟踪
        self.setFocusPolicy(Qt.WheelFocus)#焦点策略
        self.verified = False
        # judge can draw rotate rect
        self.canDrawRotatedRect = True
        self.hideRotated = False
        self.hideNormal = False
        self.canOutOfBounding = False
        self.showCenter = False

    def enterEvent(self, ev):
        self.overrideCursor(self._cursor)#将鼠标光标设置为_cursor

    def leaveEvent(self, ev):#鼠标离开小部件的区域时被调用
        self.restoreCursor()#恢复鼠标光标为默认样式

    def focusOutEvent(self, ev):#小部件失去焦点时被调用
        self.restoreCursor()

    def isVisible(self, shape):#判断指定的形状 shape 是否可见
        return self.visible.get(shape, True)

    def drawing(self):#用于判断当前模式是否为绘制模式
        return self.mode == self.CREATE

    def editing(self):#判断当前模式是否为编辑模式
        return self.mode == self.EDIT

    def setEditing(self, value=True):#设置编辑模式
        self.mode = self.EDIT if value else self.CREATE
        if not value:  # Create
            self.unHighlight()#取消高亮显示
            self.deSelectShape()

    def unHighlight(self):#取消高亮显示
        if self.hShape:
            self.hShape.highlightClear()
        self.hVertex = self.hShape = None

    def selectedVertex(self):#是否选择了某个顶点
        return self.hVertex is not None

    def mouseMoveEvent(self, ev):
        """
        处理鼠标移动事件，根据不同的鼠标操作（左键、右键、无键按下）执行不同的图形操作，如绘制多边形、移动顶点或形状、高亮显示顶点或形状。
        :param ev: 鼠标事件对象，包含鼠标移动时的位置和其他相关信息。
        """
        # 将鼠标事件位置转换为图像坐标
        pos = self.transformPos(ev.pos())
        self.restoreCursor()  # 恢复鼠标光标形状
        # 如果当前正在绘制多边形
        if self.drawing():
            self.overrideCursor(CURSOR_DRAW)  # 替换鼠标光标为绘制形状光标
            if self.current:  # 如果当前有活动的形状
                color = self.lineColor  # 设置线条颜色
                if self.outOfPixmap(pos):  # 如果点击位置超出图像边界
                    # 将点击位置投影到图像边界上
                    pos = self.intersectionPoint(self.current[-1], pos)
                elif len(self.current) > 1 and self.closeEnough(pos, self.current[0]):  # 如果点击位置接近多边形起点
                    # 吸引线条到起点，并改变颜色以提示用户
                    pos = self.current[0]
                    color = self.current.line_color
                    self.overrideCursor(CURSOR_POINT)
                    self.current.highlightVertex(0, Shape.NEAR_VERTEX)
                self.line[1] = pos  # 更新线条的终点位置
                self.line.line_color = color  # 更新线条颜色
                self.repaint()  # 重绘图像
                self.current.highlightClear()  # 清除高亮
                self.status.emit("width is %d, height is %d." % (pos.x()-self.line[0].x(), pos.y()-self.line[0].y()))
            return

        # 如果按下右键，处理形状复制移动操作
        if Qt.RightButton & ev.buttons():
            if self.selectedVertex() and self.selectedShape.isRotated:  # 如果选择了顶点且形状被旋转
                self.boundedRotateShape(pos)  # 限制范围内旋转形状
                self.shapeMoved.emit()  # 发出形状移动信号
                self.repaint()
            self.status.emit("(%d,%d)." % (pos.x(), pos.y()))
            return

        # 如果按下左键，处理形状或顶点移动操作
        if Qt.LeftButton & ev.buttons():
            if self.selectedVertex():  # 如果选择了顶点
                self.boundedMoveVertex(pos)  # 限制范围内移动顶点
                self.shapeMoved.emit()  # 发出形状移动信号
                self.repaint()
            elif self.selectedShape and self.prevPoint:  # 如果选择了形状
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShape(self.selectedShape, pos)  # 限制范围内移动形状
                self.shapeMoved.emit()  # 发出形状移动信号
                self.repaint()
                self.status.emit("(%d,%d)." % (pos.x(), pos.y()))
            return

        # 鼠标悬停在画布上，处理高亮显示形状或顶点
        self.setToolTip("Image")
        for shape in reversed([s for s in self.shapes if self.isVisible(s)]):
            # 首先尝试寻找接近的顶点进行高亮
            index = shape.nearestVertex(pos, self.epsilon)
            if index is not None:
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.hVertex, self.hShape = index, shape
                shape.highlightVertex(index, shape.MOVE_VERTEX)  # 高亮显示顶点
                self.overrideCursor(CURSOR_POINT)
                self.update()
                break
            elif shape.containsPoint(pos):  # 如果不在顶点上，则检查是否在形状内部
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.hVertex, self.hShape = None, shape
                self.overrideCursor(CURSOR_GRAB)
                self.update()
                break
        else:  # 如果没有找到任何形状或顶点进行高亮
            if self.hShape:
                self.hShape.highlightClear()
                self.update()
            self.hVertex, self.hShape = None, None
            self.status.emit("(%d,%d)." % (pos.x(), pos.y()))
        

    def mousePressEvent(self, ev):
        pos = self.transformPos(ev.pos())## 将鼠标的位置从窗口坐标转换为Canvas坐标
        # print('sldkfj %d %d' % (pos.x(), pos.y()))
        #检查按下的是哪个鼠标按钮
        if ev.button() == Qt.LeftButton:#left
            self.hideBackroundShapes(True)# 隐藏背景形状
            if self.drawing():# 如果是绘制模式，处理绘制逻辑
                self.handleDrawing(pos)
            else:#不在绘制模式
                self.selectShapePoint(pos) # 选择一个形状的点
                self.prevPoint = pos# 记录上一个点的位置
                self.repaint() #重绘Canvas
        elif ev.button() == Qt.RightButton and self.editing():#右键，并且当前处于编辑模式
            self.selectShapePoint(pos)#选择一个形状的点
            self.hideBackroundShapes(True)#隐藏背景形状
            # if self.selectedShape is not None:
            #     print('point is (%d, %d)' % (pos.x(), pos.y()))
            #     self.selectedShape.rotate(10)

            self.prevPoint = pos
            self.repaint()

    def mouseReleaseEvent(self, ev):  #鼠标释放事件
        self.hideBackroundShapes(False)      #不再隐藏背景形状
        if ev.button() == Qt.RightButton and not self.selectedVertex():  #右，没有选中顶点
            menu = self.menus[bool(self.selectedShapeCopy)]#根据是否有选中的形状副本显示相应的菜单
            self.restoreCursor()## 恢复光标样式
            ## 如果菜单没有在鼠标位置执行，并且存在选中的形状副本
            if not menu.exec_(self.mapToGlobal(ev.pos()))\
               and self.selectedShapeCopy:
                # Cancel the move by deleting the shadow copy.
                self.selectedShapeCopy = None
                self.repaint()
        elif ev.button() == Qt.LeftButton and self.selectedShape:
            self.overrideCursor(CURSOR_GRAB)
        elif ev.button() == Qt.LeftButton:
            pos = self.transformPos(ev.pos())
            if self.drawing():
                self.handleDrawing(pos)

    def endMove(self, copy=False):#结束移动操作
        assert self.selectedShape and self.selectedShapeCopy#确保有一个选中的形状和一个选中形状的副本
        shape = self.selectedShapeCopy# 获取选中形状的副本
        #del shape.fill_color
        #del shape.line_color
        if copy:## 如果copy为True，则执行复制操作
            self.shapes.append(shape)## 将形状副本添加到形状列表中
            self.selectedShape.selected = False # 取消原选中形状的选中状态
            self.selectedShape = shape# 将新复制的形状设置为当前选中形状
            self.repaint()# 重绘界面以显示新形状
        else:# 如果copy为False，则更新原选中形状的位置为形状副本的位置
            self.selectedShape.points = [p for p in shape.points]
        self.selectedShapeCopy = None# 清除选中的形状副本，因为移动或复制操作已经结束

    def hideBackroundShapes(self, value):# 根据提供的值来隐藏或显示背景形状
        # print("hideBackroundShapes")
        self.hideBackround = value # 设置隐藏背景形状的布尔值
        if self.selectedShape:# 如果存在选中的形状
            # 只隐藏其他形状，当有一个当前选中的形状时。
            # 否则，用户将无法选择形状。
            self.setHiding(True)
            self.repaint()

    def handleDrawing(self, pos):#绘制逻辑
        #outOfPixmap(pos):#检查新的顶点位置是否超出边界
        if self.current and self.current.reachMaxPoints() is False:#如果当前存在绘图操作且未达到最大点数限制
            initPos = self.current[0]# 获取绘图开始的初始位置
            # 获取初始位置的最小x和y坐标
            minX = initPos.x()
            minY = initPos.y()
            # 获取目标位置
            targetPos = self.line[1]
            # 获取目标位置的最大x和y坐标
            maxX = targetPos.x()#float
            maxY = targetPos.y()
            point1=(initPos.x(),initPos.y())
            point2=(targetPos.x(),targetPos.y())
            #print(point1,type(point1),type(point1[0]))
            '''
            计算两点间相对偏移量-(minx,miny)---->(maxx,maxy)
            左偏则为右向矩形，右偏则为左向矩形
            '''
            add_x=50#默认水平方向加100个距离

            roate=1 #0左1右，默认左偏
            print(maxX,maxY,minX,minY)

            if (minX>maxX and minY<maxY) or (minX<maxX and minY>maxY):
                roate=0
            print("roate:",roate)
            if roate==0:#左偏
                sin,cos=sin_cos.calculate_sin_cos(point1,point2)#与水平边的夹角
                #求其余角的sin，cos
                Ysin,Ycos=cos,sin
                '''tan=对边比邻边  tanα=sinα/cosα'''
                Ytan=Ysin/Ycos
                dis=sin_cos.calculate_distance(point1,point2)
                add_x=dis*0.5
                add_h=add_x*Ytan
                #超出边界框则反向画，让用户自行移动
                #if self.outOfPixmap(QPointF(minX+add_x, minY+add_h)) or self.outOfPixmap(QPointF(maxX+add_x, minY+add_h)):
                #    self.current.addPoint(QPointF(minX + add_x, minY - add_h))  # 右上角
                #    self.current.addPoint(QPointF(maxX + add_x, maxY - add_h))  # 右下角
                #else:
                self.current.addPoint(QPointF(minX+add_x, minY+add_h))  # 右上角
                self.current.addPoint(QPointF(maxX+add_x,maxY+add_h))  # 右下角
                self.current.addPoint(targetPos)  # 左下角
                self.current.addPoint(initPos)  # 左上角
                theta = math.atan2(Ysin,Ycos)
                print("theta:",theta)
                direction=theta
            else:#右偏
                sin,cos=sin_cos.calculate_sin_cos(point1,point2)#与水平边的夹角
                Ysin,Ycos=cos,sin
                Ytan=Ysin/Ycos
                dis=sin_cos.calculate_distance(point1,point2)
                add_x=dis*0.5
                add_h=add_x*Ytan
                print("右偏：",Ytan)

                self.current.addPoint(QPointF(minX+add_x,minY-add_h))# 右上角
                self.current.addPoint(QPointF(maxX + add_x, maxY - add_h))  # 右下角


                self.current.addPoint(targetPos)  # 左下角
                self.current.addPoint(initPos)  # 左上角
                theta = math.atan2(Ysin, Ycos)
                direction=(2 * math.pi)-theta
            # 根据初始位置和目标位置添加四个点到当前绘图中
            # 这四个点构成了一个矩形，初始位置和目标位置是对角线的顶点
            self.line[0] = self.current[-1]# 更新线的起始点为当前绘图的最后一个点
            # 如果当前绘图是封闭的（即起点和终点重合），则完成绘图
            if self.current.isClosed():
                self.finalise(direction)
        # 如果鼠标当前位置不在绘图区域之外
        elif not self.outOfPixmap(pos):
            # 开始一个新的绘图操作
            self.current = Shape()
            self.current.addPoint(pos)
            self.line.points = [pos, pos]
            self.setHiding()
            self.drawingPolygon.emit(True)
            self.update()


    def setHiding(self, enable=True):# 设置隐藏背景的形状
        # 如果enable为True，则使用self.hideBackround的值，否则使用False
        self._hideBackround = self.hideBackround if enable else False

    def canCloseShape(self):# 判断是否可以关闭形状
        # 如果正在绘图，存在当前形状，且当前形状点数大于2，则返回True
        return self.drawing() and self.current and len(self.current) > 2

    def mouseDoubleClickEvent(self, ev):# 鼠标双击事件处理
        # 由于鼠标按下事件处理器会额外添加一个点,所以这里需要至少4个点才能形成一个可关闭的形状。
        # 如果可以关闭形状且当前形状点数大于3（实际点数应为4）
        if self.canCloseShape() and len(self.current) > 3:
            # 移除最后一个点
            self.current.popPoint()
            self.finalise()
    # 选择形状
    def selectShape(self, shape):
        # 取消选择其他形状
        self.deSelectShape()
        # 将传入的形状设置为选中状态
        shape.selected = True
        # 将选中的形状设置为当前选中形状
        self.selectedShape = shape
        # 设置隐藏其他形状的逻辑
        self.setHiding()
        # 发出形状选择改变的信号
        self.selectionChanged.emit(True)
        # 更新绘图界面
        self.update()

    def selectShapePoint(self, point):
        """Select the first shape created which contains this point."""
        """选择包含该点的第一个创建的形状。"""
        self.deSelectShape()## 取消选择当前选中的形状
        if self.selectedVertex():  # 如果已经有顶点被标记为待选择状态
            index, shape = self.hVertex, self.hShape# 获取待选择顶点的索引和所在形状
            shape.highlightVertex(index, shape.MOVE_VERTEX)# 对该顶点进行高亮显示，表示可以进行移动操作
            # 将形状设置为选中状态
            shape.selected = True
            # 更新选中形状
            self.selectedShape = shape
            # 计算偏移量
            self.calculateOffsets(shape, point)
            self.setHiding()# 设置隐藏其他形状的逻辑
            self.selectionChanged.emit(True) # 发出形状选择改变的信号
            return# 如果已经有顶点被选中，则直接返回，不再继续查找

        for shape in reversed(self.shapes):# 反向遍历所有形状（从最新创建的形状开始）
            if self.isVisible(shape) and shape.containsPoint(point):# 如果形状是可见的，并且包含给定的点
                shape.selected = True# 将形状设置为选中状态
                self.selectedShape = shape# 更新选中形状
                self.calculateOffsets(shape, point)# 计算偏移量
                self.setHiding()
                self.selectionChanged.emit(True) # 发出形状选择改变的信号
                return# 找到包含该点的形状后，直接返回，不再继续查找

    def calculateOffsets(self, shape, point):
        rect = shape.boundingRect()## 获取形状的边界矩形
        # 计算边界矩形的左上角相对于点的偏移量
        x1 = rect.x() - point.x()
        y1 = rect.y() - point.y()
        # 计算边界矩形的右下角相对于点的偏移量
        x2 = (rect.x() + rect.width()) - point.x()
        y2 = (rect.y() + rect.height()) - point.y()
        # 将计算得到的偏移量存储为两个 QPointF 对象，并赋值给 self.offsets
        self.offsets = QPointF(x1, y1), QPointF(x2, y2)

    def boundedMoveVertex(self, pos):#移动顶点函数——放大缩小函数
        '''
        左上0 右上1 右下2 左下3
        pos: 新的顶点位置 type(pos))QPointF
        在限制条件下移动形状的一个顶点。具体地，它考虑了一个顶点的新位置（pos），
        并尝试更新形状以反映这个新的位置，同时还确保形状的其他部分不会超出指定的边界
        '''
        index, shape = self.hVertex, self.hShape#获取要移动的顶点和所在的形状
        point = shape[index]#获取当前要移动的顶点的坐标
        if not self.canOutOfBounding and self.outOfPixmap(pos):#检查新的顶点位置是否超出边界
            return
            # pos = self.intersectionPoint(point, pos)
        # print("index is %d" % index)
        sindex = (index + 2) % 4 #与当前顶点相邻的下一个顶点的索引
        # 获取形状的其他三个顶点
        p2,p3,p4 = self.getAdjointPoints(shape.direction, shape[sindex], pos, index)
        pcenter = (pos+p3)/2#检查形状的中心点是否超出边界
        '''即使允许顶点超出边界（self.canOutOfBounding 为 True），也要检查形状的中心点是否超出了边界。'''
        if self.canOutOfBounding and self.outOfPixmap(pcenter):
            return
        # if one pixal out of map , do nothing
        #检查移动顶点后形状的其他部分是否超出边界
        if not self.canOutOfBounding and (self.outOfPixmap(p2) or
            self.outOfPixmap(p3) or
            self.outOfPixmap(p4)):
                return

        # move 4 pixal one by one
        # 移动顶点并更新形状
        shape.moveVertexBy(index, pos - point)#index 和 offset
        lindex = (index + 1) % 4
        rindex = (index + 3) % 4
        shape[lindex] = p2
        # shape[sindex] = p3
        shape[rindex] = p4
        shape.close()#确保形状是一个闭合的四边形
        # calculate the height and weight, and show it
        w = math.sqrt((p4.x()-p3.x()) ** 2 + (p4.y()-p3.y()) ** 2)
        h = math.sqrt((p3.x()-p2.x()) ** 2 + (p3.y()-p2.y()) ** 2)
        self.status.emit("width is %d, height is %d." % (w,h))#右下角的提醒

    
    def getAdjointPoints(self, theta, p3, p1, index):#计算 四边形 中与指定顶点相邻的其他三个顶点的位置
        '''
        theta: 四边形的方向，以弧度表示。
        p3: 四边形的一个顶点位置。
        p1: 与 p3 相邻的另一个顶点位置。
        index: 当前处理的顶点的索引。
        '''
        # p3 = center
        # p3 = 2*center-p1
        a1 = math.tan(theta)#斜率
        if (a1 == 0):#如果 a1 为 0，表示四边形是水平的
            if index % 2 == 0:
                p2 = QPointF(p3.x(), p1.y())
                p4 = QPointF(p1.x(), p3.y())
            else:            
                p4 = QPointF(p3.x(), p1.y())
                p2 = QPointF(p1.x(), p3.y())
        else:    
            a3 = a1
            a2 = - 1/a1
            a4 = - 1/a1
            b1 = p1.y() - a1 * p1.x()
            b2 = p1.y() - a2 * p1.x()
            b3 = p3.y() - a1 * p3.x()
            b4 = p3.y() - a2 * p3.x()

            if index % 2 == 0:
                p2 = self.getCrossPoint(a1,b1,a4,b4)
                p4 = self.getCrossPoint(a2,b2,a3,b3)
            else:            
                p4 = self.getCrossPoint(a1,b1,a4,b4)
                p2 = self.getCrossPoint(a2,b2,a3,b3)

        return p2,p3,p4

    def getCrossPoint(self,a1,b1,a2,b2):#计算两条直线的交点
        '''
        y = a1 * x + b1 和 y = a2 * x + b2 的交点
        '''
        x = (b2-b1)/(a1-a2)
        y = (a1*b2 - a2*b1)/(a1-a2)
        return QPointF(x,y)

    def boundedRotateShape(self, pos):
        # 判断某个顶点是否超出像素范围
        # judge if some vertex is out of pixma
        index, shape = self.hVertex, self.hShape
        point = shape[index]

        angle = self.getAngle(shape.center,pos,point)
        # for i, p in enumerate(shape.points):
        #     if self.outOfPixmap(shape.rotatePoint(p,angle)):
        #         # print("out of pixmap")
        #         return
        if not self.rotateOutOfBound(angle):
            shape.rotate(angle)
            self.prevPoint = pos

    def getAngle(self, center, p1, p2):
        '''
        center：中心点，一个 QPointF 对象，表示形状（如矩形）的中心点位置。
        p1：一个 QPointF 对象，表示形状上的一个顶点。
        p2：另一个 QPointF 对象，表示形状上的另一个顶点或用于计算夹角的另一个点。

        计算从点 p1 到点 p2 相对于某个中心点 center 的夹角。
        这个夹角是以弧度表示的，其值范围在 -π 到 π 之间
        '''
        dx1 = p1.x() - center.x();
        dy1 = p1.y() - center.y();

        dx2 = p2.x() - center.x();
        dy2 = p2.y() - center.y();

        c = math.sqrt(dx1*dx1 + dy1*dy1) * math.sqrt(dx2*dx2 + dy2*dy2)
        if c == 0: return 0
        y = (dx1*dx2+dy1*dy2)/c
        if y>1: return 0
        angle = math.acos(y)

        if (dx1*dy2-dx2*dy1)>0:   
            return angle
        else:
            return -angle

    def boundedMoveShape(self, shape, pos):  # 定义一个方法，用于在有边界限制的情况下移动形状
        # 如果形状已经旋转，并且允许形状超出边界
        if shape.isRotated and self.canOutOfBounding:
            c = shape.center  # 获取形状的中心点
            dp = pos - self.prevPoint  # 计算从上一个点到新位置的位移
            dc = c + dp  # 计算移动后形状的中心位置

            # 如果新的中心位置在x轴方向上小于0，调整位移，确保形状不超出左边界
            if dc.x() < 0:
                dp -= QPointF(min(0, dc.x()), 0)
                # 如果新的中心位置在y轴方向上小于0，调整位移，确保形状不超出上边界
            if dc.y() < 0:
                dp -= QPointF(0, min(0, dc.y()))
                # 如果新的中心位置在x轴方向上大于等于像素图的宽度，调整位移，确保形状不超出右边界
            if dc.x() >= self.pixmap.width():
                dp += QPointF(min(0, self.pixmap.width() - 1 - dc.x()), 0)
                # 如果新的中心位置在y轴方向上大于等于像素图的高度，调整位移，确保形状不超出下边界
            if dc.y() >= self.pixmap.height():
                dp += QPointF(0, min(0, self.pixmap.height() - 1 - dc.y()))

        else:  # 如果形状没有旋转，或者不允许形状超出边界
            # 如果新位置超出像素图边界，则不需要移动形状
            if self.outOfPixmap(pos):
                return False

                # 计算形状的一个偏移位置
            o1 = pos + self.offsets[0]
            # 如果这个偏移位置超出像素图边界，调整新位置pos
            if self.outOfPixmap(o1):
                pos -= QPointF(min(0, o1.x()), min(0, o1.y()))

                # 计算形状的另一个偏移位置
            o2 = pos + self.offsets[1]
            # 如果这个偏移位置超出像素图边界，调整新位置pos
            if self.outOfPixmap(o2):
                pos += QPointF(min(0, self.pixmap.width() - 1 - o2.x()),
                               min(0, self.pixmap.height() - 1 - o2.y()))

                # 计算从上一个点到新位置的位移
            dp = pos - self.prevPoint
        # 注释：下一行代码追踪光标相对于形状的新位置，但可能导致光标在靠近边界时变得“不稳定”，
        # 并且出于某种原因允许光标超出形状区域。此部分代码被禁用，需要修复。
        # self.calculateOffsets(self.selectedShape, pos)
        # 如果位移不为零，则移动形状，更新上一个点的位置，关闭形状（确保形状完整性），并返回True表示移动成功
        if dp:
            shape.moveBy(dp)
            self.prevPoint = pos
            shape.close()
            return True
            # 如果没有位移，则返回False表示形状没有移动
        return False


    def boundedMoveShape2(self, shape, pos):
        if self.outOfPixmap(pos):
            return False  # No need to move
        o1 = pos + self.offsets[0]
        if self.outOfPixmap(o1):
            pos -= QPointF(min(0, o1.x()), min(0, o1.y()))
        o2 = pos + self.offsets[1]
        if self.outOfPixmap(o2):
            pos += QPointF(min(0, self.pixmap.width() - o2.x()),
                           min(0, self.pixmap.height() - o2.y()))
        # The next line tracks the new position of the cursor
        # relative to the shape, but also results in making it
        # a bit "shaky" when nearing the border and allows it to
        # go outside of the shape's area for some reason. XXX
        #self.calculateOffsets(self.selectedShape, pos)
        dp = pos - self.prevPoint
        if dp:
            shape.moveBy(dp)
            self.prevPoint = pos
            shape.close()
            return True
        return False

    def deSelectShape(self):# 取消选中的形状
        if self.selectedShape:
            self.selectedShape.selected = False
            self.selectedShape = None
            self.setHiding(False)
            self.selectionChanged.emit(False)
            self.update()

    def deleteSelected(self):#删除所选形状
        if self.selectedShape:
            shape = self.selectedShape
            self.shapes.remove(self.selectedShape)
            self.selectedShape = None
            self.update()
            return shape

    def copySelectedShape(self):#复制所选形状
        if self.selectedShape:
            shape = self.selectedShape.copy()
            self.deSelectShape()
            self.shapes.append(shape)
            shape.selected = True
            self.selectedShape = shape
            self.boundedShiftShape(shape)
            return shape

    def boundedShiftShape(self, shape):#有限的边界内移动形状
        # 尝试在一个方向上移动形状，如果失败，则尝试在另一个方向上移动。
        # 如果两个方向都失败，则放弃移动。
        point = shape[0]
        offset = QPointF(2.0, 2.0)
        self.calculateOffsets(shape, point)
        self.prevPoint = point
        if not self.boundedMoveShape(shape, point - offset):
            self.boundedMoveShape(shape, point + offset)

    def paintEvent(self, event):#绘制事件,删除绘制辅助框相关
        '''
        这个函数是用来绘制Canvas中的内容的。函数首先检查是否有背景图片，如果没有则调用父类的paintEvent方法。
        接着使用_painter开始绘制，并设置了一些渲染参数，如抗锯齿、高质量抗锯齿和平滑像素变换。

        接着进行缩放和平移操作，将绘制的内容放置在中心位置。然后绘制背景图片和所有形状，
        根据形状的选中状态和是否隐藏背景来确定是否绘制形状。如果形状被选中或未隐藏背景且可见，
        且未被隐藏旋转或未旋转且未隐藏正常，则绘制形状，否则绘制正常中心点。

        接着绘制当前形状和线条，以及选中的形状的副本。如果当前存在形状且线条长度为2，
        则绘制矩形和矩形的对角线。最后根据验证状态设置背景颜色，并结束绘制。
        '''
        if not self.pixmap:
            return super(Canvas, self).paintEvent(event)  # 如果没有背景图片，则调用父类的paintEvent方法

        p = self._painter
        p.begin(self)  # 开始绘制
        p.setRenderHint(QPainter.Antialiasing)  # 设置抗锯齿渲染
        p.setRenderHint(QPainter.HighQualityAntialiasing)  # 设置高质量抗锯齿渲染
        p.setRenderHint(QPainter.SmoothPixmapTransform)  # 设置平滑像素变换

        p.scale(self.scale, self.scale)  # 缩放
        p.translate(self.offsetToCenter())  # 平移至中心

        p.drawPixmap(0, 0, self.pixmap)  # 绘制背景图片
        Shape.scale = self.scale
        for shape in self.shapes:
            if (shape.selected or not self._hideBackround) and self.isVisible(shape):  # 如果形状被选中或未隐藏背景且可见
                if (shape.isRotated and not self.hideRotated) or (
                        not shape.isRotated and not self.hideNormal):  # 如果形状被旋转且未隐藏旋转或未旋转且未隐藏正常
                    shape.fill = shape.selected or shape == self.hShape
                    shape.paint(p)  # 绘制形状
                elif self.showCenter:  # 如果显示中心点
                    shape.fill = shape.selected or shape == self.hShape
                    shape.paintNormalCenter(p)  # 绘制正常中心点

        if self.current:
            self.current.paint(p)  # 绘制当前形状
            self.line.paint(p)  # 绘制线条
        if self.selectedShapeCopy:
            self.selectedShapeCopy.paint(p)  # 绘制选中的形状的副本

        # 绘制矩形
        if self.current is not None and len(self.line) == 2:
            leftTop = self.line[0]
            rightBottom = self.line[1]
            rectWidth = rightBottom.x() - leftTop.x()
            rectHeight = rightBottom.y() - leftTop.y()
            color = QColor(0, 220, 0)
            p.setPen(color)
            brush = QBrush(Qt.BDiagPattern)
            p.setBrush(brush)
            #p.drawRect(leftTop.x(), leftTop.y(), rectWidth, rectHeight)
            # 绘制矩形的对角线
            #p.setPen(self.lineColor)
            #p.drawLine(leftTop.x(), rightBottom.y(), rightBottom.x(), leftTop.y())

        self.setAutoFillBackground(True)
        if self.verified:
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(184, 239, 38, 128))
            self.setPalette(pal)
        else:
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(232, 232, 232, 255))
            self.setPalette(pal)

        p.end()  # 结束绘制

    def transformPos(self, point):
        """Convert from widget-logical coordinates to painter-logical coordinates."""
        '''将从窗口部件（widget）逻辑坐标转换为绘制器（painter）逻辑坐标'''
        return point / self.scale - self.offsetToCenter()

    def offsetToCenter(self):
        '''
        从窗口部件的中心点到其背景图片中心点的偏移量这个偏移量用于确保背景图片在窗口部件中居中显示，
        即使窗口部件的大小发生变化或者图片大小与窗口部件大小不匹配
        '''
        s = self.scale# 获取当前的缩放比例
        area = super(Canvas, self).size()# 获取窗口部件的大小
        w, h = self.pixmap.width() * s, self.pixmap.height() * s # 计算缩放后的背景图片大小
        aw, ah = area.width(), area.height()# 获取窗口部件的宽度和高度
        # 计算水平方向上的偏移量
        # 如果窗口部件的宽度大于图片宽度，则计算偏移量使图片水平居中
        # 否则，偏移量为0，即图片靠左对齐
        x = (aw - w) / (2 * s) if aw > w else 0
        # 计算垂直方向上的偏移量
        # 如果窗口部件的高度大于图片高度，则计算偏移量使图片垂直居中
        # 否则，偏移量为0，即图片靠上对齐
        y = (ah - h) / (2 * s) if ah > h else 0
        return QPointF(x, y)# 返回一个QPointF对象，表示水平和垂直方向上的偏移量

    def outOfPixmap(self, p):
        #如果点 p 在 pixmap 的边界内或上，函数返回 False
        #检查一个给定的点 p 是否在背景图片（pixmap）的边界之外
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() < w and 0 <= p.y() < h)

    def finalise(self,direction=None):
        #用于结束当前的绘图操作，清理相关资源，并准备开始新的绘图。
        assert self.current#确保当前有一个有效的绘图对象
        self.current.isRotated = self.canDrawRotatedRect#设置当前绘图对象的 isRotated 属性
        self.current.direction = direction
        # print(self.canDrawRotatedRect)
        self.current.close()#关闭或完成当前绘图对象
        self.shapes.append(self.current)#将当前绘图对象添加到 shapes 列表中，可能是为了保存所有绘制的形状
        self.current = None
        self.setHiding(False)
        self.newShape.emit()
        self.update()

    def closeEnough(self, p1, p2):
        '''判断两个点 p1 和 p2 是否足够接近的函数'''
        #d = distance(p1 - p2)
        #m = (p1-p2).manhattanLength()
        # print "d %.2f, m %d, %.2f" % (d, m, d - m)
        return distance(p1 - p2) < self.epsilon

    def intersectionPoint(self, p1, p2):
        '''# 定义intersectionPoint方法，接收两个参数p1和p2，分别代表线段的两个端点'''
        # 遍历图片的每条边界线（按顺时针方向），
        # 找到与当前线段相交的边界线。
        size = self.pixmap.size()# 获取图片的尺寸
        # 定义图片四个边界点的坐标，分别是左上角、右上角、右下角、左下角
        points = [(0, 0),
                  (size.width(), 0),
                  (size.width(), size.height()),
                  (0, size.height())]
        # 获取线段p1和p2的坐标值
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        # 调用self.intersectingEdges方法计算线段p1和p2与图片边界线的交点，
        d, i, (x, y) = min(self.intersectingEdges((x1, y1), (x2, y2), points))
        # 获取相交边界线的两个端点坐标
        x3, y3 = points[i]
        x4, y4 = points[(i + 1) % 4]
        if (x, y) == (x1, y1): # 如果计算出的交点坐标与线段p1的起点坐标相同，
            # 需要处理这种特殊情况，因为这意味着线段p1实际上是从边界线上的一点开始的。
            if x3 == x4:
                return QPointF(x3, min(max(0, y2), max(y3, y4)))
            else:  # y3 == y4
                return QPointF(min(max(0, x2), max(x3, x4)), y3)
        return QPointF(x, y)

    def intersectingEdges(self, x1y1, x2y2, points):
        """
        对于由 `points` 形成的每条边，如果与用户线段 `(x1,y1) - (x2,y2)` 有交点，则计算并返回该交点。
        同时返回线段终点 `(x2,y2)` 到边中点的距离及其索引，以便选择最近的交点。
        """
        x1, y1 = x1y1# 解包起点坐标
        x2, y2 = x2y2# 解包起点坐标
        for i in range(4):# 遍历所有四条边界线
            x3, y3 = points[i]# 当前边界线的起点坐标
            x4, y4 = points[(i + 1) % 4]# 下一条边界线的起点坐标，通过取模运算实现循环
            # 计算判别式（denominator），用于判断线段和边是否相交
            denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
            # 计算分子 nua 和 nub
            nua = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
            nub = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
            if denom == 0:# 如果判别式为零，则线段与边要么重合，要么平行
                # This covers two cases:
                #   nua == nub == 0: Coincident
                #   otherwise: Parallel
                continue# 跳过此次循环，处理下一条边
            ua, ub = nua / denom, nub / denom# 计算交点参数 ua 和 ub
            if 0 <= ua <= 1 and 0 <= ub <= 1:
                x = x1 + ua * (x2 - x1)
                y = y1 + ua * (y2 - y1)
                m = QPointF((x3 + x4) / 2, (y3 + y4) / 2)
                d = distance(m - QPointF(x2, y2))
                print("return=",d,i,(x,y))
                yield d, i, (x, y)

    # These two, along with a call to adjustSize are required for the
    # scroll area.
    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    def wheelEvent(self, ev):#鼠标滚轮事件
        qt_version = 4 if hasattr(ev, "delta") else 5
        if qt_version == 4:
            if ev.orientation() == Qt.Vertical:
                v_delta = ev.delta()
                h_delta = 0
            else:
                h_delta = ev.delta()
                v_delta = 0
        else:
            delta = ev.angleDelta()
            h_delta = delta.x()
            v_delta = delta.y()
        # print('scrolling vdelta is %d, hdelta is %d' % (v_delta, h_delta))
        mods = ev.modifiers()
        if Qt.ControlModifier == int(mods) and v_delta:
            self.zoomRequest.emit(v_delta)
        else:
            v_delta and self.scrollRequest.emit(v_delta, Qt.Vertical)
            h_delta and self.scrollRequest.emit(h_delta, Qt.Horizontal)
        ev.accept()

    def keyPressEvent(self, ev):#键盘响应
        key = ev.key()
        
        if key == Qt.Key_Escape and self.current:
            print('ESC press')
            self.current = None
            self.drawingPolygon.emit(False)
            self.update()
        elif key == Qt.Key_Return and self.canCloseShape():
            self.finalise()
        elif key == Qt.Key_Left and self.selectedShape:
            self.moveOnePixel('Left')
        elif key == Qt.Key_Right and self.selectedShape:
            self.moveOnePixel('Right')
        elif key == Qt.Key_Up and self.selectedShape:
            self.moveOnePixel('Up')
        elif key == Qt.Key_Down and self.selectedShape:
            self.moveOnePixel('Down')
        elif key == Qt.Key_Z and self.selectedShape and\
             self.selectedShape.isRotated and not self.rotateOutOfBound(0.1):
            self.selectedShape.rotate(0.1)
            self.shapeMoved.emit() 
            self.update()  
        elif key == Qt.Key_X and self.selectedShape and\
             self.selectedShape.isRotated and not self.rotateOutOfBound(0.01):
            self.selectedShape.rotate(0.01) 
            self.shapeMoved.emit()
            self.update()  
        elif key == Qt.Key_C and self.selectedShape and\
             self.selectedShape.isRotated and not self.rotateOutOfBound(-0.01):
            self.selectedShape.rotate(-0.01) 
            self.shapeMoved.emit()
            self.update()  
        elif key == Qt.Key_V and self.selectedShape and\
             self.selectedShape.isRotated and not self.rotateOutOfBound(-0.1):
            self.selectedShape.rotate(-0.1)
            self.shapeMoved.emit()
            self.update()
        elif key == Qt.Key_R:
            self.hideRotated = not self.hideRotated
            self.hideRRect.emit(self.hideRotated)
            self.update()
        elif key == Qt.Key_N:
            self.hideNormal = not self.hideNormal
            self.hideNRect.emit(self.hideNormal)
            self.update()
        elif key == Qt.Key_O:
            self.canOutOfBounding = not self.canOutOfBounding
        elif key == Qt.Key_B:
            self.showCenter = not self.showCenter
            self.update()


    def rotateOutOfBound(self, angle):
        '''
        检查当某个形状（self.selectedShape）旋转指定的角度（angle）后，其任何点是否会超出某个边界
        '''
        if self.canOutOfBounding:
            return False
        for i, p in enumerate(self.selectedShape.points):
            if self.outOfPixmap(self.selectedShape.rotatePoint(p,angle)):
                return True
        return False

    def moveOnePixel(self, direction):
        # print(self.selectedShape.points)
        if direction == 'Left' and not self.moveOutOfBound(QPointF(-1.0, 0)):
            # print("move Left one pixel")
            self.selectedShape.points[0] += QPointF(-1.0, 0)
            self.selectedShape.points[1] += QPointF(-1.0, 0)
            self.selectedShape.points[2] += QPointF(-1.0, 0)
            self.selectedShape.points[3] += QPointF(-1.0, 0)
            self.selectedShape.center += QPointF(-1.0, 0)
        elif direction == 'Right' and not self.moveOutOfBound(QPointF(1.0, 0)):
            # print("move Right one pixel")
            self.selectedShape.points[0] += QPointF(1.0, 0)
            self.selectedShape.points[1] += QPointF(1.0, 0)
            self.selectedShape.points[2] += QPointF(1.0, 0)
            self.selectedShape.points[3] += QPointF(1.0, 0)
            self.selectedShape.center += QPointF(1.0, 0)
        elif direction == 'Up' and not self.moveOutOfBound(QPointF(0, -1.0)):
            # print("move Up one pixel")
            self.selectedShape.points[0] += QPointF(0, -1.0)
            self.selectedShape.points[1] += QPointF(0, -1.0)
            self.selectedShape.points[2] += QPointF(0, -1.0)
            self.selectedShape.points[3] += QPointF(0, -1.0)
            self.selectedShape.center += QPointF(0, -1.0)
        elif direction == 'Down' and not self.moveOutOfBound(QPointF(0, 1.0)):
            # print("move Down one pixel")
            self.selectedShape.points[0] += QPointF(0, 1.0)
            self.selectedShape.points[1] += QPointF(0, 1.0)
            self.selectedShape.points[2] += QPointF(0, 1.0)
            self.selectedShape.points[3] += QPointF(0, 1.0)
            self.selectedShape.center += QPointF(0, 1.0)
        self.shapeMoved.emit()
        self.repaint()

    def moveOutOfBound(self, step):#简单平移考虑，任何点是否会超出某个边界
        points = [p1+p2 for p1, p2 in zip(self.selectedShape.points, [step]*4)]
        return True in map(self.outOfPixmap, points)

    def setLastLabel(self, text):
        assert text#确保传入的 text 参数不是 None
        self.shapes[-1].label = text
        return self.shapes[-1]

    def undoLastLine(self):
        #撤销最后一个绘制的形状或线条
        assert self.shapes
        self.current = self.shapes.pop()#出栈
        self.current.setOpen()#设置当前形状的状态为开放
        self.line.points = [self.current[-1], self.current[0]]
        self.drawingPolygon.emit(True)

    def resetAllLines(self):
        #重置所有已绘制的线条和形状
        assert self.shapes
        self.current = self.shapes.pop()
        self.current.setOpen()
        self.line.points = [self.current[-1], self.current[0]]
        self.drawingPolygon.emit(True)
        self.current = None
        self.drawingPolygon.emit(False)
        self.update()

    def loadPixmap(self, pixmap):
        self.pixmap = pixmap
        self.shapes = []
        self.repaint()

    def loadShapes(self, shapes):
        self.shapes = list(shapes)
        self.current = None
        self.repaint()

    def setShapeVisible(self, shape, value):
        self.visible[shape] = value
        self.repaint()

    def overrideCursor(self, cursor):
        self.restoreCursor()
        self._cursor = cursor
        QApplication.setOverrideCursor(cursor)

    def restoreCursor(self):
        QApplication.restoreOverrideCursor()

    def resetState(self):
        self.restoreCursor()
        self.pixmap = None
        self.update()

#!/usr/bin/python
# -*- coding: utf-8 -*-


try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from lib import distance
import math

DEFAULT_LINE_COLOR = QColor(0, 255, 0, 128)#默认线条颜色，半透明的绿色
DEFAULT_FILL_COLOR = QColor(255, 0, 0, 128)#默认填充颜色，半透明的红色
DEFAULT_SELECT_LINE_COLOR = QColor(255, 255, 255)#默认选中状态下的线条颜色，白色
DEFAULT_SELECT_FILL_COLOR = QColor(0, 128, 255, 155)#默认选中状态下的填充颜色，半透明的蓝色
DEFAULT_VERTEX_FILL_COLOR = QColor(0, 255, 0, 255)#默认顶点填充颜色，不透明的绿色
DEFAULT_HVERTEX_FILL_COLOR = QColor(255, 0, 0)#默认高亮顶点填充颜色，不透明的红色


class Shape(object):
    P_SQUARE, P_ROUND = range(2)#方形和圆形
    MOVE_VERTEX, NEAR_VERTEX = range(2)#点击或悬停在顶点上
    # The following class variables influence the drawing
    # of _all_ shape objects.
    line_color = DEFAULT_LINE_COLOR
    fill_color = DEFAULT_FILL_COLOR
    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR
    point_type = P_ROUND
    point_size = 8#顶点大小
    scale = 1.0

    def __init__(self, label=None, line_color=None,difficult = False):
        self.label = label
        self.points = []
        self.fill = False
        self.selected = False
        self.difficult = difficult#dato数据

        self.direction = 0  # added by hy
        self.center = None # added by hy
        self.isRotated = True

        self._highlightIndex = None
        self._highlightMode = self.NEAR_VERTEX
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (1.5, self.P_SQUARE),
        }

        self._closed = False

        if line_color is not None:
            # Override the class line_color attribute
            # with an object attribute. Currently this
            # is used for drawing the pending line a different color.
            self.line_color = line_color


    def rotate(self, theta):#旋转一个形状
        for i, p in enumerate(self.points):#遍历形状中的所有点
            self.points[i] = self.rotatePoint(p, theta)#将每个点 p 旋转 theta 角度
        self.direction -= theta
        self.direction = self.direction % (2 * math.pi)
        print("rotate angle: ", theta,"self.direction:",self.direction)


    def rotatePoint(self, p, theta):#旋转一个点本身,数学计算
        # 围绕当前形状的中心点旋转
        order = p-self.center;
        print("self.center",self.center)
        cosTheta = math.cos(theta)
        sinTheta = math.sin(theta)
        pResx = cosTheta * order.x() + sinTheta * order.y()
        pResy = - sinTheta * order.x() + cosTheta * order.y()
        pRes = QPointF(self.center.x() + pResx, self.center.y() + pResy)
        return pRes

    def close(self):
        self.center = QPointF((self.points[0].x()+self.points[2].x()) / 2, (self.points[0].y()+self.points[2].y()) / 2)
        # print("refresh center!")
        self._closed = True

    def reachMaxPoints(self):
        if len(self.points) >= 4:
            return True
        return False

    def addPoint(self, point):
        if self.points and len(self.points) == 4 and point == self.points[0]:
            self.close()
        else:
            self.points.append(point)

    def popPoint(self):
        if self.points:
            return self.points.pop()
        return None

    def isClosed(self):
        return self._closed

    def setOpen(self):
        self._closed = False

    def paint(self, painter):
        if self.points:#形状有至少一个点，则开始绘制过程
            color = self.select_line_color if self.selected else self.line_color#根据形状是否被选中 ，选择线条颜色
            pen = QPen(color)
            # Try using integer sizes for smoother drawing(?)
            pen.setWidth(max(1, int(round(2.0 / self.scale))))
            painter.setPen(pen)#传入的绘制对象

            line_path = QPainterPath()#边缘线
            vrtx_path = QPainterPath()#绘制形状的顶点

            line_path.moveTo(self.points[0])#将线条的起始点设置为 self.points 列表中的第一个点。
            # Uncommenting the following line will draw 2 paths
            # for the 1st vertex, and make it non-filled, which
            # may be desirable.
            #self.drawVertex(vrtx_path, 0)

            for i, p in enumerate(self.points):
                line_path.lineTo(p)
                # print('shape paint points (%d, %d)' % (p.x(), p.y()))
                self.drawVertex(vrtx_path, i)
            if self.isClosed():
                line_path.lineTo(self.points[0])

            painter.drawPath(line_path)#绘制形状的轮廓线
            painter.drawPath(vrtx_path)# 绘制形状的顶点
            painter.fillPath(vrtx_path, self.vertex_fill_color)
            if self.fill:
                color = self.select_fill_color if self.selected else self.fill_color
                painter.fillPath(line_path, color)

            if self.center is not None:
                center_path = QPainterPath()
                d = self.point_size / self.scale
                center_path.addRect(self.center.x() - d / 2, self.center.y() - d / 2, d, d)
                painter.drawPath(center_path)
                if self.isRotated:
                    painter.fillPath(center_path, self.vertex_fill_color)
                else:
                    painter.fillPath(center_path, QColor(0, 0, 0))

    def paintNormalCenter(self, painter):
        #负责绘制并可能填充一个表示形状中心点的小矩形
        if self.center is not None:#图像绘制完整时才会绘制
            center_path = QPainterPath();#创建绘制路径
            d = self.point_size / self.scale#计算小矩形的边长
            center_path.addRect(self.center.x() - d / 2, self.center.y() - d / 2, d, d)
            painter.drawPath(center_path)
            if not self.isRotated:
                '''如果形状没有被旋转（self.isRotated为False），则使用黑色填充这个小矩形。'''
                painter.fillPath(center_path, QColor(0, 0, 0))

    def drawVertex(self, path, i):#绘制一个表示顶点的图形
        d = self.point_size / self.scale#计算顶点图形的大小
        #获取顶点的形状和位置
        shape = self.point_type
        point = self.points[i]

        if i == self._highlightIndex:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        if self._highlightIndex is not None:
            self.vertex_fill_color = self.hvertex_fill_color
        else:
            self.vertex_fill_color = Shape.vertex_fill_color
        if shape == self.P_SQUARE:
            path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
        elif shape == self.P_ROUND:
            path.addEllipse(point, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"
    # def drawVertex(self, path, center):
    #     pass

    def nearestVertex(self, point, epsilon):#查找离指定点最近的顶点
        for i, p in enumerate(self.points):
            if distance(p - point) <= epsilon:
                return i
        return None

    def containsPoint(self, point):#检查一个点point是否位于由self.points定义的形状内部
        return self.makePath().contains(point)

    def makePath(self):
        path = QPainterPath(self.points[0])
        for p in self.points[1:]:
            path.lineTo(p)
        return path

    def boundingRect(self):
        return self.makePath().boundingRect()

    def moveBy(self, offset):#将形状的所有顶点移动一个指定的偏移量offset
        self.points = [p + offset for p in self.points]

    def moveVertexBy(self, i, offset):#仅移动指定索引i的顶点一个偏移量offset
        self.points[i] = self.points[i] + offset

    def highlightVertex(self, i, action):#高亮显示指定索引i的顶点
        self._highlightIndex = i
        self._highlightMode = action

    def highlightClear(self):#清除顶点的高亮显示
        self._highlightIndex = None

    def copy(self):#复制一个新的对象
        shape = Shape("%s" % self.label)
        shape.points = [p for p in self.points]
        
        shape.center = self.center
        shape.direction = self.direction
        shape.isRotated = self.isRotated

        shape.fill = self.fill
        shape.selected = self.selected
        shape._closed = self._closed
        if self.line_color != Shape.line_color:
            shape.line_color = self.line_color
        if self.fill_color != Shape.fill_color:
            shape.fill_color = self.fill_color
        shape.difficult = self.difficult 
        return shape

    def __len__(self):
        return len(self.points)

    def __getitem__(self, key):
        return self.points[key]

    def __setitem__(self, key, value):
        self.points[key] = value

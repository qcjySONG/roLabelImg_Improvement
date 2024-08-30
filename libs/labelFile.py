# Copyright (c) 2016 Tzutalin
# Create by TzuTaLin <tzu.ta.lin@gmail.com>

try:
    from PyQt5.QtGui import QImage
except ImportError:
    from PyQt4.QtGui import QImage

from base64 import b64encode, b64decode
from pascal_voc_io import PascalVocWriter
from pascal_voc_io import XML_EXT
import os.path
import sys
import math

class LabelFileError(Exception):
    pass


class LabelFile(object):
    # It might be changed as window creates. By default, using XML ext
    # suffix = '.lif'
    suffix = XML_EXT

    def __init__(self, filename=None):
        self.shapes = ()
        self.imagePath = None
        self.imageData = None
        self.verified = False

    #将一组形状（如边界框或旋转边界框）及其相关的图像信息保存为Pascal VOC格式的文件。
    def savePascalVocFormat(self, filename, shapes, imagePath, imageData,
                            lineColor=None, fillColor=None, databaseSrc=None):
        imgFolderPath = os.path.dirname(imagePath)#图像路径
        imgFolderName = os.path.split(imgFolderPath)[-1]#图像所在的文件夹名称
        imgFileName = os.path.basename(imagePath)#图像文件的名称
        imgFileNameWithoutExt = os.path.splitext(imgFileName)[0]#获取图像文件的名称，但不包括扩展名。
        # Read from file path because self.imageData might be empty if saving to
        # Pascal format
        image = QImage()#用于处理图像
        image.load(imagePath)#加载指定路径的图像到QImage对象中
        imageShape = [image.height(), image.width(),#获取图像的形状（高度、宽度和通道数）。如果图像是灰度图，则通道数为1，否则为3
                      1 if image.isGrayscale() else 3]
        '''用于写入Pascal VOC格式的文件。该对象需要图像所在的文件夹名称、无扩展名的图像文件名、图像形状以及图像路径。'''
        writer = PascalVocWriter(imgFolderName, imgFileNameWithoutExt,
                                 imageShape, localImgPath=imagePath)
        writer.verified = self.verified

        for shape in shapes:
            points = shape['points']#提取点的信息
            label = shape['label']
            # Add Chris
            difficult = int(shape['difficult'])  #从当前形状中提取难度信息
            direction = shape['direction']#从当前形状中提取方向信息。
            isRotated = shape['isRotated']#从当前形状中提取是否旋转的信息
            # if shape is normal box, save as bounding box 
            # print('direction is %lf' % direction)
            if not isRotated:#判断当前形状是否是未旋转的。
                bndbox = LabelFile.convertPoints2BndBox(points)#如果形状未旋转，则调用convertPoints2BndBox方法将点转换为边界框。
                writer.addBndBox(bndbox[0], bndbox[1], bndbox[2], #将转换后的边界框及其标签和难度信息添加到PascalVocWriter对象中。
                    bndbox[3], label, difficult)#dota
            else: #if shape is rotated box, save as rotated bounding box
                robndbox = LabelFile.convertPoints2RotatedBndBox(shape)
                writer.addRotatedBndBox(robndbox[0],robndbox[1],
                    robndbox[2],robndbox[3],robndbox[4],label,difficult)

        writer.save(targetFile=filename)
        return

    def toggleVerify(self):#切换verified属性的布尔值
        self.verified = not self.verified

    @staticmethod
    def isLabelFile(filename):#检查给定的文件名是否是一个标签文件
        fileSuffix = os.path.splitext(filename)[1].lower()
        return fileSuffix == LabelFile.suffix #一定是xml才能被监测到

    @staticmethod
    def convertPoints2BndBox(points):#将一组点转换为一个边界框的坐标
        #初始值设置为正无穷大和负无穷大
        xmin = float('inf')
        ymin = float('inf')
        xmax = float('-inf')
        ymax = float('-inf')
        for p in points:
            x = p[0]
            y = p[1]
            xmin = min(x, xmin)
            ymin = min(y, ymin)
            xmax = max(x, xmax)
            ymax = max(y, ymax)

        # Martin Kersner, 2015/11/12
        # 0-valued coordinates of BB caused an error while
        # training faster-rcnn object detector.
        if xmin < 1:
            xmin = 1

        if ymin < 1:
            ymin = 1

        return (int(xmin), int(ymin), int(xmax), int(ymax))

    # You Hao, 2017/06/121
    @staticmethod
    def convertPoints2RotatedBndBox(shape):#将一个具有特定形状的对象转换为一个旋转的边界框
        points = shape['points']
        center = shape['center']
        direction = shape['direction']
        print("points",points)
        print("center",center)
        print("direction",direction)
        #获取中心点的 x 和 y 坐标
        cx = center.x()
        cy = center.y()
        #计算宽度 w
        w = math.sqrt((points[0][0]-points[1][0]) ** 2 +
            (points[0][1]-points[1][1]) ** 2)
        #计算高度 h
        h = math.sqrt((points[2][0]-points[1][0]) ** 2 +
            (points[2][1]-points[1][1]) ** 2)
        #对 direction 进行模运算，确保角度值在 [0, π) 范围内
        angle = direction % math.pi

        return (round(cx,4),round(cy,4),round(w,4),round(h,4),round(angle,6))

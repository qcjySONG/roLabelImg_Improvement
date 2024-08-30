

# (Improved Rotating Box Annotation Tool of rolabelimg)改进旋转框标注工具rolabelimg

<div align="center">
[English](./readme_EN.md)
</div>

![wayshow.gif](GIF%2Fwayshow.gif)

###  前言
最近在写本科毕业论文，涉及弱监督有向目标检测和旋转框标注软件的搭建。调查了市面上的一圈旋转框标注软件，其实感觉不太好用。
- rolabelImg：网上介绍的最多的一款标注软件，但是其在2020年更新完V3之后就停止了维护；其次，本人觉得它的标注方式（先绘制矩形框——>再通过快捷键旋转至目标合适的角度——>再调整至合适的大小）虽然能够很好的避免标注框存在部分位于图像外面的风险（这是旋转框特有的问题），但是确实不够直观。
- labelme：在知乎有篇文章介绍了如何使用多边形标注旋转框，文章链接: [link](https://zhuanlan.zhihu.com/p/430850089)。该方法虽然一定程度上比rolabelImg原本的方法简单，但是要标注4个点以及存在耗时的取最小外接矩形操作。
- mvtec：它的标注方式是最直观的（本文也是利用的它的标注方式，当然本科论文上我会写是我的创新点），但是这个软件是外国的软件，并且非常大，下载难。标注方式b站链接: [link](https://www.bilibili.com/video/BV1ne411p7gN/?share_source=copy_web&vd_source=64142f260d920ecb9e7a7e71f98a7d7a)
基于此，我选取了最多人使用的rolabelImg融合mvtec的标注方法进行改进，让旋转框的标注又简单又快。具体改变的代码其实不多，难的是看懂这些陈年老代码。

### 目前部分开源旋转框标注软件对比
- RolabelImg基于Python中的PyQt库而建立且专注于旋转框的标注，由于其安装较为容易，是目前Github上获得收藏数最多的旋转框标注软件。其标注一个旋转框总共可以拆分为3步：首先，在待标注目标上绘制一个水平框并设置目标的名称；其次，使用相应的快捷键进行方向的调整；最后，使用鼠标对旋转框进行大小和位置的调整。具体绘制过程如下图所示。
![RolabelImg](GIF%2Fway1.png)
- 与RolabelImg不同，LabelImg支持适用于图像、文本、超文本、音频、视频和时间序列数据的标注，是集大成者的标注软件。对于其图像部分，LabelImg仅支持水平框与多边形标注，不直接支持旋转框标注。但网络上有网友分享的“十字标注法”亦可实现使用LabelImg标注旋转框。[Link]:(https://zhuanlan.zhihu.com/p/430850089)“十字标注法”主要使用的为多边形标注工具，具体标注过程同样可分为三步：首先，在待标注目标的周围交叉标注5个点，使标注图形呈交叉封闭状态；其次，将标注好的文件进行导出并使用最小外接矩形计算器将标注图像转为旋转框；最后，将转换后的文件再次导入LabelImg中进行位置的微调（无法对方向进行微调）。具体标注过程入下图所示。
![LabelImg](GIF%2Fway2.png)
- 本项目介绍方法。首先，根据目标的长边特性，绘制一条倾斜的直线（程序会自动补全为相应方向的旋转框）并为其选择相应的标签。其次，为了更精确地定位目标，对绘制的旋转框进行方向上的微调，以确保其与实际目标的方向一致。最后，进行旋转框大小上的微调，以更贴近目标的实际尺寸。具体绘制方法如下图所示。
![my_RolabelImg](GIF%2Fway3.png)
- 根据上图的展示，可以清晰地看出，相较于RolabelImg和LabelImg的“十字标注法”，本文所设计的旋转框绘制方法更为直观且直接。该方法无需任何额外的繁琐步骤，使得标注过程更加高效且精准，为旋转目标检测任务提供了更为便捷和准确的标注手段。
![com](GIF%2Fcom.png)

### 与我的毕业论文中的区别
我的毕业论文提出一种基于H2RBox的弱监督旋转目标检测模型，旨在实现水平框标注数据集到旋转框标注的高效转换。该模型能够有效利用已有的水平框标注数据，通过弱监督学习的方式，衡量不同旋转视角下检测的一致性，自动提取目标的方向信息，并将其转换为精确的旋转框标注，为旋转目标检测任务提供有力的辅助数据标注支持。H2RBox模型：Yang X, Zhang G, Li W, et al. H2rbox: Horizontal box annotation is all you need for oriented object detection[J]. arXiv preprint arXiv:2210.06742, 2022.

<video width="1920" controls>
  <source src="./GIF/my_model.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

### others
以下为B站的一位up主的介绍

原作者Github链接: [https://github.com/cgvict/roLabelImg](https://github.com/cgvict/roLabelImg)

Up Github链接(附样例)：[https://github.com/Samsara0Null/roLabelImg](https://github.com/Samsara0Null/roLabelImg)

百度网盘(附样例、附exe)链接：[https://pan.baidu.com/s/1FOxz3gAXcj3ZVQPtX11vqw](https://pan.baidu.com/s/1FOxz3gAXcj3ZVQPtX11vqw)提取码：MBJC 

CSDN主页链接: [https://blog.csdn.net/noneNull0?type=blog](https://blog.csdn.net/noneNull0?type=blog)

Bilibili视频演示讲解链接: [https://www.bilibili.com/video/BV1GR4y1X7fq/?vd_source=a6067b731745325c01a4edfa46bf5a04](https://www.bilibili.com/video/BV1GR4y1X7fq/?vd_source=a6067b731745325c01a4edfa46bf5a04)
### 背景知识（background knowledge）：
&emsp;&emsp;相较原有的水平矩形方框标签，OBB定向包围框(oriented bounding box)即旋转方框标签可更加贴合目标，其主要信息由一个五元组组成(cx，cy，w，h，angle)。
![在这里插入图片描述](https://img-blog.csdnimg.cn/65e02f5dd11a4551a7828044b25a7722.png)

&emsp;如上图所示，width是图像的宽，height是图像的高,depth是图像的通道数
&emsp;cx, cy表示bndbox的中心点坐标(坐标系方向和一般的图像坐标系相同，左上角为原点，向右为x正方向，向下为y正方向)；
&emsp;h和w是标记目标的高和宽；
&emsp;angle是旋转角度信息，水平bndbox，angle=0，,顺时针方向旋转，得到的角度值是一个弧度单位的正值，且旋转一周为pi，没有负值。
### 安装过程（setup script）：
- 1、下载rolabelimg源代码（链接见开头）
&emsp;可选择封装好的exe直接双击运行，直接跳过2、3

![在这里插入图片描述](https://img-blog.csdnimg.cn/0fe334f5f4c2487a8e545f1d9825a02c.png)
- 2 、在Anaconda运行窗口中依次输入创建环境
```javascript
conda create -n rolabelimg python=3.8
activate rolabelimg
conda install pyqt
conda install lxml
```

- 3、cd到下载路径中，输入代码运行即可
```javascript
pyrcc5 -o resources.py resources.qrc 
python roLabelImg.py
```




### 常用快捷键：
快捷键 | 作用|原文
-------- | -----|-----
| Ctrl + u   |从目录加载所有图像| Load all of the images from a directory    |
| Ctrl + r   |更改默认注释目标目录| Change the default annotation target dir   |
| Ctrl + s   |保存|  Save                                       |
| Ctrl + d   |复制当前标签和矩形框 | Copy the current label and rect box        |
| Space      |将当前图像标记为已验证|  Flag the current image as verified         |
| w          |创建矩形框 | Create a rect box                          |
| e          | 创建旋转矩形框| Create a Rotated rect box                  |
| d          |下一个图像 | Next image                                 |
| a          |上一个图像|  Previous image                             |
| r          | 隐藏/显示旋转矩形框| Hidden/Show Rotated Rect boxes             |
| n          |隐藏/显示普通矩形框 | Hidden/Show Normal Rect boxes              |
| del        | 删除所选矩形框| Delete the selected rect box               |
| Ctrl+滚轮     | 放大| Zoom in                                    |
| Ctrl+滚轮  |缩小 | Zoom out                                   |
| ↑→↓←       | 移动选定矩形框的按键| Keyboard arrows to move selected rect box  |
| zxcv       |旋转所选矩形框的按键 | Keyboard to rotate selected rect box       |


<span style="color:pink;">Author: MBJC</span>  
<span style="color:pink;">Last modification time: 2024/03/11 23:37</span>

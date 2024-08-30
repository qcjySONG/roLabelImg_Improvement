

# Improved Rotating Box Annotation Tool of rolabelimg

<div align="center">
[Chinese](./readme.md)
</div>

![wayshow.gif](GIF%2Fwayshow.gif)

###  Introduction
I am currently writing my undergraduate thesis, which involves weakly supervised oriented object detection and the development of rotating box annotation software. After researching various rotating box annotation tools available on the market, I found them to be less user-friendly.
- rolabelImg：The most widely introduced annotation software online, but it stopped being maintained after updating to V3 in 2020. Its annotation method (drawing a rectangle first -> rotating to the appropriate angle using a shortcut -> adjusting size) avoids the issue of part of the annotation box being outside the image (a problem specific to rotating boxes), but it is not intuitive enough.
- labelme：An article on Zhihu introduces how to use polygon annotation for rotating boxes. Although this method is simpler compared to rolabelImg’s original method, it involves annotating four points and a time-consuming minimum bounding rectangle operation. [link](https://zhuanlan.zhihu.com/p/430850089)。
- mvtec：This software has the most intuitive annotation method (which I am also using as a basis for my thesis, though I'll present it as my innovation). However, it is a foreign software, very large, and difficult to download. Annotation method Bilibili link: [link](https://www.bilibili.com/video/BV1ne411p7gN/?share_source=copy_web&vd_source=64142f260d920ecb9e7a7e71f98a7d7a)
Based on this, I chose to improve the widely used rolabelImg by integrating the annotation method from mvtec to make rotating box annotation both simple and fast. The changes in the code are minimal, but understanding the legacy code is the challenge.

### Comparison of Existing Open-Source Rotating Box Annotation Software
- RolabelImg is built on the PyQt library in Python and focuses on rotating box annotation. Its easy installation makes it the most bookmarked rotating box annotation software on GitHub. Annotating a rotating box involves three steps: first, draw a horizontal box on the target and set the target's name; second, use the corresponding shortcut to adjust the orientation; third, use the mouse to adjust the size and position of the rotating box. The annotation process is shown in the figure below.
![RolabelImg](GIF%2Fway1.png)
- Unlike RolabelImg, LabelImg supports annotation for images, text, hypertext, audio, video, and time-series data, making it a versatile annotation tool. For images, LabelImg supports only horizontal boxes and polygons, and does not directly support rotating boxes. However, an online method called the “Cross Annotation Method” can achieve rotating box annotation using LabelImg. Link The “Cross Annotation Method” involves annotating five points in a cross pattern around the target, exporting the annotation file, using a minimum bounding rectangle calculator to convert it into a rotating box, and then re-importing the file into LabelImg for final adjustments (direction adjustments are not possible). The annotation process is shown below.
![LabelImg](GIF%2Fway2.png)
- My Project’s Method: First, draw an inclined line according to the target's long side characteristics (the program will automatically complete it as a corresponding rotating box) and select the appropriate label. Second, to precisely locate the target, adjust the direction of the drawn rotating box to ensure it aligns with the actual target's direction. Lastly, adjust the size of the rotating box to match the actual dimensions of the target. The annotation method is shown below.
![my_RolabelImg](GIF%2Fway3.png)
- As shown in the figure above, compared to the “Cross Annotation Method” of RolabelImg and LabelImg, the rotating box drawing method designed in this paper is more intuitive and direct. This method eliminates any extra cumbersome steps, making the annotation process more efficient and accurate, providing a more convenient and precise annotation tool for rotating object detection tasks.
![com](GIF%2Fcom.png)

### Differences from My Thesis
In my thesis, I propose a weakly supervised rotating object detection model based on H2RBox, aimed at achieving efficient conversion from horizontal box annotation datasets to rotating box annotations. This model effectively utilizes existing horizontal box annotation data and, through weak supervision learning, measures the consistency of detection under different rotation angles. It automatically extracts the orientation information of the target and converts it into precise rotating box annotations, providing strong support for data annotation in rotating object detection tasks.
<video width="1920" controls>
  <source src="./GIF/my_model.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

### others
Below is an introduction from a Bilibili :

Original Author’s Github Link: [https://github.com/cgvict/roLabelImg](https://github.com/cgvict/roLabelImg)

Uploader’s Github Link (with examples):[https://github.com/Samsara0Null/roLabelImg](https://github.com/Samsara0Null/roLabelImg)

Baidu Netdisk Link (with examples and exe):[https://pan.baidu.com/s/1FOxz3gAXcj3ZVQPtX11vqw](https://pan.baidu.com/s/1FOxz3gAXcj3ZVQPtX11vqw)提取码：MBJC 

CSDN Homepage Link:[https://blog.csdn.net/noneNull0?type=blog](https://blog.csdn.net/noneNull0?type=blog)

Bilibili Video Demonstration Link:  [https://www.bilibili.com/video/BV1GR4y1X7fq/?vd_source=a6067b731745325c01a4edfa46bf5a04](https://www.bilibili.com/video/BV1GR4y1X7fq/?vd_source=a6067b731745325c01a4edfa46bf5a04)
### Background Knowledge:
&emsp;&emsp;Compared to the traditional horizontal bounding box labels, Oriented Bounding Boxes (OBB) or rotating bounding boxes can better fit the target. The main information is represented by a five-tuple (cx, cy, w, h, angle).
![在这里插入图片描述](https://img-blog.csdnimg.cn/65e02f5dd11a4551a7828044b25a7722.png)

&emsp;As shown in the image above, width is the width of the image, height is the height of the image ,depth is the number of channels in the image
&emsp;cx and cy are the coordinates of the center of the bounding box (with the coordinate system direction the same as the typical image coordinate system, with the top-left corner as the origin, right as the positive x direction, and down as the positive y direction)
&emsp;h and w are the height and width of the target
&emsp;angle is the rotation angle information, where angle = 0 for a horizontal bounding box. For clockwise rotation, the angle value is a positive value in radians, with a full rotation being π, and no negative values.
### Installation Process:：
- 1、Download the rolabelimg source code (link at the beginning) You can choose the packaged exe for direct execution, skipping steps 2 and 3.

![在这里插入图片描述](https://img-blog.csdnimg.cn/0fe334f5f4c2487a8e545f1d9825a02c.png)
- 2 、In the Anaconda command window, enter the following to create the environment:
```javascript
conda create -n rolabelimg python=3.8
activate rolabelimg
conda install pyqt
conda install lxml
```

- 3、Navigate to the download path and run the following code:
```javascript
pyrcc5 -o resources.py resources.qrc 
python roLabelImg.py
```




### Common Shortcuts:
Shortcut | 作用|Function
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

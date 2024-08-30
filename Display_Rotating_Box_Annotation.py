import cv2  
import numpy as np  
import random  

# 图像和标签文件路径  
image_path = 'jpg/P0549.png'  
label_path = 'jpg/P0549.txt'  

# 读取图像  
image = cv2.imread(image_path)  

# 读取标签文件  
with open(label_path, 'r') as f:  
    lines = f.readlines()  

# 定义一个函数生成随机颜色  
def random_color():  
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))  

# 存储标签和对应的颜色  
label_colors = {}  

# 遍历标签文件中的每一行  
for line in lines:  
    line = line.strip().split()  

    x1, y1, x2, y2, x3, y3, x4, y4, label, _ = line  

    # 将坐标转换为整数类型  
    x1, y1, x2, y2, x3, y3, x4, y4 = map(float, [x1, y1, x2, y2, x3, y3, x4, y4])  
    x1, y1, x2, y2, x3, y3, x4, y4 = map(int, [x1, y1, x2, y2, x3, y3, x4, y4])  

    # 检查标签是否已有颜色，若没有则生成随机颜色  
    if label not in label_colors:  
        line_color = random_color()  
        text_color = random_color()  
        
        # 确保文本颜色与线条颜色不同  
        while text_color == line_color:  
            text_color = random_color()  
        
        label_colors[label] = (line_color, text_color)  
    else:  
        line_color, text_color = label_colors[label]  

    # 绘制多边形  
    points = np.array([[x1, y1], [x2, y2], [x3, y3], [x4, y4]], np.int32)  
    points = points.reshape((-1, 1, 2))  
    cv2.polylines(image, [points], True, line_color, 2)  

    # 标签绘制  
    cv2.putText(image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)  

# 显示绘制标签后的图像  
cv2.imshow("Image with Labels", image)  
cv2.waitKey(0)  
cv2.destroyAllWindows()
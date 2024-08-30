import math
def calculate_sin_cos(point1, point2):
    '''
    互余的角就是和为90°的角,任意一个角的正弦值都等于它的余角的余弦值；任意一个角的余弦值也都等于它的余角的正弦值。
    sin(90°-α)=cosα，cos(90°-α)=sinα。
    '''
    x1, y1 = point1
    x2, y2 = point2
    # 计算水平距离和垂直距离
    horizontal_distance = abs(x2 - x1)#邻边
    vertical_distance = abs(y2 - y1)#对边
    # 计算两点之间的直线距离
    distance = math.sqrt(horizontal_distance ** 2 + vertical_distance ** 2)#斜边
    #print(distance)
    # 计算正弦值和余弦值 sin=对比斜 cos=邻比斜
    sin_value = vertical_distance / distance
    cos_value = horizontal_distance / distance

    return sin_value, cos_value

# 示例用法
# point1 = (0, 1)
# point2 = (math.sqrt(3) , 0)
# sin_value, cos_value = calculate_sin_cos(point1, point2)
# print("Sin:", sin_value)#1/2
# print("Cos:", cos_value)#math.sqrt(3)/2

def calculate_distance(point1, point2):  
    """  
    计算两点间的直线距离  
    :param point1: 第一个点的坐标 (x1, y1)  
    :param point2: 第二个点的坐标 (x2, y2)  
    :return: 两点间的直线距离  
    """  
    x1, y1 = point1  
    x2, y2 = point2  
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)  
    return distance  

# # 示例  
# point1 = (1, 2)  
# point2 = (4, 6)  
# print(f"两点间的直线距离: {calculate_distance(point1, point2)}")  

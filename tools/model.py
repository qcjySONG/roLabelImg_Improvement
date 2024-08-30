def rotate(theta, direction=0):  # 旋转一个形状
    direction -= theta
    direction = direction % (2 * math.pi)
    print("rotate angle: ", theta, "self.direction:", direction)
import math
direction=0
j=0
for i in range(200):
    j=j+1
    theta=0.1
    direction -= theta
    direction = direction % (2 * math.pi)
    print(j,"rotate angle: ", theta, "self.direction:", direction)
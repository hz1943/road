import ast
import math
import time
import requests


def calculate_pci_last(tag_list, road_width,type,paras_dic):
    # 需要根据摄像机的角度算出比例
    # scale=cal_scale()

    tag_area =  tag_area_sum(tag_list,paras_dic,False)
    sum_area = road_width * type
    # 计算pci
    # a0:沥青路面采用15.00，水泥混凝土路面采用10.66
    # a1:沥青路面采用0.412，水泥混凝土路面采用0.461
    a0 = 10.66
    a1 = 0.461
    pci = 100 - a0 * math.pow(100.0 * tag_area / sum_area, a1)
    return pci


# 计算pci
def calculate_pci(tag_list, gps, road_width):
    """
    :param tag_list: 一条视频内所有损坏图像的标签
    :param gps: gps 文件
    :param road_width: 路宽
    :return:
    """
    # tag_list是包含一条视频内所有损坏图像的标签
    # 0.000064为缩小倍数，图上一单位面积等于现实多少面积
    #tag_area_sum已更改
    tag_area = 0.000064 * tag_area_sum(tag_list)
    # 读取gps数据  http://117.71.48.144:9898/20210603//sdcard/Download/02021060310475820210603104945.txt
    # 获取时间,s
    start = time.mktime(time.strptime(gps[-32:-18], '%Y%m%d%H%M%S'))
    end = time.mktime(time.strptime(gps[-18:-4], '%Y%m%d%H%M%S'))
    ss = end - start
    s = requests.get(gps).text.split('\r\n')
    speed_sum = 0.0
    j = 1
    for i in range(len(s) - 2):
        stime = ast.literal_eval(s[i])['time']
        s_time = time.mktime(time.strptime(stime, '%Y-%m-%d %H:%M:%S'))
        if start <= s_time <= end:
            speed = ast.literal_eval(s[i])['speed']
            speed_sum = speed_sum + float(speed)
            if speed != '0.0':
                j += 1

    average_speed = float(speed_sum / j)

    # 计算总面积
    sum_area = road_width * ss * average_speed + 1
    # 计算pci
    # a0:沥青路面采用15.00，水泥混凝土路面采用10.66
    # a1:沥青路面采用0.412，水泥混凝土路面采用0.461
    a0 = 10.66
    a1 = 0.461
    pci = 100 - a0 * math.pow(100 * tag_area / sum_area, a1)
    return pci


def tag_area_sum(tag_list,paras_dic,isSelf):
    """
    D00:纵向裂缝 D10:横向裂缝  D20:龟裂  D40:坑槽
    :param paras_dic:
    :param tag_list:
    :return:
    """
    damageTag = "damage_tag" if isSelf else "damageTag"
    adaptive_weight = 0.4
    l_sum = 0
    h_sum = 0
    for j in range(len(tag_list)):
        ll = eval(tag_list[j]["location"])
        if tag_list[j][damageTag] == "D10":
            mid_high = (ll[1] + ll[3]) / 2
            lenth = (ll[2] - ll[0]) * cal_scale(mid_high,paras_dic,isSelf)*adaptive_weight
            l_sum += lenth * 1
        if tag_list[j][damageTag] == "D00":
            high = 0
            for i in range(ll[1], ll[3]):
                high += cal_scale(i,paras_dic,isSelf)*adaptive_weight
            l_sum += high * 1
        if tag_list[j][damageTag] == "D20":
            sum = 0
            for i in range(ll[1], ll[3]):
                scale = cal_scale(i,paras_dic,isSelf)
                # 1 pixel in y-axis
                sum += scale * scale * (ll[2] - ll[0])
            l_sum += sum * adaptive_weight
        if tag_list[j][damageTag] == "D40":
            hsum = 0
            for i in range(ll[1], ll[3]):
                scale = cal_scale(i,paras_dic,isSelf)
                hsum += scale * scale * (ll[2] - ll[0])
            h_sum += hsum * adaptive_weight
    # 裂缝权重0.8 坑洞权重1
    return 0.8 * l_sum + 1 * h_sum


# 计算比例

def cal_scale(y_i,paras_dic,isSelf):
    angleLeft = 'angle_left' if isSelf else 'angleLeft'
    angleRight = 'angle_right' if isSelf else 'angleRight'
    laneHighPixel = 'lane_high_pixel' if isSelf else 'laneHighPixel'
    lanePixelLen = 'lane_pixel_len' if isSelf else 'lanePixelLen'
    laneWidth = 'lane_width' if isSelf else 'laneWidth'
    theat1 = float(paras_dic[angleLeft])
    theat2 = float(paras_dic[angleRight])
    y_high = float(paras_dic[laneHighPixel])
    lane_pixel = float(paras_dic[lanePixelLen])
    lane_width = float(paras_dic[laneWidth])
    new_lane_pixel = 0
    if y_i < y_high:
        new_lane_pixel = lane_pixel - ((y_high - y_i) / math.tan(math.radians(theat1)) + (y_high - y_i) / math.tan(math.radians(theat2)))
    else:
        new_lane_pixel = lane_pixel + ((y_i - y_high) / math.tan(math.radians(theat1)) + (y_i - y_high) / math.tan(math.radians(theat2)))
    new_scale = lane_width / new_lane_pixel
    return new_scale


def calculate_pci1(tag_list, gps, paras_dic):
    """
    :param paras_dic:
    :param tag_list: 一条视频内所有损坏图像的标签
    :param gps: gps 文件
    :param road_width: 路宽
    :return:
    """
    # tag_list是包含一条视频内所有损坏图像的标签
    tag_area = tag_area_sum(tag_list,paras_dic, True)
    # 读取gps数据  http://117.71.48.144:9898/20210603//sdcard/Download/02021060310475820210603104945.txt
    # 获取时间,s
    start = time.mktime(time.strptime(gps[-32:-18], '%Y%m%d%H%M%S'))
    end = time.mktime(time.strptime(gps[-18:-4], '%Y%m%d%H%M%S'))
    s = requests.get(gps).text.split('\r\n')
    distance_sum = 0.0
    for i in range(len(s) - 2):
        stime = ast.literal_eval(s[i])['time']
        s_time = time.mktime(time.strptime(stime, '%Y-%m-%d %H:%M:%S'))
        if start <= s_time <= end:
            distance = ast.literal_eval(s[i])['distance']
            distance_sum = distance_sum + float(distance)

    # 计算总面积
    sum_area = float(paras_dic['lane_width']) * distance_sum + 1
    # 计算pci
    # a0:沥青路面采用15.00，水泥混凝土路面采用10.66
    # a1:沥青路面采用0.412，水泥混凝土路面采用0.461
    a0 = 10.66
    a1 = 0.461
    pci = 100 - a0 * math.pow(100 * tag_area / sum_area, a1)
    return pci

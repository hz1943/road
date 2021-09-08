from database import fetch_to_dict
import math

#计算车道线交点的y坐标
def calc_lane_corss_high(lane_high_pixel,lane_pixel_len,angle_left,angle_right):
    high_pixel = lane_pixel_len / (1.0 / math.tan(math.radians(angle_left)) + 1.0 / math.tan(math.radians(angle_right)))
    return lane_high_pixel - high_pixel

def calcTagCount(tagList):
    tagCount = {'D00':0, 'D10':0, 'D20':0, 'D40':0}
    for tag in tagList:
        tagCount[tag['damage_tag']] += 1
    return tagCount

def isTagsEqual(tagListA, tagListB):
    tags = ['D00', 'D10', 'D20', 'D40']
    tagCountA = calcTagCount(tagListA)
    tagCountB = calcTagCount(tagListB)
    for tag in tags:
        if tagCountA[tag] != tagCountB[tag]:
            return False
    return True

def filter_stride(images, stride):
    images_after_filter = []
    tag_list_filter = []
    for i in range(len(images) - 1):
        # 车速60km/h，17m/s。从图片看出识别有效距离为1车道线+1/3间隔，车道线6米，间隔9米，共9米，车行需要0.5秒。所以需要过滤fps/2间隔内的帧
        # 并且检测的tags数量一样，则认为检测的结果重复
        if (images[i]['frame_number'] + stride >= images[i + 1]['frame_number']) and isTagsEqual(images[i]['tags'], images[i + 1]['tags']):
            continue
        images_after_filter.append(images[i])
        tag_list_filter.extend(images[i]['tags'])
        
    images_after_filter.append(images[-1])
    tag_list_filter.extend(images[-1]['tags'])
    images.clear()
    images.extend(images_after_filter)
    return tag_list_filter

def filter_inter(images):
    '''
    帧间过滤
    :param images: list of dict
    :return: images after filter
    '''
    # 完成过滤的工作
    images_after_filter = []
    # 过滤image
    for i in range(len(images) - 1):
        # 连续帧过滤
        if images[i]['frame_number'] + 1 != images[i + 1]['frame_number']:
            images_after_filter.append(images[i])
    # 无论倒数第二帧和最后一帧是否连续，都要加入最后一帧
    images_after_filter.append(images[-1])    
    images.clear()
    images.extend(images_after_filter)

def filter_intra(images, y_threshold, db):
    '''
    May change images
    '''
    # 获取所有标签，计算PCI
    tag_list_filter = []
    images_temp = []
    for image in images:
        tags = fetch_to_dict(db, 'select  * from tbl_damages where damage_id=:damage_id', {'damage_id':image["id"]})
        # 过滤操作------------------
        do_filter_tag(tags, y_threshold)
        if len(tags) != 0:
            image["tags"] = tags
            images_temp.append(image)
            tag_list_filter.extend(tags)
    images.clear()
    images.extend(images_temp)
    return tag_list_filter

"""
tag_list:标签列表
ex
[xl,yl,xr,yr]
[{'location': '[588, 493, 763, 644]', 'damage_tag': 'D00'},
{'location': '[611, 486, 772, 651]', 'damage_tag': 'D00'},
{'location': '[648, 484, 766, 652]', 'damage_tag': 'D00'}]
"""


def do_filter_tag(tag_list, y_threshold):
    tag_list_temp = []
    for tag in tag_list:
        location = eval(tag['location'])
        #检测框的上边完全在车道线三角形内，或者在图像1/3以下
        #一方面是去除图像上部的干扰，另一方面避免在计算损害实际长度时为负值
        if location[1] > y_threshold:
            tag_list_temp.append(tag)
    #没有符合上述条件的框
    if len(tag_list_temp) == 0:
        tag_list.clear()
        return

    for i in range(len(tag_list_temp) - 1):
        if (tag_list_temp[i]['location'] != ''):
            for j in range(i + 1, len(tag_list_temp)):
                if (tag_list_temp[j]['location'] != ''):
                    if tag_list_temp[i]['damage_tag'] == tag_list_temp[j]['damage_tag']:
                        l1 = eval(tag_list_temp[i]['location'])
                        l2 = eval(tag_list_temp[j]['location'])
                        if isCross(l1, l2):
                            l_new = combine(l1, l2)
                            tag_list_temp[i]['location'] = str(l_new)
                            tag_list_temp[j]['location'] = ''

    tag_list.clear()
    for i in range(len(tag_list_temp)):
        if (tag_list_temp[i]['location'] != ''):
            tag_list.append(tag_list_temp[i])
    
"""
首先求出P1与P3点在X方向较大值与Y方向较大值的交点，在下图中就是P3，用红点(记为M点)表示。

然后求出P2与P4点在X方向较小值与Y方向较小值的交点，在下图中就是P2，用橙色点(记为N点)表示。

如果M点的X坐标和Y坐标值均比N点相应的X坐标和Y坐标值小，亦即M和N可以分别构成一个矩形的左上角点和右上角点，则两矩形相交；其余情况则不相交。
"""


def isCross(l1, l2):
    left_x_max = max(l1[0], l2[0])
    left_y_max = max(l1[1], l2[1])
    right_x_min = min(l1[2], l2[2])
    right_y_min = min(l1[3], l2[3])
    if (left_x_max < right_x_min) & (left_y_max < right_y_min):
        return True
    else:
        return False


def combine(l1, l2):
    left_x_min = min(l1[0], l2[0])
    left_y_min = min(l1[1], l2[1])
    right_x_max = max(l1[2], l2[2])
    right_y_max = max(l1[3], l2[3])
    l_new = [left_x_min, left_y_min, right_x_max, right_y_max]
    return l_new

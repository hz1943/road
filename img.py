from VideoInfo import VideoInfo
import os
import json
import logging

import numpy as np
import base64
from ffmpy import FFmpeg
import urllib.request
import cv2
from edict import AttrDict

cfg = AttrDict()
cfg.damage_image_path = '/app/road/damage_image/'
cfg.damage_video_path = '/app/road/damage_video/'
cfg.avi_video_path = '/app/road/avi_video/'
cfg.video_3s_path = '/app/road/video_3s/'

# URL到图片
def url_to_image(url):
    # download the image, convert it to a NumPy array, and then read
    # it into OpenCV format
    resp = urllib.request.urlopen(url)
    # bytearray将数据转换成（返回）一个新的字节数组
    # asarray 复制数据，将结构化数据转换成ndarray
    image = np.asarray(bytearray(resp.read()), dtype="uint8")
    # cv2.imdecode()函数将数据解码成Opencv图像格式
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    # return the image
    return image

def cv2_base64(image):
    base64_str = cv2.imencode('.jpg', image)[1]
    base64_str = str(base64.b64encode(base64_str))[2:-1]
    return base64_str


def base64_cv2(base64_str):
    imgString = base64.b64decode(base64_str)
    nparr = np.fromstring(imgString, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return image


def repleace_vid(url, pk, img_dict_json):  # 容器里的目录
    """
    目录：
    合成视频：video/file_video/file_id.mp4

    """
    assert url.lower().startswith(('rtsp://', 'rtmp://', 'http://')), \
        str(url) + 'is Illegal video address!'

    img_dict = json.loads(img_dict_json)
    file_save_path = '/home/container/road2.0/video/file_video/'
    damage_save_path = '/home/container/road2.0/video/damages_video/'

    vid_path = os.path.join(damage_save_path, str(pk) + '.avi')
    at_path = os.path.join(file_save_path, str(pk) + '.mp4')

    cap = cv2.VideoCapture(eval(url) if url.isnumeric() else url)
    assert cap.isOpened(), 'Failed to open %s' % str(url)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frams = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    print(frams)
    # vid_writer = cv2.VideoWriter(vid_path, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), fps, (w, h))
    vid_writer = cv2.VideoWriter(vid_path, cv2.VideoWriter_fourcc('I', '4', '2', '0'), fps, (w, h))
    # 使用yuv进行保存，省去了解码的时间
    # vid_writer = cv2.VideoWriter(vid_path, cv2.VideoWriter_fourcc('A', 'V', 'C', '1'), fps, (w, h))
    # 读取第一帧
    cap.grab()
    n = 0
    while cap.isOpened():
        if str(n) in img_dict or n in img_dict:
            # image = io.imread(img_src)
            image=url_to_image(img_dict[str(n)])
            vid_writer.write(image)
            # cv2.imwrite(os.path.join(save_path ,str(pk) + str(n) + '.jpg'), base64_cv2(img_dict[str(n)]))
        else:
            success, frame = cap.retrieve()
            if not success:
                break
            vid_writer.write(frame)  # 写视频帧
            # cv2.imwrite(os.path.join(save_path ,str(pk) + str(n) + '.jpg'), frame)
        cap.grab()
        n += 1
        if n > frams:
            break

        # cv2.waitKey(1000/fps) # 延迟
        # time.sleep(1/fps)
    if os.path.isfile(at_path):
        os.remove(at_path)
    ff = FFmpeg(
        inputs={'%s' % str(vid_path): None},
        outputs={'%s' % str(at_path): '-loglevel repeat+level+error -vcodec libx264 -f mp4'}
    )

    # ffmpeg -i filePath/fileName.avi -vcodec libx264 -f mp4 filePath/fileName.mp4
    ff.run()

    return 'http://223.244.82.97:17480/road2.0/video/file_video/'+str(pk) + '.mp4', fps, frams, vid_path


def get_3svideo(frame_number, fps, frames, file_id, avi_video):

    video_3s_path = os.path.join(cfg.video_3s_path, "%s_%s.mp4" % (str(file_id), str(frame_number)))

    # video_3s_path = os.path.join(cfg.video_3s_path, str(file_id))
    # if not os.path.exists(video_3s_path):
    #     os.makedirs(video_3s_path)
    #     print(video_3s_path + "目录创建成功")
    # else:
    #     print(video_3s_path + "目录已存在")


    # ffmpeg -i xx.avi -ss 30 -c copy -to 40 xx.mp4
    begin = frame_number / fps - 3.0
    over = frame_number / fps + 3.0
    if begin < 0:
        begin = 0
    if over > frames / fps:
        over = frames / fps
    if os.path.isfile(video_3s_path):
        os.remove(video_3s_path)
    ff = FFmpeg(
        inputs={'%s' % str(avi_video): None},
        outputs={'%s' % str( video_3s_path): '-loglevel repeat+level+error -ss %f  -to %f' % (begin, over)}
    )
    ff.run()
    return video_3s_path


def getVideoInfo(video_url):
    assert video_url.lower().startswith(('rtsp://', 'rtmp://', 'http://')), \
        str(video_url) + 'is Illegal video address!'

    videoCapture = cv2.VideoCapture(video_url)

    assert videoCapture.isOpened(), 'Failed to open %s' % str(video_url)

    videoInfo = VideoInfo()
    videoInfo.width = int(videoCapture.get(cv2.CAP_PROP_FRAME_WIDTH))
    videoInfo.height = int(videoCapture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    videoInfo.fps = videoCapture.get(cv2.CAP_PROP_FPS)
    videoInfo.frameCount = videoCapture.get(cv2.CAP_PROP_FRAME_COUNT)
    return (videoInfo, videoCapture)

def save_image(frame, addr, num):
    address = addr + str(num) + '.jpg'
    cv2.imwrite(address, frame)
    return address

def getFrames(video_url, images):
    frames = []
    videoCapture = cv2.VideoCapture(video_url)
    n = 0
    success = True
    videoCapture.grab()
    for i in range(len(images)):
        while True:
            # 在Premiere上看的是270帧（从0开始），算法给出的是269
            if n == images[i]["frame_number"] + 1:
                success, frame = videoCapture.retrieve()
                frames.append(frame)
                save_image(frame, '/app/huzeng', n)
                break
            n += 1
            videoCapture.grab()
    return frames

def draw_rectangle(video_url, images):
    frames = getFrames(video_url, images)
    for frame, image in zip(frames, images):
        for tag in image['tags']:
            ll = eval(tag["location"])
            if tag['damage_tag'] == 'D00':
                color = (255, 0, 0)
            if tag['damage_tag'] == 'D10':
                color = (0, 255, 0)
            if tag['damage_tag'] == 'D20':
                color = (0, 0, 255)
            if tag['damage_tag'] == 'D40':
                color = (128, 0, 128)
            xy1, xy2 = (ll[0], ll[1]), (ll[2], ll[3])
            cv2.rectangle(frame, xy1, xy2, color, 2)

            cv2.putText(frame, tag['damage_tag'] + ' ' + str(tag['confidence']), (ll[0], ll[1] - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, color, 4, lineType=cv2.LINE_AA)
            #TODO 上传过滤后的图片，更新tbl_road_damage_filter
            cv2.imwrite(cfg.damage_image_path + '%s.jpg' % str(image["id"]), frame)

def draw_tags(frame, tags):
    for tag in tags:
        ll = eval(tag["location"])
        if tag['damage_tag'] == 'D00':
            color = (255, 0, 0)
        if tag['damage_tag'] == 'D10':
            color = (0, 255, 0)
        if tag['damage_tag'] == 'D20':
            color = (0, 0, 255)
        if tag['damage_tag'] == 'D40':
            color = (128, 0, 128)
        xy1, xy2 = (ll[0], ll[1]), (ll[2], ll[3])
        cv2.rectangle(frame, xy1, xy2, color, 2)
        cv2.putText(frame, tag['damage_tag'] + ' ' + str(tag['confidence']), (ll[0], ll[1] - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 4, lineType=cv2.LINE_AA)
        #TODO 上传过滤后的图片，更新tbl_road_damage_filter

def save_video_and_image(file_id, videoCapture, images):

    avi_path = os.path.join(cfg.avi_video_path, str(file_id) + '.avi')
    mp4_path = os.path.join(cfg.damage_video_path, str(file_id) + '.mp4')

    
    w = int(videoCapture.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(videoCapture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = videoCapture.get(cv2.CAP_PROP_FPS)
    frame_count = videoCapture.get(cv2.CAP_PROP_FRAME_COUNT)
    logging.info('Save video: ' + str(file_id) + ' frame_count: ' + str(frame_count))
    #print('Save video: ' + str(file_id) + ' frame_count: ' + str(frame_count))
    avi_writer = cv2.VideoWriter(avi_path, cv2.VideoWriter_fourcc('I', '4', '2', '0'), fps, (w, h))

    success = videoCapture.grab()
    found = False
    n = 0
    for image in images:
        found = False
        while success:
            retval, frame = videoCapture.retrieve()            
            # 在Premiere上看的是270帧（从0开始），算法给出的是269
            if n == image["frame_number"] + 1:
                draw_tags(frame, image['tags'])
                image_url = cfg.damage_image_path + '%s.jpg' % str(image["id"])
                image['damage_img_url'] = image_url
                cv2.imwrite(image_url, frame)
                # 找到一帧应跳出循环，找下一帧
                found = True                
            avi_writer.write(frame)
            n += 1
            success = videoCapture.grab()
            if found:
                break
    while success:
        retval, frame = videoCapture.retrieve()
        avi_writer.write(frame)
        success = videoCapture.grab()

    if os.path.isfile(mp4_path):
        os.remove(mp4_path)
    ff = FFmpeg(
        inputs={'%s' % str(avi_path): None},
        outputs={'%s' % str(mp4_path): '-loglevel repeat+level+error -vcodec libx264 -f mp4'}
    )
    # ffmpeg -i filePath/fileName.avi -vcodec libx264 -f mp4 filePath/fileName.mp4
    ff.run()

    return mp4_path, fps, frame_count, avi_path

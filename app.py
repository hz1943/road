import os
from cv2 import VideoCapture
import flask
from flask_sqlalchemy import SQLAlchemy
import requests
import json
import logging
import ast
import time
from pci import calculate_pci_last
from database import fetch_to_dict
from img import get_3svideo, getVideoInfo, save_video_and_image
from pci import calculate_pci1
import filter


# cx处理
app = flask.Flask(__name__, template_folder='.')
# 格式为app.config['SQLALCHEMY_DATABASE_URI'] =  'mysql+pymysql://数据库用户:密码@127.0.0.1/数据库名称'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:zy63815635@172.16.1.200:3306/road_detection?charset=utf8'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_POOL_RECYCLE'] = 600
db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(filename)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

class tbl_file(db.Model):
    # 声明表名
    __tablename__ = 'tbl_file'
    # 建立字段函数
    id = db.Column(db.Integer, primary_key=True)
    video_file = db.Column(db.String(200))
    gps_file = db.Column(db.String(200))
    device_sn = db.Column(db.String(200))
    damage_video = db.Column(db.String(200))
    pci = db.Column(db.Integer)
    record_id = db.Column(db.Integer)


class tbl_road_damage(db.Model):
    __tablename__ = 'tbl_road_damage'
    id = db.Column(db.Integer, primary_key=True)
    frame_number = db.Column(db.Integer)
    file_id = db.Column(db.Integer)
    damage_video = db.Column(db.String(200))
    damage_img_url = db.Column(db.String(200))
    discovery_time = db.Column(db.String(200))
    longitude = db.Column(db.String(200))
    latitude = db.Column(db.String(200))
    stake_no = db.Column(db.String(200))


class tbl_road_damage_filter(db.Model):
    __tablename__ = 'tbl_road_damage_filter'
    id = db.Column(db.Integer, primary_key=True)
    damage_img = db.Column(db.Text)
    frame_number = db.Column(db.Integer)
    file_id = db.Column(db.Integer)
    damage_video = db.Column(db.String(200))
    damage_img_url = db.Column(db.String(200))
    discovery_time = db.Column(db.String(200))
    longitude = db.Column(db.String(200))
    latitude = db.Column(db.String(200))


class tbl_damages(db.Model):
    __tablename__ = 'tbl_damages'
    id = db.Column(db.Integer, primary_key=True)
    confidence = db.Column(db.String(20))
    location = db.Column(db.String(20))
    damage_tag = db.Column(db.String(20))
    damage_id = db.Column(db.Integer)


class tbl_damages_filter(db.Model):
    __tablename__ = 'tbl_damages_filter'
    id = db.Column(db.Integer, primary_key=True)
    confidence = db.Column(db.String(20))
    location = db.Column(db.String(20))
    damage_tag = db.Column(db.String(20))
    damage_id = db.Column(db.Integer)


@app.route('/pciGroup', methods=['post'])
def pciGroup():
    ret = {}
    data = []
    logging.info(flask.request.json)
    for oneJson in flask.request.json:
        startStake = oneJson['startStake']
        laneWidth = eval(oneJson['laneWidth'])
        tag_list = oneJson['roadDamageList']
        distype = eval(oneJson['type'])
        pci = calculate_pci_last(tag_list, laneWidth, distype, oneJson)
        oneRet = {}
        oneRet['startStake'] = startStake
        oneRet['pci'] = pci
        data.append(oneRet)
    ret['data'] = data
    ret['msg'] = 'ok'
    return json.dumps(ret)
    
# @app.route('/getFps', methods=['post'])
# def getFps():
#     ret = {}
#     logging.info(flask.request.json)
#     videoUrl = flask.request.json['videoUrl']
#     videoInfo, videoCapture = getVideoInfo(videoUrl)
#     videoCapture.release()
#     ret['data'] = videoInfo.fps
#     ret['msg'] = 'ok'
#     return json.dumps(ret)

@app.route('/getVideoInfo', methods=['post'])
def getVideoInfoApi():
    ret = {}
    logging.info(flask.request.json)
    videoUrl = flask.request.json['videoUrl']
    videoInfo, videoCapture = getVideoInfo(videoUrl)
    videoCapture.release()
    data = {}
    data['fps'] = videoInfo.fps
    data['width'] = videoInfo.width
    data['height'] = videoInfo.height
    data['frameCount'] = videoInfo.frameCount
    ret['data'] = data
    ret['msg'] = 'ok'
    return json.dumps(ret)

def convertNone(string):
    if string == 'None':
        string = ''
    return string

def save_image_and_tag(images):
    for image in images:
        db.session.execute(
            "insert into tbl_road_damage_filter(id,frame_number,file_id,damage_video,damage_img_url,"
            "discovery_time,device_sn,longitude,latitude,stake_no, org_img_url, area, mean) "
            "values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s', '%s', '%s', '%s')" % (
                convertNone(str(image['id'])), convertNone(str(image['frame_number'])),
                convertNone(str(image['file_id'])), convertNone(str(image['damage_video'])), convertNone(str(image['damage_img_url'])),
                convertNone(str(image['discovery_time'])), convertNone(str(image['device_sn'])), convertNone(str(image['longitude'])),
                convertNone(str(image['latitude'])), convertNone(str(image['stake_no'])), convertNone(str(image['org_img_url'])), 
                convertNone(str(image['area'])), convertNone(str(image['mean'])))
        )
        db.session.commit()    
        for tag in image['tags']:
            db.session.execute('insert into tbl_damages_filter(confidence, location, damage_tag, damage_id) values(:confidence, :location, :damage_tag, :damage_id)', 
            {"confidence":tag['confidence'],"location":tag['location'], "damage_tag":tag['damage_tag'], "damage_id":image["id"]})
            db.session.commit()  

def update(images, gps_file_url, fps):
    s = requests.get(gps_file_url).text.split('\r\n')
    gps_list = []
    for j in range(len(s) - 1):
        gpsdic = []
        distance = ast.literal_eval(s[j])['distance']
        gps_time = time.mktime(time.strptime(ast.literal_eval(s[j])['time'], '%Y-%m-%d %H:%M:%S'))
        gpsdic.append(gps_time)
        gpsdic.append(distance)
        gpsdic.append(ast.literal_eval(s[j])['latitude'])
        gpsdic.append(ast.literal_eval(s[j])['longitude'])
        gps_list.append(gpsdic)

    # gps_file_url例子，http://223.244.82.97:9001/roaddetection/20210813/SCOPAXYA88/2021072312022320210723120247.txt
    start = int(time.mktime(time.strptime(gps_file_url[-32:-18], '%Y%m%d%H%M%S')))
    #
    # 更新discovery_time 和经纬度==========================================
    for j in range(len(images)):
        dtime = int(images[j]["frame_number"] / fps + start)
        sdtime = str(int(images[j]["frame_number"] / fps + start)) + '000'
        images[j]['discovery_time'] = sdtime
        db.session.execute('update tbl_road_damage set discovery_time="%s" where id="%s"' %
                           (sdtime, str(images[j]["id"])))
        db.session.commit()

        # dis_time = [dict(zip(result.keys(), result)) for result in (db.session.execute(
        #     ' select discovery_time from tbl_road_damage where id = %s ' % str(image[j]["id"])))][0][
        #     "discovery_time"]
        for n in range(len(gps_list)):
            if dtime == int(gps_list[n][0]):
                images[j]['latitude'] = gps_list[n][2]
                images[j]['longitude'] = gps_list[n][3]
                db.session.execute(
                    'update tbl_road_damage set latitude="%s" where id="%s"' % (gps_list[n][2], images[j]["id"]))
                db.session.commit()
                db.session.execute(
                    'update tbl_road_damage set longitude="%s" where id="%s"' % (gps_list[n][3], images[j]["id"]))

                db.session.commit()
                break

    pass

def pci_video(file_id, tag_list, paras_dic):

    # 获取gps--------------------------
    gpss = db.session.execute(' select gps_file from tbl_file where id = %s ' % str(file_id))
    # 转化成字典列表
    gps = [dict(zip(result.keys(), result)) for result in gpss]
    # 取出链接地址，是一个str
    gpsurl = gps[0]['gps_file']
    # 取出4参数，计算比例关系

    pci1 = calculate_pci1(tag_list, gpsurl, paras_dic)
    pci = round(pci1, 2)

    db.session.execute('update tbl_file set pci="%s" where id="%s"' % (str(pci), str(file_id)))
    db.session.commit()
    return pci

@app.route('/process', methods=['post'])
def process():
    # -------------------------------------------------
    # 视频id
    pk = flask.request.json["pk"]
    #pk =721
    # 取出视频-----------------------------------------------------------------
    tbl_file = fetch_to_dict(db, ' select * from tbl_file where id=:id ', {'id':pk}, 'one')
    file_id = tbl_file["id"]
    video_file_url = tbl_file["video_file"]
    gps_file_url = tbl_file["gps_file"]
    record_id = tbl_file['record_id']

    # 获取比例关系的4个参数
    pci_params = fetch_to_dict(db, 'select lane_width,lane_high_pixel,lane_pixel_len,angle_left,angle_right from road_detection_record where id=:id',  {'id':record_id}, 'one')

    images = fetch_to_dict(db, ' select * from tbl_road_damage where file_id=:file_id', {'file_id':file_id})

    if images == None:
        msg = "Can not find file_id of : %s" % (file_id)
        logging.info(msg)
        ret = {}
        ret['msg'] = msg
        return json.dumps(ret)

    # 排序
    images = sorted(images, key=lambda img: img['frame_number'])

    videoInfo, videoCapture = getVideoInfo(video_file_url)
    # 更新damage表的经纬度，时间
    #update(images, gps_file_url, videoInfo.fps)

    # 帧间过滤
    # 会有问题，当fps较低时，每一帧几乎都是检测不同的路面
    #filter.filter_inter(images)

    lane_cross_high = filter.calc_lane_corss_high(eval(pci_params['lane_high_pixel']), eval(pci_params['lane_pixel_len']), eval(pci_params['angle_left']), eval(pci_params['angle_right']))
    y_threshold = int(videoInfo.height / 3)
    y_threshold = y_threshold if y_threshold > lane_cross_high else lane_cross_high
    # 帧内过滤，and add tags to images
    tag_list_filter = filter.filter_intra(images, y_threshold, db)

    stride = int(videoInfo.fps / 2)
    # 根据视频的fps选择过滤的间隔
    tag_list_filter = filter.filter_stride(images, stride)
    
    pci = pci_video(file_id, tag_list_filter, pci_params)
    logging.info("Pci of video: %d, is: %f" % (file_id, pci))
    #print("Pci of video: %d, is: %f" % (file_id, pci))    

    #draw_rectangle(video_file_url, images)

    mp4_path, fps, frame_count, avi_path = save_video_and_image(file_id, videoCapture, images)
    videoCapture.release()
    db.session.execute('update tbl_file set damage_video="%s" where id="%s"' % (mp4_path, str(file_id)))
    db.session.commit()
    # 使用ffmpeg截取前后3s视频，在生成的视频上截取
    # ffmpeg -i input.wmv -ss 30 -c copy -to 40 output.wmv
    # 从过滤数据表里面获取image
    for image in images:
        video_3s_path = get_3svideo(image['frame_number'], fps, frame_count, file_id, avi_path)
        image['damage_video'] = video_3s_path
        # db.session.execute('update tbl_road_damage_filter set damage_video="%s" where id="%s"' % (
        #     video_3s_path, str(image["id"])))
        # db.session.commit()
    logging.info("Analyse complete: " + str(file_id))
    #print("Analyse complete: " + str(file_id))
    os.remove(avi_path)

    save_image_and_tag(images)

    ret = {}
    ret['msg'] = 'ok'
    return json.dumps(ret)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0',port='5001')
    #process()
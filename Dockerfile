FROM  hz1943/ffmpeg_ssh:4.5

WORKDIR /app

RUN git clone https://github.com/hz1943/road_src.git

RUN apt update
RUN apt install -y libgl1-mesa-glx
RUN pip install opencv-python -i https://pypi.mirrors.ustc.edu.cn/simple

RUN pip install ffmpy -i https://pypi.mirrors.ustc.edu.cn/simple
RUN pip install   -r ./road_src/requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple --no-cache-dir

CMD [ "python","-u", "./road_src/app.py" ]
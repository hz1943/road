

FROM  hzru/base:v1.0



COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN apt update
RUN apt install -y libgl1-mesa-glx
RUN pip install opencv-python -i https://pypi.mirrors.ustc.edu.cn/simple

RUN pip install ffmpy -i https://pypi.mirrors.ustc.edu.cn/simple
RUN pip install   -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple --no-cache-dir

COPY . /app

CMD [ "python","-u", "./app.py" ]
from ard6s import Ard6S
from CN import Connect_Images

import os
import cv2
import time
import zmq
from threading import Thread
import shutil
import numpy as np
import configparser
import datetime

MTX_PATH = "./csv/mtx.csv"
DIST_PATH = "./csv/dist.csv"
CONF_FILEPATH = "./config_1/config.conf"

class Flags:
    def __init__(self):
        self.quit_flag = False
        self.suspend_flag = False
        self.exposure_flag = False


# def mock_move_to():
#     time.sleep(2)


class Move(Ard6S):
    def __init__(self):
        super().__init__()
        self.mtx, self.dist = self.loadCalibrationFile(MTX_PATH, DIST_PATH)
        self.config = configparser.ConfigParser()
        self.config.read(CONF_FILEPATH, 'UTF-8')
        self.config_connect = self.config['Connect']
        self.height = int(self.config_connect['height'])
        self.width1 = int(self.config_connect['width1'])
        self.width2 = int(self.config_connect['width2'])

        self.thread_shot = None
        self.status = "init"  # init | standby | shot | suspend | quit

        # self.cap = cv2.VideoCapture(2, cv2.CAP_DSHOW)
        self.cap = cv2.VideoCapture(2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)
        # self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        self.cap.set(cv2.CAP_PROP_EXPOSURE, -7)
        self.exposure = -7
        print(self.cap.read()[1].shape)

        self.flags = Flags()
        self.context = zmq.Context()
        self.sock_status = self.context.socket(zmq.PUSH)
        self.sock_status.bind("tcp://*:5001")
        print("状態送信用ソケット開始 port: 5001")
        self.sock_video = self.context.socket(zmq.PUSH)
        self.sock_video.bind("tcp://*:5002")
        print("カメラ画像送信用ソケット開始 port: 5002")

        self.invert_homing_axis(["A","B"])
        self.set_speed(A=500, B=500, C=1500)

        self.thread_send_frame = Thread(target=self.send_frame)
        self.thread_send_frame.start()

        self.blocksize = 3
        self.sub = 4

        self.homing()
        self.set_status("standby")  # finish initialize

    def close(self):
        self.flags.quit_flag = True
        if self.thread_shot is not None and self.thread_shot.is_alive():
            self.flags.suspend_flag = True
            self.thread_shot.join()
        self.thread_send_frame.join()
        self.sock_status.close()
        self.sock_video.close()
        self.context.destroy()

    def set_status(self, status):
        print("ステータスの変更: %s" % status)
        self.status = status
        send_data = {
            "type": "status",
            "data": status
        }
        self.sock_status.send_json(send_data)

    def homing(self):
        print("ホーミング中...")
        self.run_homing(["A", "B", "C"])
        self.set_current_position(A=0,B=0,C=0)
        self.move_to(C=-8000)
        print("ホーミング完了")

    def send_frame(self):
        print("カメラ画像の送信開始")   
        while not self.flags.quit_flag:
            if self.flags.exposure_flag:
                self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure)
                self.flags.exposure_flag = False
            _, frame = self.cap.read()
            resultImg = cv2.undistort(frame, self.mtx, self.dist, None)
            rgba_img = cv2.resize(cv2.cvtColor(resultImg, cv2.COLOR_BGR2RGBA),dsize=(1920,1080))
            # rgba_img = cv2.cvtColor(resultImg, cv2.COLOR_BGR2RGBA)
            self.sock_video.send(rgba_img)
        print("カメラ画像の送信終了")

    def take_image(self, vertical, horizontal):
        os.makedirs("fig", exist_ok=True)
        shutil.rmtree("fig")
        os.makedirs("fig", exist_ok=True)

        move_distance_x = 500
        move_distance_y = 8000
        x_min, y_min, x_max, y_max = 0, vertical, horizontal, 8000
        print(vertical)
        print(horizontal)

        x_count = (x_max-x_min)//move_distance_x+1
        y_count = (y_max-y_min)//move_distance_y+1

        for i in range(5):
            self.cap.read()

        count = 0
        for x in range(x_min, x_max+1, move_distance_x):
            for y in range(-y_max, -y_min+1, move_distance_y):
                self.move_to(A=x, B=x, C=y)
                time.sleep(2)
                y = abs(y)

                progress = 100 * count / (x_count*y_count) /2 # GUI表示用の進捗を算出(%)
                count += 1
                send_data = {
                    "type": "progress",
                    "data": progress
                }
                self.sock_status.send_json(send_data)

                image = self.cap.read()[1]
                resultImg = cv2.undistort(image, self.mtx, self.dist, None)
                resultImg = cv2.rotate(resultImg, cv2.ROTATE_90_COUNTERCLOCKWISE)


                Thread(target=cv2.imwrite, args=(
                    f'fig/{(x-x_min)//move_distance_x}_{(y-y_min)//move_distance_y}.png', resultImg), daemon=False).start()

                if self.flags.suspend_flag is True:
                    return

        print("撮影完了")

        # connect images
        img = self.connect_images(x_count, y_count, progress)
        if self.flags.suspend_flag is True:
            return
        progress = 100   # GUI表示用の進捗を算出(%)
        # print(progress)
        send_data = {
                    "type": "progress",
                    "data": progress
                }
        self.sock_status.send_json(send_data)

        self.ts = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # img_path = f"img/{ts}.png"
        self.img_path = os.path.abspath(f"img/{self.ts}.png")
        cv2.imwrite(self.img_path, img)

        self.img_b_path = self.binarization()

        send_data = {
            "type": "finished",
            "data": self.img_path
        }
        self.sock_status.send_json(send_data)
        # shutil.rmtree("fig")
        self.homing()
        self.set_status("standby")  # 撮影処理全体完了

    def start(self, vertical=2500, horizontal=8000):
        ##########################

        #vertical: 500, 1500, 2500
        #horizontal: 0, 8000

        ###########################
        # vertical = 500
        # horizontal = 0

        self.set_status("shot")
        # self.take_image(vertical=vertical, horizontal=horizontal)
        # self.thread_shot = Thread(target=self.take_image(vertical=vertical, horizontal=horizontal))
        self.thread_shot = Thread(target=self.take_image, args=(int(vertical), int(horizontal)))
        self.thread_shot.start()

    def suspend(self):
        self.flags.suspend_flag = True
        Thread(target=self.homing).start()
        if self.thread_shot.is_alive():
            self.thread_shot.join()
        self.flags.suspend_flag = False
        self.set_status("standby")  # 中断完了
    
    def connect_images(self, x_num=6, y_num=2, progress=91):
        os.makedirs("temp", exist_ok=True)
        shutil.rmtree("temp")
        os.makedirs("temp", exist_ok=True)

        os.makedirs("temp1", exist_ok=True)
        shutil.rmtree("temp1")
        os.makedirs("temp1", exist_ok=True)

        res_percent = 100 - progress
        res_percent_ratio = res_percent / (x_num*y_num)
        print(res_percent)
        print(res_percent_ratio)
        CN = Connect_Images()
        result_img =[]
        small_w=10000
        small_h = 10000

        print(f'xnum: {x_num}, ynum: {y_num}')

        # Phase 1
        print("###### Phase 1 ######")
        if y_num == 1:
            for i in range(x_num):
                    if self.flags.suspend_flag is True:
                        return 0
                    img = cv2.imread(f'fig/{i}_0.png')
                    cv2.imwrite(f"temp/image{i}.png", img)
        else:
            for i in range(x_num):
                if self.flags.suspend_flag is True:
                    return 0
                CN.update_images(f"fig/{i}_0.png",f"fig/{i}_1.png")
                pre_result_image = CN.auto_img_concat_v(compare_h=40, compare_w=1050, tri_h=500, tri_w=10, search_start=1100, search_h=300, limit_h_init=1229, limit_w_init=14)
                small_w = min(small_w,pre_result_image.shape[0])
                small_h = min(small_h,pre_result_image.shape[1])
                result_img.append(cv2.rotate(pre_result_image, cv2.ROTATE_90_COUNTERCLOCKWISE))
                cv2.imwrite(f"temp/image{i}.png",result_img[i])
                print("幅: ", small_w, "高さ:", small_h)
                progress += res_percent_ratio
                send_data = {
                    "type": "progress",
                    "data": progress
                }
                self.sock_status.send_json(send_data)

        # Phase 2
        print('########  Phase 2 ######')
        for i in range(0,x_num,2):
            if self.flags.suspend_flag is True:
                    return 0
            CN.update_images(f"temp/image{i}.png",f"temp/image{i+1}.png")
            if y_num == 1:
                CN.img1 = cv2.rotate(CN.img1, cv2.ROTATE_90_CLOCKWISE)
                CN.img2 = cv2.rotate(CN.img2, cv2.ROTATE_90_CLOCKWISE)
                second_image = CN.auto_img_concat_v(compare_h=40, compare_w=1900, tri_h=150, tri_w=10, search_start=600, search_h=300, limit_h_init=699, limit_w_init=14)
                small_w = second_image.shape[1]
                small_h = second_image.shape[0]     
            else:
                second_image = CN.auto_img_concat_v(compare_h=40, compare_w=2600, tri_h=100, tri_w=10, search_start=550, search_h=300, limit_h_init=649, limit_w_init=20)
            second_image = cv2.rotate(second_image, cv2.ROTATE_180)
            print("高さ:", second_image.shape[0])
            cv2.imwrite(f"temp1/image{i}.png",second_image)
            progress += res_percent_ratio
            send_data = {
                "type": "progress",
                "data": progress
            }
            self.sock_status.send_json(send_data)       
        
        if x_num == 2:
            final_image = cv2.imread("temp1/image0.png")
            final_image = cv2.rotate(final_image, cv2.ROTATE_90_CLOCKWISE)
            # cv2.imwrite("final.png", final_image)
            return final_image

        # Phase 3
        print('###### Phase 3 ######')
        CN.update_images("temp1/image0.png","temp1/image2.png")
        if self.flags.suspend_flag is True:
            return 0
        if y_num == 1:
            semi_image = CN.auto_img_concat_v(compare_h=20, compare_w=1860, tri_h=150, tri_w=10, search_start=1150, search_h=300, limit_h_init=1246, limit_w_init=20)
            small_w = semi_image.shape[1]
            small_h = semi_image.shape[0]
        else:
            semi_image = CN.auto_img_concat_v(compare_h=20, compare_w=2570, tri_h=150, tri_w=10, search_start=1100, search_h=300, limit_h_init=1239, limit_w_init=17)
        progress += res_percent_ratio
        send_data = {
            "type": "progress",
            "data": progress
        }
        self.sock_status.send_json(send_data)
        semi_image = cv2.rotate(semi_image, cv2.ROTATE_180)
        cv2.imwrite(f"temp1/semi.png",semi_image)

        print("高さ:",semi_image.shape[0])

        if x_num == 4:
            final_image = cv2.imread("temp1/semi.png")
            final_image = cv2.rotate(final_image, cv2.ROTATE_90_CLOCKWISE)
            # cv2.imwrite("final.png", final_image)
            return final_image

        # Phase 4
        print('###### Phase 4 ######')
        CN.update_images("temp1/semi.png","temp1/image4.png")
        if self.flags.suspend_flag is True:
            return 0
        if y_num == 1:
            final_image = CN.auto_img_concat_v(compare_h=20, compare_w=1820, tri_h=150, tri_w=20, search_start=2220, search_h=300, limit_h_init=2347, limit_w_init=15)
        else:
            final_image = CN.auto_img_concat_v(compare_h=20, compare_w=2540, tri_h=30, tri_w=20, search_start=2100, search_h=300, limit_h_init=2222, limit_w_init=13)
        progress += res_percent_ratio
        send_data = {
            "type": "progress",
            "data": progress
        }
        self.sock_status.send_json(send_data)
        final_image = cv2.rotate(final_image,cv2.ROTATE_90_COUNTERCLOCKWISE)
        # cv2.imwrite(f"final.png",final_image)

        return final_image

    def binarization(self):
        img = cv2.imread(self.img_path)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        th = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, self.blocksize, self.sub)
        self.img_b_path = f"img/{self.ts}_b.png"
        cv2.imwrite(self.img_b_path, th)
        return self.img_b_path
    
    def loadCalibrationFile(self, mtx_path, dist_path):
        try:
            mtx = np.loadtxt(mtx_path, delimiter=',')
            dist = np.loadtxt(dist_path, delimiter=',')
        except Exception as e:
            raise e
        return mtx, dist
        

if __name__ == "__main__":
    # サーバーの開始
    context = zmq.Context()
    sock = context.socket(zmq.REP)
    sock.bind("tcp://*:5000")
    print("リクエスト用サーバー起動 port: 5000")
    # Moveインスタンス作成
    move = Move()
    while True:
        msg = sock.recv_json()
        request = msg['type']
        print("リクエスト受信: %s" % request)
        if request == "quit":
            if move.status != "standby":
                print("動作中は終了できません。 status: %s" % move.status)
                sock.send_string("failed")
            else:
                print("終了します...")
                sock.send_string("success")
                break
        elif request == "shot":
            if move.status != "standby":
                print("撮影開始できません。 status: %s" % move.status)
                sock.send_string("failed")
            else:
                print("撮影開始...")
                sock.send_string("success")
                move.start(vertical=msg["vertical"], horizontal=msg["horizontal"])
                print("start完了")
        elif request == "suspend":
            if move.status != "shot":
                print("撮影中ではありません。 status: %s" % move.status)
                sock.send_string("failed")
            else:
                print("撮影中止...")
                move.set_status("suspend")
                Thread(target=move.suspend).start()
                sock.send_string("success")
        elif request == "change-exposure":
            move.exposure = msg["exposure"]
            move.flags.exposure_flag = True
            print(f"露光を{move.exposure}に変更")
            # move.print_settings()
            sock.send_string("success")
        # 二値化処理
        elif request == "change":
            move.blocksize = msg["blocksize"]
            move.sub = msg["sub"]
            img_b_path = move.binarization()

        else:
            print("不正なリクエストです")
            sock.send_string("invalid")
    # 終了処理
    move.close()
    del move
    sock.close()
    context.destroy()

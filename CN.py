import numpy as np
import cv2

class Connect_Images():
    def __init__(self):
        pass

    def update_images(self, img1_path, img2_path):
        self.img1 = cv2.imread(img1_path)
        self.img2 = cv2.imread(img2_path)
        print(f"img1: {not self.img1 is None}, img2: {not self.img2 is None}")

    def auto_img_concat_v(self, compare_h=50, compare_w=1050, tri_h=600, tri_w=10, search_start=1270, search_h=100, limit_h_init=1229, limit_w_init=14):

        self.upper_img = self.img1
        self.under_img = self.img2
        self.upper_img = cv2.rotate(self.upper_img, cv2.ROTATE_180)
        self.under_img = cv2.rotate(self.under_img, cv2.ROTATE_180)

        self.max_res_num = 0  # マッチング評価結果の最大値を保存
        self.limit_w = 0
        self.limit_h = 0  # マッチング評価最大時,切り出した画像の位置を保存

        self.upper_h = self.upper_img.shape[0]
        self.upper_w = self.upper_img.shape[1]
        self.under_h = self.under_img.shape[0]
        self.under_w = self.under_img.shape[1]

        # 比較するピクセル数 compare_h=50, compare_w=920

        # 検索範囲 (幅は画像の幅、)
        self.search_start = search_start
        self.search_h = search_h
        self.search_w = self.upper_w

        # 上画像の高さが高い場合、差分を取得（そうでない場合は0）
        # dif_h = (upper_h - under_h) if upper_h > under_h else 0

        # 横方向に動かす幅
        self.num_w = self.search_w-compare_w
        # 縦方向に動かす幅
        self.num_h = self.search_h-compare_h

        print("動かす幅 ", "h:", self.num_h, " w:", self.num_w)

        for i in range(0, self.num_w, 1):
            for j in range(0, self.num_h, 1):

                # 切り出すupper画像の切り出す部分
                '''
                ws-------------we
                hs
                |
                |
                |
                he
                '''
                self.search_hs = self.search_start+j
                self.search_he = self.search_hs+compare_h
                self.search_ws = i
                self.search_we = self.search_ws+compare_w

                # 画像切り出し
                # 上画像のトリミング
                self.search_img = self.upper_img[self.search_hs: self.search_he, self.search_ws: self.search_we, :]
                # 下画像のトリミング
                self.target_img = self.under_img[tri_h: tri_h + compare_h, tri_w: tri_w+compare_w, :]

                # if i==0:
                #     cv2.imwrite(f"temp/search{j}.png",self.search_img)
                # if j == 0 and i==0:
                #     cv2.imwrite(f"temp/target{i}.png",self.target_img)

                self.cv_search_img = cv2.cvtColor(self.search_img, cv2.COLOR_RGB2GRAY)  # グレースケール化（上画像）
                self.cv_target_img = cv2.cvtColor(self.target_img, cv2.COLOR_RGB2GRAY)  # 　　　〃　　　（下画像）

                # マッチング評価（出力は類似度を表すグレースケール画像）
                self.res = cv2.matchTemplate(self.cv_search_img, self.cv_target_img, cv2.TM_CCOEFF_NORMED)
                self.res_num = cv2.minMaxLoc(self.res)[1]  # マッチング評価を数値で取得
                # print(self.res_num, " ", "w方向に動かしたピクセル　",i," ", "h方向に動かしたピクセル　",j)

                if self.max_res_num < self.res_num:  # マッチング評価結果の最大値を取得
                    self.max_res_num = self.res_num
                    self.limit_w = self.search_ws  # マッチング評価最大時,切り出した画像の位置
                    self.limit_h = self.search_hs
                
                # if self.max_res_num >= 0.97 and abs(limit_h_init-self.limit_h) <= 5 and abs(limit_w_init-self.limit_w) <= 5:
                if self.max_res_num >= 0.985:
                    break

        print("\n", self.max_res_num, "\n", self.limit_h, self.limit_w)
        print(f"init_h: {limit_h_init} init_w: {limit_w_init}")

        # if (self.max_res_num <= 0.85 or abs(limit_h_init-self.limit_h) >= 10 or abs(limit_w_init-self.limit_w) >= 10):
        if self.max_res_num <= 0.85:
             self.limit_h = limit_h_init
             self.limit_w = limit_w_init

        # print(f"upper: {self.upper_img.shape}")
        # print(f"under: {self.under_img.shape}")
        
        self.upper_img = self.upper_img[0: self.limit_h, self.limit_w: self.limit_w+compare_w, :]
        self.under_img = self.under_img[tri_h: self.under_h, tri_w: tri_w+compare_w, :]
        # print(f"upper: {self.upper_img.shape}")
        # print(f"under: {self.under_img.shape}")
        self.result_img = cv2.vconcat([self.upper_img, self.under_img])
        return self.result_img
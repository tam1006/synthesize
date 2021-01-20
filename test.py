from CN import Connect_Images
import numpy as np
import cv2
import os
import shutil
import time

def connect_images(x_num=6, y_num=2):
    os.makedirs("temp", exist_ok=True)
    shutil.rmtree("temp")
    os.makedirs("temp", exist_ok=True)

    os.makedirs("temp1", exist_ok=True)
    shutil.rmtree("temp1")
    os.makedirs("temp1", exist_ok=True)

    CN = Connect_Images()
    result_img = []
    small_w = 10000
    small_h = 10000

    print(f'xnum: {x_num}, ynum: {y_num}')

    # Phase 1
    print("Phase 1")
    if y_num == 1:
        for i in range(x_num):
                # if self.flags.suspend_flag is True:
                #     return 0
                img = cv2.imread(f'fig/{i}_0.png')
                cv2.imwrite(f"temp/image{i}.png", img)
    else:
        for i in range(x_num):
            # if self.flags.suspend_flag is True:
            #     return 0
            CN.update_images(f"fig/{i}_0.png", f"fig/{i}_1.png")
            pre_result_image = CN.auto_img_concat_v(
                compare_h=40, compare_w=1050, tri_h=500, tri_w=10, search_start=1170, search_h=100, limit_h_init=1229, limit_w_init=14)
            small_w = min(small_w, pre_result_image.shape[0])
            small_h = min(small_h, pre_result_image.shape[1])
            result_img.append(cv2.rotate(
                pre_result_image, cv2.ROTATE_90_COUNTERCLOCKWISE))
            cv2.imwrite(f"temp/image{i}.png", result_img[i])
            print("幅: ", small_w, "高さ:", small_h)

    # Phase 2
    print('Phase 2')
    for i in range(0, x_num,2):
        # if self.flags.suspend_flag is True:
        #         return 0
        CN.update_images(f"temp/image{i}.png", f"temp/image{i+1}.png")
        if y_num == 1:
            CN.img1 = cv2.rotate(CN.img1, cv2.ROTATE_90_CLOCKWISE)
            CN.img2 = cv2.rotate(CN.img2, cv2.ROTATE_90_CLOCKWISE)
            second_image = CN.auto_img_concat_v(compare_h=40, compare_w=1900, tri_h=150, tri_w=10, search_start=670, search_h=100, limit_h_init=699, limit_w_init=14)
            small_w = second_image.shape[1]
            small_h = second_image.shape[0]
        else:
            second_image = CN.auto_img_concat_v(
                compare_h=40, compare_w=2600, tri_h=100, tri_w=10, search_start=630, search_h=60, limit_h_init=649, limit_w_init=20)
        second_image = cv2.rotate(second_image, cv2.ROTATE_180)
        print("高さ:", second_image.shape[0])
        cv2.imwrite(f"temp1/image{i}.png", second_image)

    if x_num == 2:
        final_image = cv2.imread("temp1/image0.png")
        final_image = cv2.rotate(final_image,cv2.ROTATE_90_CLOCKWISE)
        cv2.imwrite("final.png", final_image)
        return final_image

    # Phase 3
    print('Phase 3')
    CN.update_images("temp1/image0.png", "temp1/image2.png")
    # if self.flags.suspend_flag is True:
    #     return 0
    if y_num == 1:
        semi_image = CN.auto_img_concat_v(compare_h=20, compare_w=1860, tri_h=150, tri_w=10, search_start=1210, search_h=100, limit_h_init=1246, limit_w_init=20)
        small_w = semi_image.shape[1]
        small_h = semi_image.shape[0]
    else:
        semi_image = CN.auto_img_concat_v(compare_h=20, compare_w=2570, tri_h=150,
                                            tri_w=10, search_start=1190, search_h=100, limit_h_init=1239, limit_w_init=17)
    semi_image = cv2.rotate(semi_image, cv2.ROTATE_180)
    cv2.imwrite(f"temp1/semi.png", semi_image)

    print("高さ:", semi_image.shape[0])

    if x_num == 4:
        final_image = cv2.imread("temp1/semi.png")
        final_image = cv2.rotate(final_image, cv2.ROTATE_90_CLOCKWISE)
        cv2.imwrite("final.png", final_image)
        return final_image

    # Phase 4
    print('Phase 4')
    CN.update_images("temp1/semi.png", "temp1/image4.png")
    # if self.flags.suspend_flag is True:
    #     return 0
    if y_num == 1:
        final_image = CN.auto_img_concat_v(compare_h=20, compare_w=1820, tri_h=150, tri_w=20, search_start=2310, search_h=100, limit_h_init=2347, limit_w_init=15)
    else:
        final_image = CN.auto_img_concat_v(
            compare_h=20, compare_w=2540, tri_h=30, tri_w=20, search_start=2190, search_h=100, limit_h_init=2222, limit_w_init=13)
    final_image = cv2.rotate(final_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    # final_image = cv2.rotate(final_image, cv2.ROTATE_180)
    cv2.imwrite("final.png", final_image)

    return final_image

if __name__ == "__main__":
    a = connect_images(x_num=6, y_num=2)
    # print(a.shape)
    # cv2.imshow('final.png', cv2.resize(a, (640, 480)))
    # cv2.waitKey(1)
    # time.sleep(2)

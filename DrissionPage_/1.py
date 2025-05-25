from DrissionPage import Chromium,ChromiumOptions
from PIL import Image

import base64
import requests

def verify(b):
    url = "http://api.jfbym.com/api/YmServer/customApi"
    data = {
        ## 关于参数,一般来说有3个;不同类型id可能有不同的参数个数和参数名,找客服获取
        "token": "wCf9XIoP0pc8N0jCXrsu0wflKCfIldMylDex1twqQ6g",
        "type": "20110",
        "image": b,
    }
    _headers = {
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, headers=_headers, json=data).json()
    print(response)
    return response.get('data').get('data')



co = ChromiumOptions()
co.new_env(True)
co.no_js(True)
tab = Chromium(co).latest_tab
tab.get('https://www.leroymerlin.es/')
frame1 = tab.get_frame(1)
# frame1.actions.hold('.slider').right(138).release()

# captcha__element
# img = frame1('#captcha__element')
frame1.actions.hold()
frame1.get_screenshot()
bytes_str = frame1.get_screenshot(as_bytes='png')  # 返回截图二进制文本

# 打开原始图片
img = Image.open('iframe.jpg')
# 截取指定区域
cropped_img = img.crop((473, 422, 823, 745))
# 保存或显示裁剪后的图片
cropped_img.save('iframe.jpg')
# www.jfbym.com  注册后登录去用户中心
with open('iframe.jpg', 'rb') as f:
    b = base64.b64encode(f.read()).decode()  ## 图片二进制流base64字符串
verify_data = int(int(verify(b)) * 0.912)
print(verify_data)
frame1.actions.hold('.slider')
frame1.actions.hold('.slider').right(verify_data).release()
# 473,412
# 825,740
# tab.actions.click('@captcha-mode=embed')
# tab.actions.hold('.yidun_slider  yidun_slider--hover ').right(300).release()
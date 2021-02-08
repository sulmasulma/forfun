# -*- coding: utf-8 -*-
import time, os, sys
# sys.path.append('./libs') # libs 폴더에 들어있는 라이브러리를 사용하도록 configure
import logging, pickle, requests, json, base64
from urllib import parse
from datetime import datetime

# 크롤링
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
from tqdm import tqdm
from urllib.request import urlretrieve

# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# initiate slack bot
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
client = WebClient(token=slack_bot_token)

conversations_store = {}


# 채널 목록 dict에 저장
def save_conversations(conversations):
    conversation_id = ""

    for conversation in conversations:
        conversation_id = conversation["id"]
        conversations_store[conversation_id] = conversation

    return conversations_store


# 채널 목록 가져오기
def fetch_conversations():
    try:
        result = client.conversations_list()
        save_conversations(result["channels"])

    except SlackApiError as e:
        logger.error("Error fetching conversations: {}".format(e))


# 텍스트 쓰기 (client 이용)
def post_message(channel_id, message):
    try:
        # Call the chat.postMessage method using the WebClient
        result = client.chat_postMessage(
            channel=channel_id, # id 대신 '#채널명' 으로 적어도 됨 
            text=message
        )
        logger.info(result)

    except SlackApiError as e:
        logger.error(f"Error posting message: {e}")


# 텍스트 쓰기 (api endpoint 이용)
def post_message_raw(channel_id, message):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Authorization": "Bearer {}".format(slack_bot_token)
    }

    params = {
        "channel": channel_id,
        "text": message
    }

    r = requests.post(url, headers=headers, params=params)
    print(json.loads(r.text))


# 파일 올리기 (client 이용)
def upload_file(channel_id, file_name):
    try:
        # Call the files.upload method using the WebClient
        # Uploading files requires the `files:write` scope
        result = client.files_upload(
            channels = channel_id,
            initial_comment = "오늘의 아린", # 이미지와 같이 들어가는 텍스트
            file = file_name,
        )
        # Log the result
        logger.info(result)

    except SlackApiError as e:
        logger.error("Error uploading file: {}".format(e))


# 파일 올리기 (api endpoint 이용) -> 이 함수는 현재 오류
def upload_file_raw(channel_id, file_name):
    url = "https://slack.com/api/files.upload"
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Authorization": "Bearer {}".format(slack_bot_token)
    }

    params = {
        "channels": channel_id,
        "file": file_name
    }

    r = requests.post(url, headers=headers, params=params)
    print(json.loads(r.text))


# 네이버 사진 크롤링
def scrap_photo_naver():
    keyword = '아린'

    # 1. 웹 접속 - 네이버 이미지 접속
    print('Loading...')
    driver = webdriver.Chrome('../../chromedriver')
    driver.implicitly_wait(30) # 브라우저 오픈시까지 대기

    before_src = ""

    #개요에서 설명했다시피 google이 아니라 naver에서 긁어왔으며, 
    #추가적으로 나는 1027x760이상의 고화질의 해상도가 필요해서 아래와 같이 추가적인 옵션이 달려있다.
    # 고화질 사진 코드
    keyword = '아린'
    url = "https://search.naver.com/search.naver?where=image&section=image&query={}&res_fr=786432&res_to=100000000&sm=tab_opt&color=&ccl=0&nso=so%3Ar%2Cp%3A1w%2Ca%3Aall&datetype=2&startdate=&enddate=&gif=0&optStr=dr".format(keyword) # 7일 고화질 쿼리
    # url = "https://search.naver.com/search.naver?where=image&section=image&query={}&res_fr=786432&res_to=100000000\
    #     &sm=tab_opt&color=&ccl=0&nso=so%3Ar%2Ca%3Aall%2Cp%3A1w&datetype=2&startdate=0&enddate=0&gif=0&optStr=rd&nq=&dq=\
    #     &rq=&tq=#imgId=image_sas%3Ablog146041157%7C20%7C222227290623_2019645439".format(keyword)


    #해당 경로로 브라우져를 오픈해준다.
    driver.get(url)
    time.sleep(1)


    photo_list = driver.find_elements_by_xpath("//*[@id='main_pack']/section/div/div[1]/div[1]/div")

    # 폴더 없으면 새로 만들기
    # location_name = 'arin'
    if not os.path.isdir('./{}'.format(keyword)):
        os.mkdir('./{}'.format(keyword))
        print('Create new directory!')
    else:
        print('Image updates!')

    index = 1
    for img in photo_list[:5]:
        #위의 큰 이미지를 구하기 위해 위의 태그의 리스트를 하나씩 클릭한다.
        img.click()
        
        #한번에 많은 접속을 하여 image를 크롤링하게 되면 naver, google서버에서 우리의 IP를 10~20분
        #정도 차단을 하게된다. 때문에 Crawling하는 간격을 주어 IP 차단을 피하도록 장치를 넣어주었다.
        time.sleep(1)
        
        # # #확대된 이미지의 정보는 img태그의 _image_source라는 class안에 담겨있다.
        html_objects = driver.find_element_by_css_selector('div.image._imageBox > img')
        # print(html_objects)
        current_src = html_objects.get_attribute('src')

        if before_src == current_src:
            continue
        elif before_src != current_src:
            before_src = current_src
            filename = "./{}/{}_{}.jpg".format(keyword, keyword, index)
            print("{}번째 이미지 저장 완료!".format(index))
            urlretrieve(current_src, filename)
            index += 1

    driver.close()

    print('Download complete!')


def scrap_photo_google():
    keyword = '아린'
    
    # 1. 웹 접속 - 구글
    print('Loading...')
    driver = webdriver.Chrome('../../chromedriver')
    driver.implicitly_wait(30) # 브라우저 오픈시까지 대기

    # 고화질 쿼리
    url = "https://www.google.com/search?q={}&tbm=isch&hl=ko&safe=images&tbs=qdr:m%2Cisz:lt%2Cislt:svga".format(keyword)
    driver.get(url)

    # 2. 이미지 링크 수집
    photo_list = driver.find_elements_by_css_selector('img.rg_i')

    # 폴더 없으면 새로 만들기
    # location_name = 'arin'
    if not os.path.isdir('./{}'.format(keyword)):
        os.mkdir('./{}'.format(keyword))
        print('Create new directory!')
    else:
        print('Image updates!')

    img = photo_list[0] # 첫번째 사진 받기
    img.click()

    time.sleep(1)
    html_objects = driver.find_element_by_css_selector('img.n3VNCb')
    src = html_objects.get_attribute('src')

    filename = "./{}/{}_{}.jpg".format(keyword, keyword, str(datetime.today().date()))
    urlretrieve(src, filename)

    driver.close()

    print('Download complete!')



def main():
    # fetch_conversations()

    # # 채널 목록 보기
    # for key in conversations_store.keys():
    #     print(conversations_store[key]['id'], conversations_store[key]['name'])

    # 텍스트 쓰기
    # post_message(channel_arin, "메시지 테스트")
    # post_message_raw(channel_arin, "메시지 테스트")

    # 크롤링
    scrap_photo_google()

    # slack에 파일 올리기
    photo_location = "./아린"
    photo = "/아린_{}.jpg".format(str(datetime.today().date())) # gif -> jpg로 저장해도 움직임
    upload_file("#아린", photo_location + photo) # channel id 말고 이름으로 써도 됨

    

if __name__ == "__main__":
    main()
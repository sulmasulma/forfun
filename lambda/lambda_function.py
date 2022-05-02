# -*- coding: utf-8 -*-
import time, os, sys
# sys.path.append('./libs') # libs 대신 Layers 이용하여 라이브러리 configure
import logging, requests, json, random
from datetime import datetime, timezone, timedelta

# 크롤링
from selenium import webdriver
from urllib.request import urlretrieve, urlopen, Request
from urllib import parse

# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

### for linux ###
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

# chrome for lambda layer
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1280x1696')
chrome_options.add_argument('--user-data-dir=/tmp/user-data')
chrome_options.add_argument('--hide-scrollbars')
chrome_options.add_argument('--enable-logging')
chrome_options.add_argument('--log-level=0')
chrome_options.add_argument('--v=99')
chrome_options.add_argument('--single-process')
chrome_options.add_argument('--data-path=/tmp/data-path')
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--homedir=/tmp')
chrome_options.add_argument('--disk-cache-dir=/tmp/cache-dir')
chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
chrome_options.binary_location = "/opt/python/bin/headless-chromium"

driver = webdriver.Chrome('/opt/python/bin/chromedriver', chrome_options=chrome_options)

# 웹 접속 - 구글
print('Loading...')
driver.implicitly_wait(30) # 브라우저 오픈시까지 대기

# logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# initiate slack bot
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
client = WebClient(token=slack_bot_token)

# 전역 변수
conversations_store = {} # 채널 목록 저장
file_type = ""
KST = timezone(timedelta(hours=9))
date_now = str(datetime.now(tz=KST).date()) # OS 시간이 아닌, 한국 시간으로 설정


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
        # logger.error(f"Error posting message: {e}")
        logger.error("Error posting message: {}".format(e))


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
def upload_file(channel_id, file_name, is_initial = False):
    try:
        # Call the files.upload method using the WebClient
        # Uploading files requires the `files:write` scope
        if is_initial:
            result = client.files_upload(
                channels = channel_id,
                initial_comment = "<!channel>", # 이미지와 같이 들어가는 텍스트. 공지 처리
                file = file_name,
            )
        else:
            result = client.files_upload(
                channels = channel_id,
                file = file_name,
            )   

        # Log the result
        logger.info(result)

    except SlackApiError as e:
        logger.error("Error uploading file: {}".format(e))


# 구글 사진 크롤링
def scrap_photo_google(keyword):

    keyword_parse = parse.quote(keyword) # url에 넣는 용도

    # 고화질(800x600보다 큰 이미지) + 최근 1주로 검색하는 url
    # url = "https://www.google.com/search?q={}&tbm=isch&hl=ko&safe=images&tbs=qdr:m%2Cisz:lt%2Cislt:svga".format(keyword) # 최근 1달
    # url = "https://www.google.com/search?q={}&tbm=isch&hl=ko&safe=images&tbs=qdr:w%2Cisz:lt%2Cislt:svga".format(keyword) # 최근 1주
    url = "https://www.google.com/search?q={}&tbm=isch&hl=ko&safe=images&tbs=itp:animated".format(keyword_parse) # gif(전체 기간)
    driver.get(url) # cron 실행시 여기서 에러 발생

    # 1.5 페이지 스크롤 다운 - 페이지를 스크롤 하여 더 많은 사진을 수집
    # 1초에 한번씩 3번 반복하여 페이지 다운 스크롤
    # body = driver.find_element_by_css_selector('body')
    body = driver.find_element(By.CSS_SELECTOR, 'body')
    for _ in range(10):
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(1)

    # 2. 검색 결과 이미지들 수집(썸네일)
    # photo_list = driver.find_elements_by_css_selector('img.rg_i')
    photo_list = driver.find_elements(By.CSS_SELECTOR, 'img.rg_i') # .rg_i.Q4LuWd

    # 날짜별 중복을 피하기 위해, 결과 중 상위 n개 결과 랜덤으로 고르기. 배열 길이가 300이어도 299번째 요소를 접근할 수는 없는 것 같음
    while True:
        idx = random.randrange(150) # n
        print("{}번째 사진 고르기".format(idx + 1))
        img = photo_list[idx]
        try:
            img.click()
            time.sleep(5) # 이미지 클릭후 로딩까지 잠시 대기

            # html_objects = driver.find_element_by_css_selector('img.n3VNCb') # 이게 틀린 듯. 잘못된 걸 찾음
            # html_objects = driver.find_element_by_xpath('//*[@id="islrg"]/div[1]/div[{}]/a[1]/div[1]/img'.format(str(idx + 1)))
            # html_objects = driver.find_element_by_xpath('//*[@id="Sva75c"]/div/div/div[3]/div[2]/c-wiz/div/div[1]/div[1]/div[2]/div[1]/a/img') # xpath 변경
            html_objects = driver.find_element(By.XPATH, '//*[@id="Sva75c"]/div/div/div[3]/div[2]/c-wiz/div/div[1]/div[1]/div[3]/div/a/img') # 문법 및 xpath 수정
            src = html_objects.get_attribute('src')
            global file_type
            file_type = src[-3:]

            # src가 http로 시작하는 것만으로 가져오기
            if src[:4] == 'http' and file_type in ['gif', 'png', 'jpg']:
                print("{} gif 정상 성공!".format(keyword))
                break
            
            print("http 형식 아님. 다시 찾기")

        except Exception as e:
            logger.error("Exception 에러: {}".format(e))
            continue

    # 파일 저장. Request + urlopen 사용
    filename = "/tmp/{}_{}.{}".format(keyword, date_now, file_type) # lambda에선 /tmp/ 에만 file write 가능
    # print(os.getcwd()) # /var/task

    headers = {'User-Agent': 'whatever'} # 403 에러 방지. 'Chrome/88.0.4324.27'(버전 맞춰줌) or 'whatever'
    req = Request(src, headers=headers)
    html = urlopen(req)
    source = html.read()

    with open(filename, "wb") as f:
        f.write(source)

    print('Download complete!')


def lambda_handler(event, context):
    # fetch_conversations()

    # # 채널 목록 보기
    # for key in conversations_store.keys():
    #     print(conversations_store[key]['id'], conversations_store[key]['name'])

    # 텍스트 쓰기
    # post_message('#아린', "메시지 테스트")

    # 여러장 올리기
    # keywords = ['오마이걸 아린', '조유리', '오마이걸 유아', '있지 예지']
    keywords = ['오마이걸 아린', '조유리', '아이브 안유진', '있지 예지']
    for keyword in keywords:
        scrap_photo_google(keyword)

        # slack에 파일 올리기
        photo = "/tmp/{}_{}.{}".format(keyword, date_now, file_type)

        # 채널 구분
        if keyword == '오마이걸 아린':
            upload_file("#아린", photo) # channel id 말고 이름으로 써도 됨
        else:
            upload_file("#아이돌", photo, True) # 다른 채널. with initial comment

    # 드라이버 닫으면 cron job 작동이 되지 않음
    # driver.close()

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Matthew!')
    }

import os, sys
# sys.path.append('./libs') # libs 폴더에 들어있는 라이브러리를 사용하도록 configure
import logging, pickle, requests, json, base64
from urllib import parse

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
            channels=channel_id,
            initial_comment="오늘의 아린 사진",
            file=file_name,
            # as_user=True
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


def main():

    fetch_conversations()

    # 채널 목록 보기
    for key in conversations_store.keys():
        print(conversations_store[key]['id'], conversations_store[key]['name'])

    # 텍스트 쓰기
    # post_message(channel_arin, "메시지 테스트")
    # post_message_raw(channel_arin, "메시지 테스트")

    # 파일 올리기
    photo_location = "./image.png"
    upload_file("#아린", photo_location) # channel id 말고 이름으로 써도 됨

    

if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
# 도서관 사이트 크롤링하여, 노트북실에 빈 자리 나면 메일 보내는 코드
# 참고: http://hleecaster.com/python-email-automation/
from selenium import webdriver
from bs4 import BeautifulSoup
import time

import smtplib, os, pickle # smtplib: 메일 전송을 위한 패키지
from email.mime.multipart import MIMEMultipart # 메시지를 보낼 때 메시지에 대한 모듈
from email.mime.text import MIMEText # 본문내용을 전송할 때 사용되는 모듈
# from email import encoders # 파일전송을 할 때 이미지나 문서 동영상 등의 파일을 문자열로 변환할 때 사용할 패키지
# from email.mime.base import MIMEBase # 파일을 전송할 때 사용되는 모듈

# SMTP 접속을 위한 서버, 계정 설정
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# 발신자 계정, 비밀번호
SMTP_USER = "발신자 메일"
SMTP_PASSWORD = "발신자 비밀번호"

# 수신자 계정
addr = "수신자 메일"

# 이메일 유효성 검사 함수
def is_valid(addr):
    import re
    if re.match('(^[a-zA-Z-0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)', addr):
        return True
    else:
        return False

# 이메일 보내기 함수
def send_mail(addr, subj_layout, cont_layout, attachment=None):
    if not is_valid(addr):
        print("Wrong email: " + addr)
        return
    
    # 텍스트 파일
    msg = MIMEMultipart("alternative")
    # 첨부파일이 있는 경우 mixed로 multipart 생성
    if attachment:
        msg = MIMEMultipart('mixed')
    msg["From"] = SMTP_USER
    msg["To"] = addr
    msg["Subject"] = subj_layout
    contents = cont_layout
    text = MIMEText(_text = contents, _charset = "utf-8")
    msg.attach(text)
    # 첨부파일이 있으면
    if attachment:
        from email.mime.base import MIMEBase
        from email import encoders
        file_data = MIMEBase("application", "octect-stream")
        file_data.set_payload(open(attachment, "rb").read())
        encoders.encode_base64(file_data)
        filename = os.path.basename(attachment)
        file_data.add_header("Content-Disposition", 'attachment', filename=('UTF-8', '', filename))
        msg.attach(file_data)
    # smtp로 접속할 서버 정보를 가진 클래스변수 생성
    smtp = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    # 해당 서버로 로그인
    smtp.login(SMTP_USER, SMTP_PASSWORD)
    # 메일 발송
    smtp.sendmail(SMTP_USER, addr, msg.as_string())
    # 닫기
    smtp.close()

def main():
    driver = webdriver.Chrome('../../chromedriver')
    url = '사이트 주소'
    driver.get(url)
    i = 0

    while True:
        i += 1
        print("{}번째 시도..".format(i))
        html = driver.find_element_by_id('maptemp').get_attribute('innerHTML')
        soup = BeautifulSoup(html, 'html.parser')

        # 원하는 자리: 309~360, 369~388
        # 비었을 때 색: #5AB6CF
        # 찼을 때 색: #C9C9C9
        data = []
        for ele in soup.find_all('div')[1:]: # 1번째부터 각 자리를 나타내는 div 태그
            d = ele.table.tbody.tr.td
            num = int(d.font.get_text())
            color = d.get('bgcolor')
            # 원하는 자리 났을 경우, 리스트에 자리와 색 넣기
            if any([309 <= num <= 360, 377 <= num <= 384]) and color == "#5AB6CF":
                data.append([num, color])

        # 파란색으로 바뀌었으면 메일 보내기
        if data:
            cont = ' '.join([str(d[0]) for d in data])
            cont += '\n'
            cont += '사이트 주소'
            send_mail(addr, '노트북실 자리가 났습니다!!', cont)
            print("자리 났음!! 종료")
            driver.quit() # 드라이버 완전히 종료. 창 하나만 닫으려면 .close()
            break

        # 20초마다 새로고침하여 반복
        time.sleep(20)
        driver.refresh()


if __name__ == "__main__":
    main()
### 프로그램 개요
트레이딩뷰의 얼러트를 메일로 수신하여, 거래소 API를 통해 자동매매를 실현함.


### 요구사항
Python 3.6.7이상



### 설치목록

~~~
pip install pybithumb pandas
pip install python-telegram-bot
~~~



### config 파일 생성
configs폴더에 'sample_'로 시작하는 샘플 파일이 있습니다.
해당 샘플 파일을 아래와 같이 수정하여 사용하시면 됩니다

#### Ants config
~~~
./configs/ants.conf
~~~

#### Mail config
~~~
./configs/mail.key
~~~
메일지원 : 네이버 IMAP 설정 (OTP 미지원)

#### Exchange config
거래소 지정파일은 자동으로 생성됩니다. 자동 생성을 위해서는 아래의 프로그램을 사용하여야합니다.
~~~
python exchange/crypt_cli.py [add/test] [exchange name]
~~~

ex) upbit key 추가
~~~
$ exchange/crypt_cli.py add upbit
input key :
secret key :
config file save done
exchange connection test with key
test pass
~~~

ex) bithumb key 추가
~~~
$ exchange/crypt_cli.py add bithumb
~~~

ex) binance key 추가
~~~
$ exchange/crypt_cli.py add bithumb
~~~

ex) upbit key 연결 테스트
~~~
$ exchange/crypt_cli.py test upbit
exchange connection test with key
test pass
~~~


### 트레이딩뷰 얼러트 설정

~~~
#BTC/KRW #1M #SELL #BITHUMB
#종목심볼/마켓 #봉 #BUY/SELL타입 #거래소
~~~
얼러트 내용부분을 위의 형태로 적용.


### 실행

~~~
python ./ants/ants.py
~~~


### 지원거래소

#### 업비트
#### 빗썸
#### 바이낸스


### 주의사항

> 해당 프로그램으로 직접 투자시 위험부담은 투자자 본인에게 있습니다.

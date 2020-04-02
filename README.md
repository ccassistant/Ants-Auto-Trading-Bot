### 프로그램 개요
다양한 전략을 작성하여 전략에 맞춰 자동매매를 수행하는 것이 목표입니다
지원되는 전략
1. 트레이딩뷰의 얼러트를 메일로 수신하여, 거래소 API를 통해 자동매매를 실현함.
</br>

### 요구사항
Python 3.6.7

3.7버젼에서 오류가 발생합니다.</p>
</p>
</p>

</br>


### 설치목록

~~~
pip install -U -r requirements.txt
~~~

~~~
python3 -m venv `pwd`/venv_ants
~~~
</br>

### config 파일 생성
configs폴더에 'sample_'로 시작하는 샘플 파일이 있습니다.<p>
해당 샘플 파일을 아래와 같이 수정하여 사용하시면 됩니다<p>
</br>


#### Ants config
프로그램 동작에 관여하는 설정.</p> 
RSA키와 어떤 전략을 사용할지 결정합니다.</p>
~~~
./configs/ants.conf
~~~
RSA키를 설정하는 방법은 다양한데 pem포멧 RSA만 지원합니다</p>
윈도우 10의 경우 ssh-keygen을 사용하시면 됩니다</p>
윈도우 7의 경우 git-bash를 받으신 후 ssh-keygen을 사용하시면됩니다.</p>
이 때 private key 포멧을 pem으로 지정해주셔야 동작합니다.</p>

우분투 18.04의 경우 ssh-keygen(?)으로 생성하시면 됩니다.</p>
</br>
  
#### Mail config
메일을 사용하는 전략일 경우 imap에 관한 설정을 합니다.</p>
~~~
./configs/mail.key
~~~
메일지원 : 네이버 IMAP 설정 (OTP 미지원)</p>
</br>
</br>

#### Exchange Key
거래소 KEY 파일은 다음의 툴을 사용하여 암호화된 파일로 자동으로 생성됩니다.</p>
자동 생성을 위해서는 아래의 프로그램을 사용하여야합니다.</p>
파일이 생성된 후 거래소랑 연결 테스트를 하는데 test가 pass하지 않으면 설정이 잘못된 것입니다.</p>
test할 내용은 거래소의 잔고를 조회하여 연결 테스트를 합니다.</p>
coin name은 거래소에서 사용할 잔고를 테스트하는 용도입니다</p>
거래소에 없는 코인을 입력할 경우 오류가 발생할 수 있습니다</p>
거래소 API를 만들 때 잔고 조회 권한이 필요합니다.</p>
~~~
python exchange/crypt_cli.py [add/test] [exchange name] [coin name]
~~~

ex) upbit key 추가
~~~
$ python exchange/crypt_cli.py add upbit -c krw
input key :
secret key :
config file save done
exchange connection test with key
test pass
~~~

ex) python bithumb key 추가
~~~
$ exchange/crypt_cli.py add bithumb -c btc
~~~

ex) python binance key 추가
~~~
$ exchange/crypt_cli.py add bithumb -c krw
~~~

ex) upbit key 연결 테스트
~~~
$ python exchange/crypt_cli.py test upbit -c krw
exchange connection test with key
test pass
~~~
</br>
</br>

### 거래소 설정 파일
거래소별 설정 파일이 존재합니다</p>
설정 가능한 항목은 2가지 입니다.
 - 사용가능한 금액(availabel_size)</p>
사용가능한 금액은 한번의 시그널에서 사용할 금액을 결정하는 것입니다</p>

 - 남겨둘 금액(freeze_size)</p>
남겨둘 금액은 매매요청이 들어왔을 때 남겨둘 금액을 의미합니다.</p>
남겨둘 금액 보다 더 많은 SELL 요청이 들어오면 해당 요청은 거부됩니다.</p>
</br>
사용 가능한 금액과 남겨둘 금액이 상충이 날 경우 남겨둘 금액을 최우선합니다.</p>

#### 남겨둘 금액
~~~
"freeze_size" : {
        "KRW" : 0,
        "BTC" : 1,
        "ETH" : 10,
        "ZIL" : 27933.083
    }
    
ex1) BTC잔고가 1일 때 #BTC #SELL #1.1 시그널이 들어올 경우
0.1 SELL을 수행합니다.

ex2) KRW 잔고가 10,000원일 때 #ETH #BUY #만원치 시그널이 들어올 경우
요청이 들어온 모든 금액을 구매하는데 사용합니다.
만약 지켜야하는 금액이 5,000원으로 설정이 되어 있었다면 5,000원에 해당하는 ETH만 구매합니다.
~~~
#### 사용가능한 금액
~~~
"availabel_size" : {
        "KRW" : 5000,
        "BTC" : 1,
        "ETH" : 1,
        "USDT" : 10,
        "TRX" : 5000,
        "VTC" : 10000,
        "ARK" : 1000
    }
    
ex1) #EOS/KRW #BUY #만원치 시그널이 들어왔을 경우
잔고에 얼마나 많은 금액이 있는지 상관없이 5,000원치 EOS를 구매합니다.
단, 다음 시그널에도 5,000원을 사용할 수 있습니다. 그 다음 시그널에도 다음에도.
즉 한번의 시그널에서 사용할 최대 금액을 제한하는 것입니다
만약 최저로 지켜야하는 금액이 있다면 "남겨둘 금액"에서 설정하셔야합니다

ex2) #TRX/KRW #SELL #모두 시그널이 들어왔을 경우
TRX에 가용가능한 코인이 몇개든 상관없이 최대 5000개만 판매합니다
ex1과 동일하게 시그널 한번에 적용되는 규칙입니다
SELL시그널이 여러번 들어오면 한번에 최대 5,000개씩 시그널 횟수만큼 판매됩니다
~~~
</br>

#### 사용가능한 금액과 지켜아할 금액이 상출될 경우
~~~
원화 마켓을 예로 들어보겠습니다.
case1.
원화 잔고 : 만원
freeze_size : 오천원
availabel_size  : 만원

이 때 BUY 시그널이 뜰 경우 지켜야할 금액이 우선시 되기 때문에 "오천원"치 금액(availabel_size - freeze_size)을 구매하게 됩니다.

case2.
원화 잔고 : 사천원
freeze_size : 오천원
availabel_size : 만원

이 때 BUY 시그널이 떠도 지켜할 금액보다 잔고가 낮으므로 매매를 진행하지 않습니다.


case3.
BTC 잔고 : 1 BTC
freeze_size BTC : 0.5 BTC
availabel_size BTC : 1 BTC

BUY시그널이 뜰 경우 case1과 동일합니다. 0.5BTC만 구매에 사용합니다.
~~~

### 트레이딩뷰 얼러트 설정

~~~
#BTC/KRW #1M #SELL #BITHUMB
#종목심볼/마켓 #봉 #BUY/SELL타입 #거래소
~~~
얼러트 내용부분을 위의 형태로 적용.</p>

얼럿트의 앞에 어떤 문자가 들어와도 상관없음. 다만 '#'표시만 안들어가면 됨</p>
~~~
올바른 예) 이 얼럿트는 전략 1번 : #BTC/KRW #1M #SELL #BITHUMB
잘못된 예) 이 얼럿트는 #전략 1번 : #BTC/KRW #1M #SELL #BITHUMB
~~~

또는 얼럿트의 뒷부분에 문자를 넣을 때 #을 시작으로 넣어야함
~~~
올바른 예) #BTC/KRW #1M #SELL #BITHUMB #이 뒤로는 전부 무시 된다
잘못된 예) #BTC/KRW #1M #SELL #BITHUMB 샾을 붙이지 않으면 거래소 이름을 올바르게 인식하지 못한다
~~~

</br>

### 실행
실행을 하게되면 ants.conf에 설정된 전략('strategy' 항목)을 찾아서 사용하게 된다
~~~
zip 파일을 풀어둔 폴더로 이동 후 아래의 명령어 
python ants/main.py
~~~
</br>

### 보고서
프로그램이 실행되면 data.db라는 파일이 생성됩니다. 이 파일은 sqlite3로 만들어져있으며, 매매 기록을 저장하고 있습니다.</p>
아래의 프로그램을 사용하여 매매기록을 .csv파일을 생성합니다. 이 파일은 엑셀에서 열어볼 수 있습니다.</p>
파일은 자동으로 생성 날짜를 붙여서 생성하므로 파일이 겹치는 일이 없습니다. 다만 프로그램이 설치될 때부터 모든 기록을 가지고 있습니다.</p>
기록을 초기화 시키고 싶으시면 data.db파일을 지우시면 됩니다.</p>

~~~
python exchange/csvout.py trading
~~~
</br>

### LOG
logs폴더에 ants.log가 출력됩니다. 현재 개발버젼이라 debug 메시지도 함께 출력이 되어 log가 꽤 크게 남습니다.</p>
이를 변경하려면 configs/log.conf 파일에 DEBUG부분을 INFO로 변경하시면 됩니다. 이 부분은 배포 버젼에서 INFO로 변경될 것입니다</p>
</br>

### 지원거래소

#### 업비트
#### 빗썸
#### 바이낸스


### 주의사항

> 해당 프로그램으로 직접 투자시 위험부담은 투자자 본인에게 있습니다.

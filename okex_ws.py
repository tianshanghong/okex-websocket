import websocket
import zlib    #压缩相关的库
import json
import threading
import hashlib
import time

#输入OKEx账户的api key与secret key（v1版本）
api_key=''
secret_key =''

#解压函数
def inflate(data):
    decompress = zlib.decompressobj(-zlib.MAX_WBITS)
    inflated = decompress.decompress(data)
    inflated += decompress.flush()
    return inflated

#签名函数，订阅个人信息，买卖等都需要签名
def buildMySign(params,secretKey):
    sign = ''
    for key in sorted(params.keys()):
        sign += key + '=' + str(params[key]) +'&'
    return  hashlib.md5((sign+'secret_key='+secretKey).encode("utf-8")).hexdigest().upper()

#返回签名的信息
def wsGetAccount(channel,api_key,secret_key):
    params = {
      'api_key':api_key,
    }
    sign = buildMySign(params,secret_key)
    return "{'event':'addChannel','channel':'"+channel+"','parameters':{'api_key':'"+api_key+"','sign':'"+sign+"'}}"


#每当有消息推送时，就会触发，信息包含为message，注意在这里也可以使用ws.send()发送新的信息。
def on_message(ws, message):
    try:
        inflated = inflate(message).decode('utf-8')  #将okex发来的数据解压
    except Exception as e:
        print(e)
    if inflated == '{"event":"pong"}':  #判断推送来的消息类型：如果是服务器的心跳
            print("Pong received.")
            return
    global trade
    try:
        msgs = json.loads(inflated)
        for msg in msgs:
            if 'addChannel' == msg["channel"]: #判断推送来的消息类型：如果是订阅成功信息
                print(msg["data"]["channel"] + " subscribed.")
            if 'ok_sub_futureusd_btc_trade_quarter' == msg["channel"]: #判断推送来的消息类型：如果是订阅的数据
                for data in msg["data"]:
                    trade = data
                    # print(trade[3], trade[1]) #打印价格和时间信息到控制台
    except Exception as e:
        print(e)

#出现错误时执行
def on_error(ws, error):
    print(error)

#关闭连接时执行
def on_close(ws):
    print("### closed ###")

#开始连接时执行，需要订阅的消息和其它操作都要在这里完成
def on_open(ws):
    ws.send(wsGetAccount('ok_sub_futureusd_btc_trade_quarter',api_key,secret_key)) #如果需要订阅多条数据，可以在下面使用ws.send方法来订阅
    # ws.send("{'event':'addChannel','channel':'ok_sub_spotcny_btc_depth_60'}")
    # ws.send("{'event':'addChannel','channel':'ok_sub_spotcny_btc_ticker'}")

#发送心跳数据
def sendHeartBeat(ws):
    ping = '{"event":"ping"}'
    while(True):
        time.sleep(30) #每隔30秒交易所服务器发送心跳信息
        sent = False
        while(sent is False): #如果发送心跳包时出现错误，则再次发送直到发送成功为止
            try:
                ws.send(ping)
                sent = True
                print("Ping sent.")
            except Exception as e:
                print(e)

#创建websocket连接
def ws_main():
    websocket.enableTrace(True)
    host = "wss://real.okex.com:10441/ws/v1"
    ws = websocket.WebSocketApp(host,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    threading.Thread(target=sendHeartBeat, args=(ws,)).start() #新建一个线程来发送心跳包
    ws.run_forever()    #开始运行


if __name__ == "__main__":
    trade = 0
    threading.Thread(target=ws_main).start()
    while True:
        #这里是需要进行的任务，下单的策略可以安排在这里
        time.sleep(3)
        print(trade[3], trade[1]) #打印价格和时间信息到控制台
        # Do something

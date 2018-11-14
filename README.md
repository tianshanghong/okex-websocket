# okex-websocket
A python implemented websocket API demo for OKEx automatic trading.

本文发布在我的个人博客中（[传送门](https://blog.marsrainbow.cn/2018/11/14/使用websocket接口获取okex交易数据/)）。

我在获取和处理Okex的交易数据时，找不到开源好用的支持websocket连接的SDK包。再加上okex的API几经修改，一些曾经可以使用的代码目前也已失效。于是有了以下自己尝试使用WebSocket接口获取Okex交易数据的内容。

本文中所包含的完整代码位于[我的Github仓库](https://github.com/tianshanghong/okex-websocket "我的Github仓库")，欢迎批评，欢迎Star。

### 思考与分析

[wb wang](https://www.zhihu.com/people/wb-wang-91 "wb wang")曾在知乎专栏写了一篇[《比特币程序化交易入门（5）：WebSocket API》](https://zhuanlan.zhihu.com/p/22693475 "《比特币程序化交易入门（5）：WebSocket API》")的文章。由于Okex的API几经修改，目前已经不能直接使用。但是大体思路还是一样的。
1. 通过websocket方式与服务器建立连接，并向服务器发送[订阅请求](https://github.com/okcoin-okex/API-docs-OKEx.com/blob/master/API-For-Futures-CN/%E5%90%88%E7%BA%A6%E4%BA%A4%E6%98%93WebSocket%20API.md#%E5%8F%91%E9%80%81%E8%AF%B7%E6%B1%82 "订阅请求")。

```python
#开始连接时执行，需要订阅的消息和其它操作都要在这里完成
def on_open(ws):
    ws.send(wsGetAccount('ok_sub_futureusd_btc_trade_quarter',api_key,secret_key)) #如果需要订阅多条数据，可以在下面使用ws.send方法来订阅
    # ws.send("{'event':'addChannel','channel':'ok_sub_futureusd_eth_trade_quarter'}")
    # ws.send("{'event':'addChannel','channel':'ok_sub_futureusd_bch_trade_quarter'}")

```

2. 服务器在收到订阅请求后会返回[订阅成功](https://github.com/okcoin-okex/API-docs-OKEx.com/blob/master/API-For-Futures-CN/%E5%90%88%E7%BA%A6%E4%BA%A4%E6%98%93WebSocket%20API.md#%E6%9C%8D%E5%8A%A1%E5%99%A8%E5%93%8D%E5%BA%94 "订阅成功")的消息。然后每当有新的交易信息，就会自动推送给我们。

3. 解析[服务器返回的json格式数据](https://github.com/okcoin-okex/API-docs-OKEx.com/blob/master/API-For-Futures-CN/%E5%90%88%E7%BA%A6%E4%BA%A4%E6%98%93WebSocket%20API.md#api%E5%8F%82%E8%80%83 "服务器返回的json格式数据")，然后做你想做的事情:-)。比如说打印当前价格到控制台或者把数据存到数据库或内存缓存中。

Okex服务器发送来的消息总共有三种类型。第一种是心跳包“pong”，用来确认和客户端的连接未被中断（详情见下一点）。第二种是服务器确认订阅事件成功的消息。这种消息会在我们向服务器发送订阅请求之后，由交易所的服务器发送给我们。第三种是所订阅的数据信息。

第一种数据格式很简单，就是`{"event":"pong"}`，也没有其它的什么变化。
后两种的数据格式基本上是`[{"binary":1,"channel":"","data":[]}]
`，都有`binary`、`channel`、`data`的字段。我们根据`channel`字段的值来判断这条消息是第二种消息还是第三种消息。

```python
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
```

按道理整个过程到这里就该结束了，因为你已经拿到了你想拿的数据。但是，为了保持WebSocket的持续连接，也就是说为了保障你能够持续地收到来自交易所服务器的信息，你需要每隔30分钟向交易所发送一个心跳包，表明你与交易所的连接没有中断。如果你不发送这个心跳包，那么Okex服务器的WebSocket推送一般会在几分钟后自动中断。这也是本文与[wb wang的文章](https://zhuanlan.zhihu.com/p/22693475 "wb wang的文章")不同的一点。

于是我们有了第四点：
4. 每隔30秒向交易所服务器发送[心跳包](https://github.com/okcoin-okex/API-docs-OKEx.com/blob/master/API-For-Futures-CN/%E5%90%88%E7%BA%A6%E4%BA%A4%E6%98%93WebSocket%20API.md#%E5%A6%82%E4%BD%95%E5%88%A4%E6%96%AD%E8%BF%9E%E6%8E%A5%E6%98%AF%E5%90%A6%E6%96%AD%E5%BC%80 "心跳包")。

创建一个心跳包发送函数`sendHeartBeat(ws)`，借助websocket客户端的send方法来发送心跳包。
```python
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
```

然后创建一个新的线程，专门用于发送心跳包。
```python
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
```

### 完整代码

本文的文章代码请见[okex_ws.py](https://github.com/tianshanghong/okex-websocket/blob/master/okex_ws.py)

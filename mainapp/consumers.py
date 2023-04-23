import json

from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from asgiref.sync import sync_to_async
from .models import StockDetail
import copy

class StockConsumer(AsyncWebsocketConsumer):
    @sync_to_async
    def addToCeleryBeat(self, stockpicker):
        task = PeriodicTask.objects.filter(name = "every-10-seconds")
        if len(task)>0:
            print("hello")  # testing that task.first() will work or not
            task = task.first()
            args = json.loads(task.args)
            args = args[0]
            for x in stockpicker:
                if x not in args:
                    args.append(x)
            task.args = json.dumps([args])
            task.save()
        else:
            schedule, created = IntervalSchedule.objects.get_or_create(every=10, period = IntervalSchedule.SECONDS)
            task = PeriodicTask.objects.create(interval = schedule, name='every-10-seconds', task="mainapp.tasks.update_stock", args = json.dumps([stockpicker]))

    @sync_to_async
    def addToStockDetail(self,stockpicker):
        user = self.scope['user']
        for i in stockpicker:
            stock, created = StockDetail.objects.get_or_create(stock=1)
            stock.user.add(user)
    
    async def connect(self):
        print(self.scope)
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "stock_%s" % self.room_name

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        #parse querystring
        query_params = parse_qs(self.scope['query_string'].decode())
        print(query_params)
        stockpicker = query_params['stockpicker']
        #add to celery beat
        await self.addToCeleryBeat(stockpicker)
        #add user to stock detail
        await self.addToStockDetail(stockpicker)

        await self.accept()

    @sync_to_async
    def helper_func(self):
        user = self.scope['user']
        stocks = StockDetail.objects.filter(user__id = user.id)
        tasks = PeriodicTask.objects.get(name = "every-10-seconds")
        args = json.loads(tasks.args)
        args = args[0]
        for i in stocks:
            i.user.remove(user)
            if i.user.count() == 0:
                args.remove(i.stock)
                i.delete()
        if args == None:
            args= []
        if len(args) == 0:
            tasks.delete()
        else:
            tasks.args = json.dumps(args)
            tasks.save()


    async def disconnect(self, close_code):
        await self.helper_func()


        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "stock_update", "message": message}
        )

    @sync_to_async
    def selectUserStock(self):
        user = self.scope['user']
        user_stock = user.stockdetail_set.values_list("stock", flat=True)
        return list(user_stock)
    # Receive message from room group
    async def send_stock_update(self, event):
        message = event["message"]
        message = copy.copy(message)
        user_stock = await self.selectUserStock()

        keys = message.keys()
        for key in list(keys):
            if key in user_stock:
                pass
            else:
                del message[key]

        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))
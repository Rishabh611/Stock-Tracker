from django.shortcuts import render
from yahoo_fin.stock_info import *
from django.http import HttpResponse
import time
import threading, queue
from threading import Thread
from asgiref.sync import sync_to_async
# Create your views here.
def stockPicker(request):
    stock_picker = tickers_nifty50()
    return render(request, "mainapp/stockpicker.html", {'stocks':stock_picker})
    
@sync_to_async
def checkAuthenticated(request):
    if not request.user.is_authenticated:
        return False
    else:
        return True

async def stocktracker(request):
    is_loggedin = await checkAuthenticated(request)
    if not is_loggedin:
        return HttpResponse("Login First")
    stocks = request.GET.getlist('stockpicker')
    print(stocks)
    data = {}
    available_stocks = tickers_nifty50()
    for i in stocks:
        if i in available_stocks:
            pass
        else:
            return HttpResponse("Error")
    start = time.time()
    print(start)
    n_threads = len(stocks)
    thread_list = []
    que = queue.Queue()
    # for i in stocks:
    #     print(data)
    #     result = get_quote_table(i)
    #     data.update({i : result})
    for i in range(n_threads):
        thread = Thread(target = lambda q,  args1: q.put({stocks[i] : get_quote_table(args1)}), args = (que, stocks[i]))
        thread_list.append(thread)
        thread_list[i].start()
    for thread in thread_list:
        thread.join()
    while not que.empty():
        result = que.get()
        data.update(result)

    end = time.time()
    time_taken = end - start
    print(time_taken)
    print(data)
    return render(request, 'mainapp/stocktracker.html', {
        'data':data, 'room_name' : 'track'
    })
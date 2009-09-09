from itty import *
import Queue
import threading

queue = Queue.Queue()
message_count = 0
message_count_lock = threading.Lock()
finish_queue = False
finish_queue_lock = threading.Lock()
wait_for_it = threading.Event()


class Consumer(threading.Thread):
    def __init__(self, queue):
        super(Consumer, self).__init__()
        self.queue = queue
    
    def run(self):
        while True:
            wait_for_it.wait()
            
            self.process_queue()
            
            finish_queue_lock.acquire()
            should_finish = finish_queue
            finish_queue_lock.release()
            
            if should_finish:
                break
    
    def process_queue(self):
        for i in range(self.queue.qsize()):
            try:
                job = self.queue.get(True, 1)
            except Queue.Empty:
                continue
            
            print "Got '%s'..." % job
            self.queue.task_done()


@get('/')
def list(request):
    return "Queue length is: %d." % queue.qsize()


@get('/add')
def add(request):
    global message_count, queue
    message_count_lock.acquire()
    message_count += 1
    queue.put(request.GET.get('message', 'No message.'), True, 1)
    message_count_lock.release()
    
    if queue.qsize() >= 5:
        wait_for_it.set()
        wait_for_it.clear()
    
    return "Message queued."


def shutdown():
    global finish_queue
    print "Finishing up the queue..."
    finish_queue_lock.acquire()
    finish_queue = True
    finish_queue_lock.release()
    
    wait_for_it.set()
    wait_for_it.clear()
    # queue.join() # This is probably the behavior we want but for now...
    consumer.join()
    
    message_count_lock.acquire()
    print "Handled #%d messages." % message_count
    message_count_lock.release()


try:
    consumer = Consumer(queue)
    consumer.start()
    run_itty()
except KeyboardInterrupt:
    shutdown()
    import sys
    sys.exit()

import threading;
from multiprocessing import Process;
from multiprocessing import Pipe;
import time;
import sys;

class Reporter:
    def __init__(self, freq = 0):
        self.freq = freq;
        self.init();

    def init(self):
        self.start = time.time();
        self.count = 0;

    def report(self, text = ''):
        if self.freq:
            self.count += 1;
            if self.count % self.freq == 0:
                print '\b' * 200, self.count, time.time() - self.start, text,
                sys.stdout.flush();

    def end(self):
        if self.freq:
            print '';

class GeneralTask:
    def __init__(self, elements, func, reporter):
        self.elements = elements;
        self.func = func;
        self.reporter = reporter;

    def run(self):
        self.results = [];
        for element in self.elements:
            self.results.append(self.func(element));
            self.reporter.report();

class GeneralThread(threading.Thread, GeneralTask):
    def __init__(self, elements, func, reporter):
        threading.Thread.__init__(self);
        GeneralTask.__init__(self, elements, func, reporter);

    def run(self):
        GeneralTask.run(self);

class GeneralProcess(Process, GeneralTask):
    def __init__(self, elements, func, conn, reporter):
        Process.__init__(self);
        self.conn = conn;
        GeneralTask.__init__(self, elements, func, reporter);

    def run(self):
        GeneralTask.run(self);
        self.conn.send(self.results);
        self.conn.close();

class TaskManager:
    def __init__(self, reporter):
        self.tasks = [];
        self.reporter = reporter;

    def run(self):
        self.reporter.init();
        map(lambda task: task.start(), self.tasks);
        map(lambda task: task.join(), self.tasks);
        self.reporter.end();
        results = reduce(lambda sub_results, i: sub_results + self.get_result(i), range(len(self.tasks)), []);
        return results;

class ThreadManager(TaskManager):
    def __init__(self, reporter):
        TaskManager.__init__(self,reporter);
    def add(self, func, elements):
        self.tasks.append(GeneralThread(elements, func, self.reporter));
    def get_result(self, i):
        return self.tasks[i].results;

class ProcessManager(TaskManager):
    def __init__(self, reporter):
        TaskManager.__init__(self, reporter);
        self.conns = [];

    def add(self, func, elements):
        parent_conn, child_conn = Pipe();
        self.tasks.append(GeneralProcess(elements, func, child_conn, self.reporter));
        self.conns.append(parent_conn);
    def get_result(self, i):
        return self.conns[i].recv();

def get_task_manager(name, reporter):
    if name == 'thread':
        return ThreadManager(reporter);
    elif name == 'process':
        return ProcessManager(reporter);

def partition(elements, thread_num):
    elements_groups = [];
    element_num = len(elements);
    element_per_thread = (element_num - 1) / thread_num + 1;
    for i in range(0, element_num, element_per_thread):
        element_this_task = min(element_per_thread, element_num - i);
        begin = i;
        end = begin + element_this_task;
        sub_elements = elements[begin:end];
        elements_groups.append(sub_elements);
    return elements_groups;

'''
    in the same semantics of map, but in parallel way
'''
def fastmap(func, thread_num, elements, worker_type = 'thread', reporter=Reporter()):
    if len(elements) == 0:
        return [];
    elements_groups = partition(elements, thread_num);
    task_manager = get_task_manager(worker_type, reporter);
    map(lambda elements_group: task_manager.add(func, elements_group), elements_groups);
    results = task_manager.run();
    return results;


def run_batch(func, thread_num, elements, writer, report_freq): 
    results = fastmap(func, thread_num, elements, 'thread', report_freq);
    for result in results:
        writer.write(result.__str__() + '\n');
    writer.flush();

'''
    in the same semantics of map, but read and write from/to a file
'''
def filemap(func, thread_num, task_per_thread, reader, writer, report_freq=0):
    element = reader.next();
    elements = [];
    batch_size = thread_num * task_per_thread;
    reporter = Reporter(report_freq);
    while(element):
        elements.append(element);
        element_num = len(elements);
        if element_num >= batch_size:
            print 'run a batch';
            run_batch(func, thread_num, elements, writer, reporter);        
            elements = [];
        element = reader.next();
    run_batch(func, thread_num, elements, writer, reporter);        
    writer.close();
 

def my_test_func(i):
    time.sleep(.001)
    return i + 1;

def fastmap_test():
    elements = range(0,1000);
    t0= time.time();
    result1 = map(my_test_func, elements);
    print time.time() - t0;
    result2 = fastmap(my_test_func, 20, elements, 'process');
    print time.time() - t0;
    print result1 == result2;

if __name__ == '__main__':
    fastmap_test();


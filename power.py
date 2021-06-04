import os
import tkinter as tk
from telnetlib import Telnet
import ctp.pdu.apc as apc


class PDUPower():
    def __init__(self):
        self.window = tk.Tk()
        self.pdu1 = tk.IntVar()
        self.pdu2 = tk.IntVar()
        self.pdu3 = tk.IntVar()
        self.pdu4 = tk.IntVar()
        self.p1 = tk.Checkbutton(self.window, text='PDU: 1', variable=self.pdu1, onvalue=1, offvalue=0)
        self.p2 = tk.Checkbutton(self.window, text='PDU: 2', variable=self.pdu2, onvalue=1, offvalue=0)
        self.p3 = tk.Checkbutton(self.window, text='PDU: 3', variable=self.pdu3, onvalue=1, offvalue=0)
        self.p4 = tk.Checkbutton(self.window, text='PDU: 4', variable=self.pdu4, onvalue=1, offvalue=0)

    def pdu(self, powerStatue='off'):
        tmp = [self.pdu1.get(), self.pdu2.get(), self.pdu3.get(), self.pdu4.get()]
        
        pdu_cli = apc.APC('10.0.0.253', usr='apc', pwd='apc -c')
        cmd = ",".join([str(i+1) for i, val in enumerate(tmp) if val == 1])
        if powerStatue is 'on':   
            pdu_cli.power_on(cmd)
            for i in cmd.split(','):
                [self.p1, self.p2, self.p3, self.p4][int(i)-1].config(bg='green')
        if powerStatue is 'off':
            pdu_cli.power_off(cmd)
            for i in cmd.split(','):
                [self.p1, self.p2, self.p3, self.p4][int(i)-1].config(bg='grey')

    def __del__(self):
        print('destory the window')
        self.window.quit()

    def PowerControl(self):
        self.window.title('PDU Power')
        self.window.geometry('500x300')
        l = tk.Label(self.window, text='DST PDU Power Control', bg='light blue', font=('Arial', 12), width=30, height=2)
        l.pack()

        self.p1.pack()
        self.p2.pack()
        self.p3.pack()
        self.p4.pack()
        button1 = tk.Button(self.window, text='ready to on', width=10, height=2, command=lambda: self.pdu('on'))
        button2 = tk.Button(self.window, text='ready to off', width=10, height=2, command=lambda: self.pdu('off'))
        button3 = tk.Button(self.window, text='logout', width=10, height=2, command=self.__del__)
        button1.pack()
        button2.pack()
        button3.pack()
        self.window.mainloop()


if __name__ == '__main__':
    easyCommand = PDUPower()
    easyCommand.PowerControl()

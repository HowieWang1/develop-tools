#include"telnet.h"
#include<string.h>
#include<stdio.h>
#include <stdlib.h>

#define MAXLINE 1024
#define SEND    1
#define IS      0



static uint32 handle_telnetcmd_from_server(uint8* buf,uint32 len,uint8* resp,uint32 n);
static uint32 process_every_frame(uint8* startByte,uint8* endByte,uint8* sendbuf,uint32 startSendByte);

/* 2020-01-13 begin */
extern uint32 SOCKFD ;
extern void telnet_client_send_msg(int fd, const void *vptr, size_t n);
/* 2020-01-13 end*/

uint32 get_every_frame(uint8* recvbuf,uint32 len,uint8* sendbuf,uint32 sendlen)
{
    uint32 i =0,n=0,sum =0;
    //uint8* p = sendbuf;
    uint8* pRear = &recvbuf[len];
    uint8* startByte = recvbuf;
    uint8* endByte = recvbuf;
    uint8* strSendToMQTT = NULL;
    
    strSendToMQTT = (uint8*)malloc(MAXLINE);
    if(strSendToMQTT == NULL)
    {
        printf("==========strSendToMQTT malloc failed==============\n");
        return 0;
    }
    
#if 1   
    printf("-sum-receivelen----%d-------\n",len);
    printf("receive :<*");
    
    for(i =0 ;i<len;i++)
    {
        printf("%x*",recvbuf[i]);
    }
    printf("*>\n");
    
#endif


    while(startByte != pRear)
    {
        if(*startByte == IAC)
        {
        sum = sum + n;
            switch(*(++endByte))
            {
        /*fa 250 */case SB:while(*(++endByte) != SE){};n = process_every_frame(startByte,endByte,sendbuf,sum);break;
        /*fb 251 */case WILL:endByte +=2;n = process_every_frame(startByte,endByte,sendbuf,sum);break;
        /*fc 252 */case WONT:endByte +=2;n = process_every_frame(startByte,endByte,sendbuf,sum);break;
        /*fd 253 */case DO:endByte +=2;n = process_every_frame(startByte,endByte,sendbuf,sum);break;
        /*fe 254 */case DONT:endByte +=2;n = process_every_frame(startByte,endByte,sendbuf,sum);break;    
        /* 240 */  case SE:break;
        /* sss */  default : break;
            }
                        startByte = endByte;
        }
        else
        {
                        /* 2020-01-13 begin ：按照原来的写法 else分支会造成死循环，这里修改 */
            i = 0;
            memset(strSendToMQTT,0,MAXLINE);
            while((startByte != pRear)&&(*startByte != IAC ))
            {
                strSendToMQTT[i++] = *startByte ;
                ++startByte;
            }
            strSendToMQTT[i] = '\0';
            /* 2020-01-13 strSendToMQTT的字符串应当也要发送出去 */
            telnet_client_send_msg(SOCKFD,strSendToMQTT,i+1);
                       /* 2020-01-13 end ：按照原来的写法 else分支会造成死循环，这里修改 */
        }
    }
    if(sum > sendlen)
    {
        printf("--error3---sum > MAXLINE-----\n");
    }
    printf("--------------sum is %d ----\n",sum);
    return sum;
}



static uint32 process_every_frame(uint8* startByte,uint8* endByte,uint8* sendbuf,uint32 startSendByte)
{
    uint8 n = 0 ;
    uint8* pstartByte = startByte;
    
    while(pstartByte != endByte)
    {
        n++;
        pstartByte++;
    }
    return handle_telnetcmd_from_server(startByte,n,&sendbuf[startSendByte],MAXLINE);
}

static uint32 handle_telnetcmd_from_server(uint8* buf,uint32 len,uint8* resp,uint32 n)
{
    uint32 i =0;
    uint8 *p = resp;
    OPERATION_OPTIONS optionCode;
    uint8 cmdCode,ch;
    uint32 resplen =0;
    memset(resp,0,len);
    //first display cmd from server in string
    
#if 1
    printf("--receivelen----%d-------\n",len);
    printf("receive :<*");
    for(i =0 ;i<len;i++)
    {
        printf("%x*",buf[i]);
    }
    printf("*>\n");
    
#endif

    if(len < 3)
    {
        printf("IAC command length is %d less then 3\n",len);
        return -1;
    }
    
    //获得命令码
    cmdCode = buf[1];
    //获得选项码
    optionCode = buf[2];
    
    
    //response requests from server
    
    *p = IAC;
    resplen++;
    if( optionCode == TOPT_SUPP)//if(optionCode == TOPT_ECHO || optionCode == TOPT_SUPP)
    {
        if (cmdCode == DO)
        {
        //我设置我应答的命令码为 251(WILL) 即为支持 回显或抑制继续进行
            ch = WILL;
            *(++p) = ch;
            *(++p)= optionCode;
            resplen += 2;

        }
        //如果命令码为 254(DONT)
        else if (cmdCode == DONT)
        {
            //我设置我应答的命令码为 252(WONT) 即为我也会"拒绝启动" 回显或抑制继续进行
            ch = WONT;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;

        }
        //如果命令码为251(WILL)
        else if (cmdCode == WILL)
        {
            //我设置我应答的命令码为 253(DO) 即为我认可你使用回显或抑制继续进行
            ch = DO;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;
            //break;
        }
        //如果接受到的命令码为251(WONT) 
        else if (cmdCode == WONT)
        {
            //应答  我也拒绝选项请求回显或抑制继续进行
            ch = DONT;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;
            //    break;
        }
        //如果接受到250(sb,标志子选项开始)
        else if (cmdCode == SB)
        {
            /*
            * 因为启动了子标志位,命令长度扩展到了4字节,
            * 取最后一个标志字节为选项码
            * 如果这个选项码字节为1(send)
            * 则回发为 250(SB子选项开始) + 获取的第二个字节 + 0(is) + 255(标志位IAC) + 240(SE子选项结束)
        ....*/
            ch = buf[3];
            if (ch == SEND)
            {
                ch = SB;
                *(++p)= ch;
                *(++p)= optionCode;
                *(++p)= IS;
                *(++p)= IAC;
                *(++p)= SE;
                resplen += 5;
            }
            else
            {
                printf("ch != SEND\n");
            }
        }
        else
        {
            /* do nothing */
        }
    }
    else/* 如果选项码不是1 或者3  */
    {
        // 底下一系列代表,无论你发那种请求,我都不干
        if (cmdCode == DO)
        {
            ch = WONT;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;
        }
        else if (cmdCode == DONT)
        {
            ch = WONT;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;
        }
        else if (cmdCode == WILL)
        {
            ch = DONT;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;
        }
        else if (cmdCode == WONT)
        {
            ch = DONT;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;
        }
        else
        {
            /* do nothing */
        }
            
    }
    
#if 1
    printf("--resplen---%d-------\n",resplen);
    printf("response :<*");
    for(i =0 ;i<resplen;i++)
    {
        printf("%x*",resp[i]);
    }
    printf("*>\n");
#endif    
    
    
    if(n < resplen )
    {
        printf("error n < resplen !!! \n");
    }
    if(resplen < 3 )
    {
        printf("resplen < 3 \n");
    }
    return resplen;
}
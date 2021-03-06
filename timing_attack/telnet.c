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
                        /* 2020-01-13 begin ???????????????????????? else??????????????????????????????????????? */
            i = 0;
            memset(strSendToMQTT,0,MAXLINE);
            while((startByte != pRear)&&(*startByte != IAC ))
            {
                strSendToMQTT[i++] = *startByte ;
                ++startByte;
            }
            strSendToMQTT[i] = '\0';
            /* 2020-01-13 strSendToMQTT???????????????????????????????????? */
            telnet_client_send_msg(SOCKFD,strSendToMQTT,i+1);
                       /* 2020-01-13 end ???????????????????????? else??????????????????????????????????????? */
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
    
    //???????????????
    cmdCode = buf[1];
    //???????????????
    optionCode = buf[2];
    
    
    //response requests from server
    
    *p = IAC;
    resplen++;
    if( optionCode == TOPT_SUPP)//if(optionCode == TOPT_ECHO || optionCode == TOPT_SUPP)
    {
        if (cmdCode == DO)
        {
        //????????????????????????????????? 251(WILL) ???????????? ???????????????????????????
            ch = WILL;
            *(++p) = ch;
            *(++p)= optionCode;
            resplen += 2;

        }
        //?????????????????? 254(DONT)
        else if (cmdCode == DONT)
        {
            //????????????????????????????????? 252(WONT) ???????????????"????????????" ???????????????????????????
            ch = WONT;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;

        }
        //??????????????????251(WILL)
        else if (cmdCode == WILL)
        {
            //????????????????????????????????? 253(DO) ???????????????????????????????????????????????????
            ch = DO;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;
            //break;
        }
        //??????????????????????????????251(WONT) 
        else if (cmdCode == WONT)
        {
            //??????  ???????????????????????????????????????????????????
            ch = DONT;
            *(++p)= ch;
            *(++p)= optionCode;
            resplen += 2;
            //    break;
        }
        //???????????????250(sb,?????????????????????)
        else if (cmdCode == SB)
        {
            /*
            * ???????????????????????????,????????????????????????4??????,
            * ???????????????????????????????????????
            * ??????????????????????????????1(send)
            * ???????????? 250(SB???????????????) + ???????????????????????? + 0(is) + 255(?????????IAC) + 240(SE???????????????)
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
    else/* ?????????????????????1 ??????3  */
    {
        // ?????????????????????,????????????????????????,????????????
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
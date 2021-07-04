//gcc client.c -o client


#include"utils.h"
#include"telnet.h"


#define IP_ADDRESS   "127.0.0.1"
#define IP_PORT      23
#define SERV_PORT    3333
#define MAXLINE      1024

typedef struct sockaddr SA;


void str_cli(FILE *fp,uint32 sockfd);
uint32 max(uint32 a,uint32 b);
void ERR_EXIT(char* s);

uint32 main(uint32 argc,uint32 **argv)
{
    uint32 sockfd,isReady=0;
    struct sockaddr_in servaddr;
    uint32 hname[128];

    sockfd = socket(AF_INET,SOCK_STREAM,0);
    bzero(&servaddr,sizeof(servaddr));          //set to zero
    servaddr.sin_family = AF_INET;
    servaddr.sin_port = htons(IP_PORT);
    servaddr.sin_addr.s_addr = inet_addr(IP_ADDRESS);
    printf("servaddr: IP is %s, Port is %d\n",inet_ntoa(servaddr.sin_addr), ntohs(servaddr.sin_port));

    while(connect(sockfd,(SA*)&servaddr,sizeof(servaddr))){};
    printf("connect has been ready\n");
    
    str_cli(stdin,sockfd);
    exit(0);
    return 0;
}
void ERR_EXIT(char* s)
{
    perror(s);
    exit(EXIT_FAILURE);
}
void INFO_PRINT(char* s)
{
    printf("%s",s);
}
uint32 max(uint32 a,uint32 b)
{
    return (a>b?a:b);
}

void str_cli(FILE *fp,uint32 sockfd)
{
    uint32 maxfdp1,nready;               //stdin eof;
    fd_set rset;
    uint8 buf[MAXLINE];
    uint8 respbuff[MAXLINE] = {0};;
    uint32 resplen;
    uint32 n;
    uint8 echo_cmd[] = {0xff,0xfb,0x01};
    //stdineof = 0;
    FD_ZERO(&rset);
    writen(sockfd,echo_cmd,3);
    
    for(;;)
    {
        //if(stdineof == 0)
        FD_SET(fileno(fp),&rset);
        FD_SET(sockfd,&rset);
        maxfdp1 = max(fileno(fp),sockfd)+1;
        nready = select(maxfdp1,&rset,NULL,NULL,NULL);
        
        if(nready < 0)
        {
            ERR_EXIT("ERROR!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");
        }
        
        if(FD_ISSET(sockfd,&rset))
        {
            memset(buf,0,MAXLINE);
            if((n = read(sockfd,buf,MAXLINE))==0)
            {
                ERR_EXIT("str_cli:server termination prematurely");
            }
            buf[n] = '\0';
            //printf("FD_ISSET(sockfd,&rset)-------------%s\n",buf);
            
            if(buf[0] == IAC)
            {
                memset(respbuff,0,MAXLINE);
                resplen = get_every_frame(buf,n,respbuff,MAXLINE);
                writen(sockfd,respbuff,resplen);
            }
            else
            {
                telnet_client_send_msg(fileno(stdout),(char *)buf,n);
            }
            
            //writen(fileno(stdout),buf,n);
        }
        if(FD_ISSET(fileno(fp),&rset))
        {
            memset(buf,0,MAXLINE);
            if((n = readline(fileno(fp),(char *)buf,MAXLINE)) == 0)
            {
                //stdineof = 1;//此时碰到EOF 并且马上要发生FIN序列 所以标准输入不可读了
                shutdown(sockfd,SHUT_WR);
                FD_CLR(fileno(fp),&rset);
                INFO_PRINT("nothing input!");
                continue;
            }
            else if(n >0)
            {
                /* do nothing */
            }
            else
            {
                ERR_EXIT("some error occurred ");
            }
            //printf("FD_ISSET(fileno(fp),&rset)----%d--\n",n);
            //memset(buf,0,MAXLINE);
            telnet_client_send_msg(sockfd,(char *)buf,n);
        }
    }
}
#include"utils.h"


ssize_t readn(int fd, void *vptr,size_t n)
{
    size_t nleft;
    ssize_t nread;
    char *ptr;
    
    ptr = vptr;
    nleft = n;
    while(nleft >0)
    {
        if((nread = read(fd,ptr,nleft))<0)
        {
            if(errno == EINTR)                     //error：为EAGAIN，表示在非阻塞下，此时无数据到达，立即返回。
                nread = 0;                         //error：== EINTR，interrupt
            else
                return (-1);
        }
        else if(nread == 0)                        // read the end of the file
            break;
        else 
        /* do nothing */
        nleft -= nread;
        ptr += nread;
    }
    return n-nleft;//actually read
}

ssize_t writen(int fd, const void *vptr, size_t n)
{
    size_t nleft;
    ssize_t nwritten;
    const char *ptr;
    
    ptr = vptr;
    nleft = n;
    while(nleft > 0)
    {
        if((nwritten = write(fd,ptr,nleft)) < 0)
        {
            if(nwritten <0 &&  errno == EINTR)
            {
                nwritten = 0;
            }
            else
                return (-1);
        }
        else if(nwritten == 0)   
            break;
        else //nwritten > 0
        {
            /*do nothing*/
        }
        nleft = nleft - nwritten;
        ptr = ptr + nwritten;
    }
    return (n- nleft);//实际写了多少字节
}

ssize_t readline(int fd,void *vptr,size_t maxlen)
{
    ssize_t n =0,rc;
    char c,*ptr;
    
    ptr = vptr;
    while(1)
    {
        if((rc = read(fd,&c,1)) == 1)
        {
            *ptr++ = c;
            n++;
            if(c == '\n')
                break;
        }
        else if (rc == 0)
        {
            *ptr = '\0';
            return (n -1);
        }
        else
        {
            if(errno == EINTR)
                continue;
            else
                return (-1);
        }
    }
    *ptr = '\0';
    return n;
}
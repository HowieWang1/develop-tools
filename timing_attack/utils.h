#ifndef __UTILS__H
#define __UTILS__H

#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <malloc.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/ioctl.h>
#include <stdarg.h>
#include <fcntl.h>
#include <fcntl.h>
#include <sys/poll.h>
#include <signal.h>
#include <sys/wait.h>

typedef signed long int ssize_t;
typedef unsigned long int size_t;

ssize_t readn(int fd, void *vptr,size_t n);
ssize_t writen(int fd, const void *vptr, size_t n);
ssize_t readline(int fd,void *vptr,size_t maxlen);

#endif

#ifndef __TELNET__H
#define __TELNET__H

//<IAC CMD OP >

#define IAC   255

//command word
#define NUL        0
#define BEL        7
#define BS         8
#define HT         9
#define LF         10
#define VT         11
#define FF         12
#define CR         13
#define SE         240
#define NOP        241
#define DM         242
#define BRK        243
#define IP         244
#define AO         245
#define AYT        246
#define EC         247
#define EL         248
#define GA         249
#define SB         250
#define WILL       251
#define WONT       252
#define DO         253
#define DONT       254

typedef unsigned char uint8;
typedef unsigned int  uint32;


//operation options

typedef enum tagOPERATION_OPTIONS
{
    TOPT_BIN = 0,
    TOPT_ECHO = 1,
    TOPT_RECN = 2,
    TOPT_SUPP = 3
    
}OPERATION_OPTIONS;


uint32 get_every_frame(uint8* recvbuf,uint32 len,uint8* sendbuf,uint32 sendlen);

#endif

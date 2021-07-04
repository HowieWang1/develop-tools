all:Client_telnet
    @echo ""
    @echo "This is telnet Client compile......."
    @echo ""
    
Client_telnet:client.o utils.o telnet.o
    gcc -g -o Client_telnet client.o utils.o telnet.o
    
client.o:client.c utils.h telnet.h
    gcc -g -c client.c
    
utils.o:utils.c utils.h
    gcc -g -c utils.c 
    
telnet.o:telnet.c telnet.h
    gcc -g -c telnet.c
    
clean :
    -rm client.o utils.o telnet.o Client_telnet
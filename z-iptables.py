block network from port 5432
    iptables
        -A INPUT
        -p tcp
        -s 15.15.15.0/24
        --dport 5432
        -m state NEW,ESTABLISHED
        -j DROP

Block single IP
    iptables
        -A INPUT
        -s "$BLOCK_THIS_IP"
        -j DROP

Allow Incoming HTTP and HTTPS
    iptables -A INPUT -i eth0 -p tcp --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT
    iptables -A OUTPUT -o eth0 -p tcp --sport 80 -m state --state ESTABLISHED -j ACCEPT

Ping
    iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT
    iptables -A OUTPUT -p icmp --icmp-type echo-reply -j ACCEPT

outbound dns:
    iptables -A OUTPUT -p udp -o eth0 --dport 53 -j ACCEPT
    iptables -A INPUT -p udp -i eth0 --sport 53 -j ACCEPT

ddos:
    iptables
        -A INPUT
        -p tcp
        --dport 80
        -m limit
        --limit 25/minute
        --limit-burst 100
        -j ACCEPT
*
- m limit: This uses the limit iptables extension
– limit 25/minute: This limits only maximum of 25 connection per minute.
– limit-burst 100: This value indicates that the limit/minute will be enforced
  only after the total number of connection have reached the limit-burst level.


Port Forward:
    iptables
        -t nat
        -A PREROUTING
        -p tcp
        -d 192.168.102.37
        --dport 422
        -j DNAT
        --to 192.168.102.37:22

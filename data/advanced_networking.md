# شبكات متقدّمة
## IPv4/IPv6 & Subnetting
- CIDR: 10.0.0.0/16 → /24 شبكات فرعية (256 عنوان)
- Summarization مثال: 192.168.0.0/24 + 192.168.1.0/24 → 192.168.0.0/23

## VLAN & Trunking
- Access vs Trunk (802.1Q)، Native VLAN.
- STP/RSTP: تجنّب الحلقات، Root Bridge، PortFast, BPDU Guard.

## Routing
- OSPF: Areas، LSAs، DR/BDR، التكلفة = 100/الـBandwidth (تقريب).
- BGP: eBGP/iBGP، AS Path، Local Pref، MED، المسارات الافتراضية، Communities.

## QoS
- DSCP Classes، Queueing (LLQ/CBWFQ)، Policing vs Shaping.

## Security
- ACLs (L3/L4)، NAT (Static/Pat)، DHCP Snooping، Dynamic ARP Inspection.
- VPNs: Site-to-Site (IPSec IKEv2)، Remote Access (SSL).
- Zero Trust: مصادقة قوية، أقل امتياز، مراقبة مستمرة.

## مراقبة وتشخيص
- NetFlow/sFlow، SNMP، Syslog، NTP، أدوات: Wireshark, iperf, mtr.

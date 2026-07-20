---
id: net-dns
domain: systems
title: DNS — Domain Name System
tags: [networking, dns]
mastery: 0
source:
visibility: public
---

DNS is the **phonebook of the internet**. Humans remember readable domain names (`www.google.com`), but the network needs numeric IP addresses (`142.250.190.4`) to route to a server. DNS **resolves** a domain name into its IP address so the browser can connect.

It's hierarchical (root → TLD → authoritative servers) and usually runs over **UDP port 53** (falling back to TCP for large responses or zone transfers).


DNS 是網際網路的**電話簿**：人好記域名（`www.google.com`），但網路底層要數字 IP（`142.250.190.4`）才能連線。DNS 把域名**解析**成 IP。階層式（root → TLD → authoritative），通常走 UDP port 53。

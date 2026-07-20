---
id: net-unicast-broadcast-multicast
domain: systems
title: Unicast vs Broadcast vs Multicast
tags: [networking, addressing]
mastery: 0
source:
visibility: public
---

- **Unicast:** one-to-**one** — a packet from a single source to a single specific destination (e.g. standard web browsing). 單播＝一對一（瀏覽特定網頁）
- **Broadcast:** one-to-**all** — a packet to every device on the same LAN segment (e.g. an ARP request looking for a MAC address). 廣播＝一對整個 LAN 網段所有裝置（ARP 找 MAC）
- **Multicast:** one-to-**a group** — a packet only to devices that subscribed to a multicast group, saving bandwidth (e.g. IPTV streaming, stock-ticker feeds).
多播＝一對「有訂閱群組」的裝置，大幅省頻寬（IPTV）

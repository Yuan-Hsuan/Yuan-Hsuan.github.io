---
id: net-packet-transmission-flow
domain: systems
title: Packet Transmission — Encapsulation & the IP Layer
tags: [networking, osi, encapsulation, network-layer, ip, routing]
mastery: 0
source:
visibility: public
---

## Encapsulation — how data goes down the stack

When data is sent, it is **encapsulated** top-down through the OSI stack — each layer adds its own header:

1. **Application:** generates the original payload (e.g. an HTTP request).
2. **Transport:** adds a TCP/UDP header (source/dest **ports**) → a **Segment / Datagram**.
3. **Network:** adds an IP header (source/dest **IP**) → a **Packet**.
4. **Data Link:** adds a MAC header + checksum (FCS) → a **Frame**.
5. **Physical:** converts the frame into bits (electrical / optical / radio signals).

The receiver runs the reverse — **decapsulation** bottom-up — stripping one header per layer until the original payload is recovered.

送資料時由上而下逐層**封裝**：App 產生原始資料 → Transport 加 TCP/UDP 標頭 (Port) 成 **Segment** → Network 加 IP 標頭成 **Packet** → Data Link 加 MAC + FCS 成 **Frame** → Physical 轉成 bits 送出。收端由下而上**解封裝**，層層剝標頭還原資料。

## The IP layer — who routes the packet

The IP protocol operates at the **Network Layer** and is responsible for **routing and addressing** packets from source to destination. It assigns logical IP addresses (IPv4 = 32-bit, IPv6 = 128-bit) so every device has a unique identifier.

IP itself is **connectionless and unreliable (best-effort delivery)** — packets may be lost or arrive out of order; reliability is left entirely to upper-layer protocols like TCP.

IP 位於 OSI **網路層**，負責把封包從來源**路由**到目的、並定義 IP 位址（IPv4/IPv6）。IP 本身**非連線導向且不可靠（best-effort）**，封包可能遺失或亂序，可靠性交給上層 TCP——這正是上面封裝流程裡 Network 層那一站的工作。

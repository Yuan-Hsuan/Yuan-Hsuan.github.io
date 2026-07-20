---
id: net-tcp-vs-udp
domain: systems
title: TCP vs UDP — and the Three-Way Handshake
tags: [networking, transport-layer, tcp, udp]
mastery: 0
source:
visibility: public
---

## The two transport protocols

**TCP (Transmission Control Protocol):** a **reliable, connection-oriented** protocol that guarantees ordered, lossless delivery, with error checking, flow control, and congestion control. Ideal where data integrity matters — web browsing (HTTP/HTTPS), file transfer (FTP).

**UDP (User Datagram Protocol):** an **unreliable, connectionless** protocol — no delivery or order guarantee, no congestion control — but with minimal overhead, so it's fast and low-latency. Ideal where speed beats perfect integrity — video streaming, real-time voice/video, online gaming.

**TCP：** 可靠、連線導向，保證封包按序不遺失，有錯誤檢查/流量/壅塞控制（較慢）；用於網頁、檔案傳輸。
**UDP：** 不可靠、非連線導向，不保證順序或送達、無壅塞控制，但開銷極小、速度快延遲低；用於串流、即時視訊、遊戲。

## How TCP opens a connection — the three-way handshake

1. **SYN (Synchronize):** the client sends a SYN packet to the server to initiate a connection.
2. **SYN-ACK (Synchronize-Acknowledge):** the server replies with a SYN-ACK, acknowledging the request and signaling it's ready too.
3. **ACK (Acknowledge):** the client sends a final ACK back. The connection is now established.

Why three and not two: the connection is **bidirectional**, so each side must both announce its **initial sequence number** and confirm it received the other's.

為什麼要三次不是兩次——連線是**雙向**的，雙方都要各自宣告初始 sequence number、並確認收到對方的。UDP 沒有這套流程，這正是它「快但不保證」的來源。

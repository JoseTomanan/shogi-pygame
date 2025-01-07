package main

import (
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"strconv"

	"github.com/gorilla/websocket"
)

const messageSizeLimit int64 = 202
const clientMessageBufferSize int64 = 256

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin:     func(_ *http.Request) bool { return true },
}

type Client struct {
	sendCh chan Message
}

type Message struct {
	sourceId int
	payload  []byte
}

type Broadcaster struct {
	client1     *Client
	client2     *Client
	broadcastCh chan Message
}

func (m Message) asByteSlice() []byte {
	return append([]byte(strconv.Itoa(m.sourceId)+" "), m.payload...)
}

func makeBroadcaster() *Broadcaster {
	return &Broadcaster{
		client1:     nil,
		client2:     nil,
		broadcastCh: make(chan Message),
	}
}

func (r *Broadcaster) serve() {
	for {
		rawMessage := <-r.broadcastCh

		if r.client1 != nil {
			r.client1.sendCh <- rawMessage
		}

		if r.client2 != nil {
			r.client2.sendCh <- rawMessage
		}
	}
}

func (r *Broadcaster) registerClient(client *Client) int {
	if r.client1 == nil {
		r.client1 = client
		return 1
	}

	if r.client2 == nil {
		r.client2 = client
		return 2
	}

	return 0
}

func (c *Client) start(broadcaster *Broadcaster, w http.ResponseWriter, r *http.Request) {
	clientId := broadcaster.registerClient(c)

	if clientId <= 0 {
		log.Printf("Rejected %s; no more space for new clients\n", r.RemoteAddr)
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println(err)
		return
	}

	emptyMessage := Message { sourceId: clientId, payload: []byte{} }
	conn.WriteMessage(websocket.TextMessage, emptyMessage.asByteSlice())

	log.Printf("%s is now Player %d\n", r.RemoteAddr, clientId)

	conn.SetReadLimit(messageSizeLimit)
	go c.startSendLoop(clientId, conn)
	go c.startRecvLoop(clientId, broadcaster, conn)
}

func (c *Client) startRecvLoop(clientId int, broadcaster *Broadcaster, conn *websocket.Conn) {
	for {
		_, byteMsg, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("error: %v", err)
			}
			break
		}

		message := Message{sourceId: clientId, payload: byteMsg}
		payloadWithId := message.asByteSlice()

		log.Printf("Received from Client %d: %s\n", clientId, string(payloadWithId))
		broadcaster.broadcastCh <- message
	}
}

func (c *Client) startSendLoop(clientId int, conn *websocket.Conn) {
	for {
		message := <-c.sendCh
		payloadWithId := message.asByteSlice()

		log.Printf("Broadcasting to Client %d: %s\n", clientId, string(message.asByteSlice()))
		conn.WriteMessage(websocket.TextMessage, payloadWithId)
	}
}

func printIPAddresses() {
	ifaces, err := net.Interfaces()

	if err != nil {
		log.Fatalf("error: Cannot get network interfaces for IP addresses")
	}

	for _, iface := range ifaces {
		addrs, err := iface.Addrs()

		if err != nil {
			log.Fatalf("error: Cannot get IP addresses of interface")
		}

		for _, addr := range addrs {
			ip := ""

			switch v := addr.(type) {
			case *net.IPNet:
				ip = v.IP.String()
			case *net.IPAddr:
				ip = v.IP.String()
			}

			if _, err := strconv.Atoi(string(ip[0])); err == nil {
				// Print only IPv4 addresses
				log.Printf("- IP address: %s", string(ip))
			}
		}
	}
}

func main() {
	log.Printf("Starting communication server...")

	var portPtr = flag.Int("port", 15000, "server port")
	flag.Parse()

	log.Printf("- Port: %d", *portPtr)
	printIPAddresses()

	broadcaster := makeBroadcaster()
	go broadcaster.serve()

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		log.Printf("Connection request from %s\n", r.RemoteAddr)

		client := &Client{sendCh: make(chan Message, clientMessageBufferSize)}
		client.start(broadcaster, w, r)
	})

	if err := http.ListenAndServe(fmt.Sprintf("0.0.0.0:%d", *portPtr), nil); err != nil {
		log.Fatal("error: ", err)
	}
}
